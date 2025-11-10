#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
from typing import List, Dict, Optional, Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error, r2_score
from statsmodels.tsa.ar_model import AutoReg
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import SimpleExpSmoothing, Holt
from statsmodels.tsa.statespace.sarimax import SARIMAX

from src.Generation.Feature_engineering import engineer_all_features
from src.Generation.data_loader import get_all_transactions

# --- Állandók / konfiguráció (NINCS argumentum, FIX uid) ---
TARGET = "amount"
FORECAST_STEPS = 10
ARIMA_ORDER = (1, 1, 1)
MIN_POINTS = 8  # minimum pont a futtatáshoz (konzervatív)
uid_base = "3Dye4gBbAdPQSto3WbqgkBu6lrj2"
OUT_PATH = Path("forecast_output.csv")


# --- helper funkciók ---


def is_flat(series: pd.Series, rel_tol: float = 0.01) -> bool:
    if series is None:
        return True
    try:
        mx = float(series.max())
        mn = float(series.min())
        mean = float(series.mean())
    except Exception:
        return True
    if mean == 0:
        return (mx - mn) < 1e-6
    return (mx - mn) / mean < rel_tol


def naive_last(series: pd.Series, steps: int):
    return np.repeat(series.iloc[-1], steps)


# --- segédfüggvény: DataFrame -> havi Series előállítása (robosztusabb) ---
def prepare_monthly_series_from_df(df: pd.DataFrame, date_col="date", amount_col=TARGET) -> pd.Series:
    df = df.copy()
    if date_col not in df.columns:
        raise ValueError(f"A '{date_col}' oszlop hiányzik a DataFrame-ből.")
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    if amount_col not in df.columns:
        raise ValueError(f"A '{amount_col}' oszlop hiányzik a DataFrame-ből.")
    df[amount_col] = pd.to_numeric(df[amount_col], errors="coerce").fillna(0.0).abs()
    df = df.dropna(subset=[date_col])
    if df.empty:
        return pd.Series(dtype=float)
    df = df.set_index(date_col).sort_index()
    monthly = df[amount_col].resample("ME").sum().fillna(0)
    monthly = monthly.asfreq("ME", fill_value=0.0)
    return monthly


# --- inspect segéd ---
def inspect_series(monthly_series: pd.Series, plot: bool = False, verbose: bool = False):
    if verbose:
        print("\n--- SERIE INSPECT ---")
        print(monthly_series.to_string())
        print("\nLeíró statisztika:")
        print(monthly_series.describe().to_string())
        print("\nNullák száma:", int((monthly_series == 0).sum()), " / ", len(monthly_series))
    if plot:
        try:
            monthly_series.plot(marker="o", figsize=(8, 4), title="Monthly series — inspect")
            plt.grid(True)
            plt.show()
        except Exception:
            pass


# --- outlier kezelés: winsorize (most kicsit erősebb alapértelmezés) ---
def winsorize_series(s: pd.Series, lower_q=0.01, upper_q=0.99) -> pd.Series:
    lo = s.quantile(lower_q)
    hi = s.quantile(upper_q)
    return s.clip(lower=lo, upper=hi)


# --- seasonal-naive baseline ---
def seasonal_naive(series: pd.Series, steps=10):
    if len(series) >= 12:
        idx = pd.date_range(start=series.index[-1] + pd.offsets.MonthEnd(1), periods=steps, freq="ME")
        vals = []
        for i in range(steps):
            target = series.index[-1] + pd.offsets.MonthEnd(1) + pd.offsets.MonthEnd(i)
            ref = target - pd.DateOffset(months=12)
            if ref in series.index:
                vals.append(series.loc[ref])
            else:
                vals.append(series.iloc[-1])
        return pd.Series(vals, index=idx)
    else:
        return pd.Series([series.iloc[-1]] * steps, index=pd.date_range(start=series.index[-1] + pd.offsets.MonthEnd(1), periods=steps, freq="ME"))


# --- modellező/fc függvények ---
def _safe_expm1_arr(arr, cap=700.0, max_out=None):
    a = np.array(arr, dtype=float)
    a = np.where(a > cap, cap, a)
    with np.errstate(over='ignore', invalid='ignore'):
        out = np.expm1(a)
    out = np.where(np.isfinite(out), out, np.nan)
    out = np.where(out < 0, 0.0, out)
    if max_out is not None:
        out = np.minimum(out, max_out)
    return out


def fit_and_forecast_arima(series: pd.Series, order=(1, 1, 1), steps=10, use_log=False):
    """
    Robusztus ARIMA wrapper. FONTOS: alapból use_log=False (elkerüljük az exp overflow-t).
    """
    s = series.copy().astype(float)
    apply_log = bool(use_log)
    if apply_log:
        # ha valami negatív van, kikapcsoljuk a logot
        if (s < 0).any():
            apply_log = False

    if apply_log:
        s_t = np.log1p(s)
    else:
        s_t = s

    try:
        model = ARIMA(s_t, order=order)
        fit = model.fit()
        fc = fit.get_forecast(steps=steps)
        mean_fc = fc.predicted_mean
        ci = fc.conf_int(alpha=0.2)

        if apply_log:
            # ha mégis logoltunk, safe visszaalakítás
            cap = 700.0
            max_out = float(max(series.max() * 10.0, 1e6))
            mean_bt = np.expm1(np.minimum(mean_fc.values, cap))
            lower_log = np.minimum(ci.iloc[:, 0].values, cap)
            upper_log = np.minimum(ci.iloc[:, 1].values, cap)
            lower_bt = _safe_expm1_arr(lower_log, cap=cap, max_out=max_out)
            upper_bt = _safe_expm1_arr(upper_log, cap=cap, max_out=max_out)
            if mean_fc.index is None or len(mean_fc.index) == 0:
                idx = pd.date_range(start=series.index[-1] + pd.offsets.MonthEnd(1), periods=len(mean_bt), freq="ME")
            else:
                idx = mean_fc.index
            mean_ser = pd.Series(mean_bt, index=idx)
            ci_df = pd.DataFrame({"lower": lower_bt, "upper": upper_bt}, index=idx)
            ci_df["lower"] = ci_df["lower"].clip(lower=0.0)
            return fit, mean_ser, ci_df
        else:
            if mean_fc.index is None or len(mean_fc.index) == 0:
                idx = pd.date_range(start=series.index[-1] + pd.offsets.MonthEnd(1), periods=len(mean_fc), freq="ME")
                mean_fc.index = idx
                ci.index = idx
            try:
                ci.columns = ["lower", "upper"]
                ci["lower"] = ci["lower"].clip(lower=0.0)
            except Exception:
                pass
            return fit, mean_fc, ci

    except Exception as e:
        print(f"⚠️ ARIMA fit error: {e}")
        return None, None, None


def fit_and_forecast_sarimax(series: pd.Series, order=(1, 1, 1), seasonal_order=(1, 1, 1, 12), steps=10, use_log=False):
    s = series.copy().astype(float)
    transform = False
    if use_log:
        if (s < 0).any():
            use_log = False
        else:
            s = np.log1p(s)
            transform = True
    try:
        model = SARIMAX(s, order=order, seasonal_order=seasonal_order,
                        enforce_stationarity=False, enforce_invertibility=False)
        fit = model.fit(disp=False)
        fc = fit.get_forecast(steps=steps)
        mean = fc.predicted_mean
        ci = fc.conf_int(alpha=0.2)
        if transform:
            cap = 700.0
            max_out = float(max(series.max() * 10.0, 1e6))
            mean_bt = np.expm1(np.minimum(mean.values, cap))
            lower_log = np.minimum(ci.iloc[:, 0].values, cap)
            upper_log = np.minimum(ci.iloc[:, 1].values, cap)
            lower_bt = _safe_expm1_arr(lower_log, cap=cap, max_out=max_out)
            upper_bt = _safe_expm1_arr(upper_log, cap=cap, max_out=max_out)
            idx = pd.date_range(start=series.index[-1] + pd.offsets.MonthEnd(1), periods=len(mean_bt), freq="ME")
            mean = pd.Series(mean_bt, index=idx)
            ci = pd.DataFrame({"lower": lower_bt, "upper": upper_bt}, index=idx)
            ci["lower"] = ci["lower"].clip(lower=0.0)
            return fit, mean, ci
        else:
            idx = pd.date_range(start=series.index[-1] + pd.offsets.MonthEnd(1), periods=len(mean), freq="ME")
            mean.index = idx
            ci.index = idx
            try:
                ci.columns = ["lower", "upper"]
                ci["lower"] = ci["lower"].clip(lower=0.0)
            except Exception:
                pass
            return fit, mean, ci
    except Exception as e:
        print(f"⚠️ SARIMAX fit error: {e}")
        return None, None, None


def fit_and_forecast_ses(series: pd.Series, steps=10):
    try:
        model = SimpleExpSmoothing(series).fit(optimized=True)
        mean = model.forecast(steps)
        resid = model.fittedvalues - series
        resid_std = resid.std(ddof=1) if len(resid) > 1 else np.std(series)
        z = 1.2816
        lower = mean - z * resid_std
        upper = mean + z * resid_std
        idx = pd.date_range(start=series.index[-1] + pd.offsets.MonthEnd(1), periods=len(mean), freq="ME")
        mean = pd.Series(mean.values, index=idx, name="ses_forecast")
        ci = pd.DataFrame({"lower": lower, "upper": upper}, index=idx)
        ci["lower"] = ci["lower"].clip(lower=0.0)
        return mean, ci
    except Exception as e:
        print(f"⚠️ SES fit error: {e}")
        return None, None


def fit_and_forecast_holt(series: pd.Series, steps=10):
    try:
        model = Holt(series, exponential=False, damped_trend=True).fit(optimized=True)
        mean = model.forecast(steps)
        resid = model.fittedvalues - series
        resid_std = resid.std(ddof=1) if len(resid) > 1 else np.std(series)
        z = 1.2816
        lower = mean - z * resid_std
        upper = mean + z * resid_std
        idx = pd.date_range(start=series.index[-1] + pd.offsets.MonthEnd(1), periods=len(mean), freq="ME")
        mean = pd.Series(mean.values, index=idx, name="holt_forecast")
        ci = pd.DataFrame({"lower": lower, "upper": upper}, index=idx)
        ci["lower"] = ci["lower"].clip(lower=0.0)
        return mean, ci
    except Exception as e:
        print(f"⚠️ Holt fit error: {e}")
        return None, None


def fit_and_forecast_autoreg(series: pd.Series, lags=5, steps=10):
    try:
        used_lags = min(lags, max(1, len(series) - 1))
        model = AutoReg(series, lags=used_lags, old_names=False).fit()
        start = len(series)
        end = start + steps - 1
        preds = model.predict(start=start, end=end, dynamic=False)
        idx = pd.date_range(start=series.index[-1] + pd.offsets.MonthEnd(1), periods=steps, freq="ME")
        preds = pd.Series(preds.values, index=idx, name="autoreg_forecast")
        preds = preds.clip(lower=0.0)
        return model, preds, None
    except Exception as e:
        print(f"⚠️ AutoReg fit error: {e}")
        return None, None, None


def fit_and_forecast_time_regression_boosted(series: pd.Series, steps=10, lags_for_features=3, alpha=0.8):
    try:
        n = len(series)
        if n < 3:
            return None, None, None

        df = pd.DataFrame({"y": series.values})
        used_lags = min(lags_for_features, max(1, n - 2))
        for i in range(1, used_lags + 1):
            df[f"lag{i}"] = df["y"].shift(i)

        df["t"] = np.arange(n)
        months = series.index.month.values
        df["month_sin"] = np.sin(2 * np.pi * (months - 1) / 12.0)
        df["month_cos"] = np.cos(2 * np.pi * (months - 1) / 12.0)

        df = df.dropna()
        lag_features = [f"lag{i}" for i in range(1, used_lags + 1)]
        feat_cols = lag_features + ["t", "month_sin", "month_cos"]
        X = df[feat_cols].values
        y = df["y"].values

        reg = Ridge(alpha=alpha, fit_intercept=True, random_state=42).fit(X, y)

        last_vals = list(series.values[-used_lags:])
        last_t = n
        preds = []
        for step in range(steps):
            cur_month = ((series.index[-1].month - 1 + step + 1) % 12) + 1
            month_sin = np.sin(2 * np.pi * (cur_month - 1) / 12.0)
            month_cos = np.cos(2 * np.pi * (cur_month - 1) / 12.0)
            feat = np.array(last_vals[-used_lags:] + [last_t, month_sin, month_cos]).reshape(1, -1)
            yhat = float(reg.predict(feat)[0])
            preds.append(yhat)
            last_vals.append(yhat)
            last_t += 1

        idx = pd.date_range(start=series.index[-1] + pd.offsets.MonthEnd(1), periods=steps, freq="ME")
        preds = pd.Series(preds, index=idx, name="time_reg_ridge_forecast")
        preds = preds.clip(lower=0.0)
        return reg, preds, None

    except Exception as e:
        print("⚠️ Time-reg (Ridge) fit error:", e)
        return None, None, None


# --- walk-forward (javítva) ---
def walk_forward_1step(series: pd.Series, model_order=(1, 1, 1), n_test=5):
    if n_test >= len(series):
        raise ValueError("n_test túl nagy a sorozathoz.")
    history = series.iloc[:-n_test].copy()
    test = series.iloc[-n_test:].tolist()
    preds = []
    for t in range(len(test)):
        try:
            model = ARIMA(history, order=model_order).fit()
            yhat = float(model.forecast(steps=1).iloc[0])
        except Exception:
            yhat = float(history.iloc[-1])
        preds.append(yhat)
        next_idx = history.index[-1] + pd.offsets.MonthEnd(1)
        history = pd.concat([history, pd.Series([test[t]], index=[next_idx])])
    mse = mean_squared_error(test, preds)
    r2 = r2_score(test, preds) if len(test) > 1 else float("nan")
    return preds, test, mse, r2


# --- plot results ---
def plot_results(series, forecast_mean, forecast_ci, baseline_preds=None, save_path: Path = None, plot: bool = False):
    if not plot:
        return

    plt.figure(figsize=(10, 6))
    plt.plot(series.index, series.values, label="Valós (monthly)", marker="o")
    last_date = series.index[-1]
    if hasattr(forecast_mean, "index") and len(forecast_mean.index) > 0:
        forecast_index = forecast_mean.index
    else:
        forecast_index = pd.date_range(start=last_date + pd.offsets.MonthEnd(1), periods=len(forecast_mean), freq="ME")
    plt.plot(forecast_index, forecast_mean, label="Forecast", linestyle="--", marker="o")
    try:
        if forecast_ci is not None:
            lower = forecast_ci.iloc[:, 0]
            upper = forecast_ci.iloc[:, 1]
            plt.fill_between(forecast_index, lower, upper, alpha=0.25, label="80% CI")
    except Exception:
        pass
    if baseline_preds is not None:
        try:
            plt.plot(forecast_index, baseline_preds, label="Baseline (seasonal-naive/SES)", linestyle="-.")
        except Exception:
            pass
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path)
        print(f"Plot elmentve: {save_path}")
    else:
        plt.show()


# helper used in plot
def simple_exp_smoothing_forecast(series, steps):
    m = SimpleExpSmoothing(series).fit()
    return m.forecast(steps)


# --- Javított pipeline: ARIMA/SARIMAX vs SES vs HOLT vs AUTOREG + fallbacks ---
def run_short_series_pipeline(monthly_series: pd.Series, plot: bool = False, verbose: bool = False):
    if len(monthly_series) < MIN_POINTS:
        raise ValueError(f"Adatmennyiség túl kevés (min {MIN_POINTS} hónap ajánlott).")

    inspect_series(monthly_series, plot=plot, verbose=verbose)

    # winsorize az outlierek mérséklésére
    monthly_series_proc = winsorize_series(monthly_series)

    # --- walk-forward metrikák (ARIMA alapú) ---
    n_test = min(5, len(monthly_series_proc) // 3)
    preds_arima, test_vals, mse_arima, r2_arima = walk_forward_1step(monthly_series_proc, model_order=ARIMA_ORDER,
                                                                     n_test=n_test)
    if verbose:
        print(f"Walk-forward (1-step) ARIMA MSE: {mse_arima:.3f}, R2: {r2_arima:.3f}")

    # SES WF
    history = monthly_series_proc.iloc[:-n_test].tolist()
    ses_preds = []
    test = monthly_series_proc.iloc[-n_test:].tolist()
    for t in range(len(test)):
        try:
            s = SimpleExpSmoothing(pd.Series(history)).fit()
            yhat = float(s.forecast(1)[0])
        except Exception:
            yhat = float(history[-1])
        ses_preds.append(yhat)
        history.append(test[t])
    mse_ses = mean_squared_error(test, ses_preds)
    if verbose:
        print(f"Walk-forward (1-step) SES MSE: {mse_ses:.3f}")

    # HOLT WF
    history = monthly_series_proc.iloc[:-n_test].copy()
    holt_preds = []
    for t in range(len(test)):
        try:
            hmod = Holt(history).fit(optimized=True)
            yhat = float(hmod.forecast(1)[0])
        except Exception:
            yhat = float(history.iloc[-1])
        holt_preds.append(yhat)
        next_idx = history.index[-1] + pd.offsets.MonthEnd(1)
        history = pd.concat([history, pd.Series([test[t]], index=[next_idx])])
    mse_holt = mean_squared_error(test, holt_preds)
    if verbose:
        print(f"Walk-forward (1-step) HOLT MSE: {mse_holt:.3f}")

    # AUTOREG WF
    try:
        _, ar_preds_wf, _ = fit_and_forecast_autoreg(monthly_series_proc.iloc[:-n_test], lags=5, steps=n_test)
        mse_autoreg = mean_squared_error(test, ar_preds_wf.values)
    except Exception:
        mse_autoreg = float("inf")
    if verbose:
        print(f"Walk-forward (1-step) AUTOREG MSE: {mse_autoreg:.3f}")

    # --- Modellválasztás: normalizált MSE (mse / var) - stabilabb döntés skálánként ---
    var = np.var(monthly_series_proc.values) if len(monthly_series_proc) > 1 else 1.0
    def norm(mse):
        return mse / (var + 1e-9)

    candidates = [
        ("arima", mse_arima, norm(mse_arima)),
        ("ses", mse_ses, norm(mse_ses)),
        ("holt", mse_holt, norm(mse_holt)),
        ("autoreg", mse_autoreg, norm(mse_autoreg)),
    ]
    # sort by normalized mse
    candidates_sorted = sorted(candidates, key=lambda x: x[2])
    chosen = candidates_sorted[0][0]
    if verbose:
        print(f"👉 Modell döntés (norm. WF MSE alapján): {chosen.upper()} választva (raw MSE={candidates_sorted[0][1]:.1f}, norm={candidates_sorted[0][2]:.3f}).")

    mean_forecast = None
    ci = None

    # helper: sanity-check
    def _forecast_is_sane(fc: pd.Series, orig: pd.Series, scale_factor=10.0):
        if fc is None or not isinstance(fc, pd.Series):
            return False
        if fc.isna().any():
            return False
        if np.isinf(fc.values).any():
            return False
        if (fc < 0).any():
            return False
        if orig.max() > 0 and (fc.max() > orig.max() * scale_factor):
            return False
        return True

    # try chosen; if fails or numerically insane -> fallback chain
    tried = []
    def try_model(model_name):
        nonlocal mean_forecast, ci
        tried.append(model_name)
        if model_name == "holt":
            mean_forecast, ci = fit_and_forecast_holt(monthly_series_proc, steps=FORECAST_STEPS)
        elif model_name == "ses":
            mean_forecast, ci = fit_and_forecast_ses(monthly_series_proc, steps=FORECAST_STEPS)
        elif model_name == "autoreg":
            _, mean_forecast, ci = fit_and_forecast_autoreg(monthly_series_proc, lags=8, steps=FORECAST_STEPS)
        elif model_name == "arima":
            # IMPORTANT: disable log by default to avoid exp overflow
            fit, mean_forecast, ci = fit_and_forecast_arima(monthly_series_proc, order=ARIMA_ORDER, steps=FORECAST_STEPS, use_log=False)
            # if ARIMA returned None, mean_forecast stays None
        return _forecast_is_sane(mean_forecast, monthly_series_proc, scale_factor=10.0)

    # Try primary model
    ok = try_model(chosen)
    if not ok:
        # fallback order: SARIMAX -> time-reg -> seasonal-naive -> Holt/SES
        print(f"⚠️ A választott modell ({chosen}) numerikailag gyanús vagy nem futott: {mean_forecast}")
        # Try SARIMAX
        fit_sar, mean_sar, ci_sar = fit_and_forecast_sarimax(monthly_series_proc, order=ARIMA_ORDER, seasonal_order=(1, 1, 1, 12), steps=FORECAST_STEPS, use_log=False)
        if _forecast_is_sane(mean_sar, monthly_series_proc, scale_factor=10.0):
            mean_forecast, ci = mean_sar, ci_sar
            print("✅ SARIMAX fallback ok.")
        else:
            _, tr_preds, _ = fit_and_forecast_time_regression_boosted(monthly_series_proc, steps=FORECAST_STEPS, lags_for_features=3)
            if _forecast_is_sane(tr_preds, monthly_series_proc, scale_factor=10.0):
                mean_forecast, ci = tr_preds, None
                print("✅ Time-reg fallback ok.")
            else:
                # try simpler Holt/SES as final fallback
                mean_h, ci_h = fit_and_forecast_holt(monthly_series_proc, steps=FORECAST_STEPS)
                if _forecast_is_sane(mean_h, monthly_series_proc, scale_factor=10.0):
                    mean_forecast, ci = mean_h, ci_h
                    print("✅ Holt fallback ok.")
                else:
                    mean_forecast = seasonal_naive(monthly_series_proc, FORECAST_STEPS)
                    ci = None
                    print("✅ Seasonal-naive final fallback ok.")

    # if forecast is flat, try AutoReg/time-reg fallback
    if is_flat(mean_forecast, rel_tol=0.01):
        print("⚠️ Forecast túl lapos — próbálkozom AutoReg/time-reg fallback-kel.")
        _, ar_preds, _ = fit_and_forecast_autoreg(monthly_series_proc, lags=8, steps=FORECAST_STEPS)
        if (ar_preds is not None) and (not is_flat(ar_preds, rel_tol=0.01)):
            mean_forecast = ar_preds
            ci = None
            print("✅ AutoReg fallback sikeres.")
        else:
            _, tr_preds, _ = fit_and_forecast_time_regression_boosted(monthly_series_proc, steps=FORECAST_STEPS, lags_for_features=3)
            if tr_preds is not None:
                mean_forecast = tr_preds
                ci = None
                print("✅ Time-reg fallback sikeres.")

    # ensure pd.Series index
    if isinstance(mean_forecast, (np.ndarray, list)):
        mean_forecast = pd.Series(mean_forecast,
                                  index=pd.date_range(start=monthly_series_proc.index[-1] + pd.offsets.MonthEnd(1),
                                                      periods=len(mean_forecast), freq="ME"))

    # clamp negatives & extremely large values
    try:
        mean_forecast = mean_forecast.clip(lower=0.0)
        max_allowed = max(monthly_series_proc.max() * 20.0, 1e7)  # agressive cap to avoid e+6 surprises
        mean_forecast = mean_forecast.clip(upper=max_allowed)
        if ci is not None:
            ci["lower"] = ci["lower"].clip(lower=0.0)
            ci["upper"] = ci["upper"].clip(upper=max_allowed)
    except Exception:
        pass

    print("Előrejelzés (pontbecslés):\n", mean_forecast)

    try:
        baseline_vals = seasonal_naive(monthly_series_proc, FORECAST_STEPS)
    except Exception:
        baseline_vals = None

    plot_results(monthly_series_proc, forecast_mean=mean_forecast, forecast_ci=ci,
                 baseline_preds=baseline_vals)

    fc_series = pd.Series(mean_forecast.values, index=mean_forecast.index)
    fc_ci = ci
    return fc_series, fc_ci, {"wf_mse_arima": mse_arima, "wf_mse_ses": mse_ses, "wf_mse_holt": mse_holt,
                              "wf_mse_autoreg": mse_autoreg}


# --- Fő függvény (nem vár paramétereket) ---
# Az eredeti run_sarima_pipeline() logika most a ForecastPipeline osztályban is meghívható.
class ForecastPipeline:
    """
    Pipeline wrapper:
      - run(uid=None, tx_list=None)
      - ha tx_list meg van adva: azt használja (raw tranzakciók)
      - különben lekéri a transactions-okat uid alapján
      Visszatér egy dict-tel, amiben vannak:
        - history: list of {"date": "YYYY-MM", "value": float}
        - forecast: list of {"date": "YYYY-MM", "value": float}
        - ci: list of {"date": "YYYY-MM", "lower": float, "upper": float} vagy None
        - metrics: dict (walk-forward metrikák)
        - raw_arrays: opcionálisan numpy array-ek (history_arr, forecast_arr)
        - status: "from_db" | "demo" | "no_data"
    """

    def __init__(self, uid_default: str = uid_base, out_path: Path = OUT_PATH):
        self.uid_default = uid_default
        self.out_path = out_path

    def _series_to_date_value_list(self, series: pd.Series) -> List[Dict[str, Any]]:
        out = []
        for ts, v in series.items():
            try:
                date_str = pd.to_datetime(ts).strftime("%Y-%m")
            except Exception:
                date_str = str(ts)
            # Sanitize inf/nan values
            val = float(v)
            if not np.isfinite(val):
                val = 0.0
            out.append({"date": date_str, "value": val})
        return out

    def _ci_to_list(self, ci_df: Optional[pd.DataFrame]) -> Optional[List[Dict[str, Any]]]:
        if ci_df is None:
            return None
        out = []
        for idx, row in ci_df.iterrows():
            try:
                date_str = pd.to_datetime(idx).strftime("%Y-%m")
            except Exception:
                date_str = str(idx)
            # row may have columns in either order; pick first two as lower/upper
            try:
                lower = float(row.iloc[0])
                upper = float(row.iloc[1])
            except Exception:
                lower = float(row.get("lower", np.nan))
                upper = float(row.get("upper", np.nan))
            out.append({"date": date_str, "lower": lower, "upper": upper})
        return out

    def run(self, uid: Optional[str] = None, tx_list: Optional[List[Dict[str, Any]]] = None, plot=False, verbose=False) -> Dict[str, Any]:
        """
        Futtatja a pipeline-t.
        - Preferálja a tx_list-et, ha kapott ilyet (API előre lekéri és átadja).
        - Ha nincs tx_list, akkor uid kell (vagy a default uid használódik) és a pipeline lekéri a DB-t.
        Visszaad részletes, JSON-szerializálható dict-et.
        """
        uid_local = uid if uid is not None else self.uid_default
        # 1) adatforrás: tx_list vagy DB
        if tx_list is None:
            try:
                tx_list = get_all_transactions(uid)
            except Exception as e:
                print(f"❌ Hiba a tranzakciók lekérésekor: {e}")
                tx_list = []

        monthly_series = None
        used_status = "no_data"

        if tx_list:
            df_tx = pd.DataFrame(tx_list)
            # próbáljuk meg a feature-engineeringet egy helyen (pipeline kezeli)
            try:
                df_tx = engineer_all_features(df_tx)
            except Exception as e:
                print(f"⚠️ engineer_all_features hibát dobott: {e} (folytatom a nyers df-fel)")

            # NORMALIZÁLÁS: prefer 'for_who' -> tran_type_norm (megegyezik a korábbi logikával)
            if 'for_who' in df_tx.columns:
                df_tx['tran_type_norm'] = df_tx['for_who'].astype(str).str.lower()
            else:
                df_tx['tran_type_norm'] = ''

            outgoing_mask = df_tx['tran_type_norm'].str.contains('out|kimen|ki|kimenő', na=False)
            df_tx = df_tx[outgoing_mask].copy()

            if 'internal_transfer' in df_tx.columns:
                df_tx = df_tx[df_tx['internal_transfer'].fillna('none') == 'none'].copy()

            if TARGET not in df_tx.columns:
                print(f"❌ Figyelem: a pipeline elvárja a '{TARGET}' oszlopot az engineer_all_features kimenetében.")

            try:
                monthly_series = prepare_monthly_series_from_df(df_tx, date_col="date", amount_col=TARGET)
            except Exception as e:
                print(f"⚠️ Nem sikerült havi sorozatot előállítani: {e}")
                monthly_series = None

        # 2) fallback demo adat, ha nincs elegendő adat
        if (monthly_series is None) or monthly_series.empty:
            # demo adatokat hozunk létre — ugyanúgy, mint korábban
            periods = 10
            last = pd.Timestamp.today().normalize()
            idx = pd.date_range(end=last, periods=periods, freq="ME")
            np.random.seed(42)
            base = np.linspace(200, 400, periods)
            seasonal = 20 * np.sin(np.linspace(0, 2 * np.pi, periods))
            noise = np.random.normal(scale=30, size=periods)
            values = (base + seasonal + noise).clip(min=0)
            monthly_series = pd.Series(values.round(2), index=idx)
            used_status = "demo"
        else:
            used_status = "from_db"

        # 3) futtatjuk a meglévő modellező pipeline-t (blokkoló hívás — hétköznapi használatban to_thread)
        print("\n▶️ Lefuttatom a rövid-sorozat pipeline-t...")
        fc_series, fc_ci, metrics = run_short_series_pipeline(monthly_series)

        # 4) előkészítjük a kimenetet: dátummal párosított listák, CI, metrics
        history_list = self._series_to_date_value_list(monthly_series)
        forecast_list = self._series_to_date_value_list(fc_series)
        ci_list = self._ci_to_list(fc_ci)
        history_arr = monthly_series.values.astype(float)
        forecast_arr = fc_series.values.astype(float)

        # 5) opcionális: mentjük CSV-be (ugyanaz, mint korábban)
        try:
            ci_out = None
            if fc_ci is not None:
                ci_df = fc_ci.copy()
                lower = ci_df.iloc[:, 0].values
                upper = ci_df.iloc[:, 1].values
                ci_out = pd.DataFrame({"lower": lower, "upper": upper}, index=fc_series.index)
            df_out = pd.DataFrame(
                {
                    "forecast": fc_series,
                    "ci_lower": ci_out["lower"] if ci_out is not None else np.nan,
                    "ci_upper": ci_out["upper"] if ci_out is not None else np.nan,
                }
            )
            df_out.to_csv(self.out_path, index_label="date")
            print(f"\n💾 Elmentve (wrapper): {self.out_path.resolve()}")
        except Exception as e:
            print("⚠️ Nem sikerült elmenteni a forecast-ot (wrapper):", e)

        # 6) visszatérési dict
        result = {
            "status": "success",
            "data_source": used_status,
            "history": history_list,
            "forecast": forecast_list,
            "ci": ci_list,
            "metrics": metrics or {},
            # raw arrays included for internal use if kell
            "raw_arrays": {"history_arr": history_arr, "forecast_arr": forecast_arr},
        }
        return result


def run_sarima_pipeline(uid: str = None):
    """Backward-compatible wrapper: returns (history_arr, forecast_arr) extracted from the pipeline result dict."""
    pipeline = ForecastPipeline()
    result = pipeline.run(uid=uid)
    raw = result.get("raw_arrays", {})
    history_arr = raw.get("history_arr")
    forecast_arr = raw.get("forecast_arr")
    # Ha szeretnéd, itt ellenőrizhetsz None-okat és dobhatunk kivételt
    return history_arr, forecast_arr

if __name__ == "__main__":
    # Példa: futtatás script-ként
    hist, fut = run_sarima_pipeline()
    print("\nPélda output shape-ek:")
    print(" - history shape:", getattr(hist, "shape", None))
    print(" - forecast shape:", getattr(fut, "shape", None))
    print( hist, fut)
