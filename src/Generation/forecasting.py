#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main forecasting pipeline orchestration.
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, Any, List

from src.Generation.config import (
    TARGET, FORECAST_STEPS, MIN_POINTS, ARIMA_ORDER, SEASONAL_ORDER,
    MAX_NORMALIZED_MSE, FORECAST_SCALE_FACTOR, MAX_OUTPUT_CAP, BASELINE_REL_IMPROVEMENT,
    BACKTEST_MIN, BACKTEST_MAX, SEASONAL_MIN_POINTS
)
from src.Generation.utils import winsorize_series, inspect_series, is_flat
from src.Generation.validation import (
    walk_forward_1step, walk_forward_ses, walk_forward_holt, walk_forward_autoreg
)
from src.Generation.models import (
    fit_and_forecast_arima, fit_and_forecast_sarimax, fit_and_forecast_ses,
    fit_and_forecast_holt, fit_and_forecast_autoreg, fit_and_forecast_time_regression_boosted
)
from src.Generation.visualization import plot_results, seasonal_naive


def run_short_series_pipeline(
    monthly_series: pd.Series,
    exog: Optional[pd.DataFrame] = None,
    exog_forecast: Optional[pd.DataFrame] = None,
    plot: bool = False,
    verbose: bool = False
) -> tuple:
    """
    Main forecasting pipeline with automatic model selection.

    Performs walk-forward validation across multiple models (ARIMA, SES, Holt, AutoReg),
    selects the best model, and applies fallback mechanisms if needed.

    Args:
        monthly_series: Input monthly time series
        exog: Optional exogenous variables
        exog_forecast: Optional future exogenous variables
        plot: Whether to plot results
        verbose: Whether to print detailed logs

    Returns:
        Tuple of (forecast_series, confidence_interval, metrics_dict)
    """
    if len(monthly_series) < MIN_POINTS:
        raise ValueError(f"Adatmennyiség túl kevés (min {MIN_POINTS} hónap ajánlott).")

    inspect_series(monthly_series, plot=plot, verbose=verbose)

    # Winsorize outliers
    monthly_series_proc = winsorize_series(monthly_series)

    seasonal_order = SEASONAL_ORDER
    if len(monthly_series_proc) < SEASONAL_MIN_POINTS:
        seasonal_order = (0, 0, 0, 0)
        if verbose:
            print(
                f"⚠️ Rövid idősor ({len(monthly_series_proc)} pont) — "
                "szezonalitás kikapcsolva."
            )

    # --- Walk-forward validation across models ---
    n = len(monthly_series_proc)
    n_test = min(BACKTEST_MAX, max(BACKTEST_MIN, n // 3))
    n_test = min(n_test, n - 1)

    backtest_start = None
    backtest_end = None
    if n_test > 0:
        try:
            backtest_start = monthly_series_proc.index[-n_test]
            backtest_end = monthly_series_proc.index[-1]
        except Exception:
            backtest_start = None
            backtest_end = None

    def _calc_mae(y_true: np.ndarray, y_pred: np.ndarray) -> Optional[float]:
        if y_true.size == 0 or y_pred.size == 0:
            return None
        if y_true.size != y_pred.size:
            return None
        return float(np.mean(np.abs(y_true - y_pred)))

    def _calc_smape(y_true: np.ndarray, y_pred: np.ndarray, eps: float = 1e-6) -> Optional[float]:
        if y_true.size == 0 or y_pred.size == 0:
            return None
        if y_true.size != y_pred.size:
            return None
        denom = np.abs(y_true) + np.abs(y_pred) + eps
        return float(200.0 * np.mean(np.abs(y_true - y_pred) / denom))

    def _infer_exog_forecast_method(
        exog_df: Optional[pd.DataFrame],
        exog_fc: Optional[pd.DataFrame]
    ) -> str:
        if exog_fc is None:
            return "none"
        if exog_df is None or not isinstance(exog_df, pd.DataFrame) or exog_df.empty:
            return "provided"
        try:
            cols = [c for c in exog_fc.columns if c in exog_df.columns]
            if not cols:
                return "provided"
            last_row = exog_df.iloc[-1][cols]
            last_row = pd.to_numeric(last_row, errors="coerce").fillna(0.0).values
            fc_vals = exog_fc[cols].apply(pd.to_numeric, errors="coerce").fillna(0.0).values
            if fc_vals.size == 0:
                return "provided"
            repeated = np.allclose(fc_vals, last_row, rtol=0.0, atol=1e-9)
            return "last_known_ffill" if repeated else "provided"
        except Exception:
            return "provided"

    test_series = monthly_series_proc.iloc[-n_test:]
    test_arr = test_series.values if n_test > 0 else np.array([])

    # Seasonal-naive baseline WF
    baseline_mse = None
    baseline_mae = None
    baseline_smape = None
    baseline_wf_preds = None
    try:
        history = monthly_series_proc.iloc[:-n_test].copy()
        test = monthly_series_proc.iloc[-n_test:]
        preds = []
        for i in range(len(test)):
            cur_idx = test.index[i]
            ref_idx = cur_idx - pd.DateOffset(months=12)
            if len(history) >= 12 and ref_idx in history.index:
                pred = float(history.loc[ref_idx])
            else:
                pred = float(history.iloc[-1])
            preds.append(pred)
            history = pd.concat([history, pd.Series([test.iloc[i]], index=[cur_idx])])
        baseline_wf_preds = preds
        baseline_pred_arr = np.array(preds, dtype=float)
        baseline_mse = float(np.mean((test.values - baseline_pred_arr) ** 2))
        baseline_mae = _calc_mae(test.values, baseline_pred_arr)
        baseline_smape = _calc_smape(test.values, baseline_pred_arr)
        if verbose:
            print(f"Walk-forward (1-step) BASELINE MSE: {baseline_mse:.3f}")
    except Exception:
        baseline_mse = None
        baseline_mae = None
        baseline_smape = None
        baseline_wf_preds = None

    # ARIMA WF
    preds_arima, test_vals, mse_arima, r2_arima = walk_forward_1step(
        monthly_series_proc, model_order=ARIMA_ORDER, n_test=n_test)
    arima_pred_arr = np.array(preds_arima, dtype=float) if preds_arima else np.array([])
    arima_test_arr = np.array(test_vals, dtype=float) if test_vals else np.array([])
    mae_arima = _calc_mae(arima_test_arr, arima_pred_arr)
    smape_arima = _calc_smape(arima_test_arr, arima_pred_arr)
    if verbose:
        print(f"Walk-forward (1-step) ARIMA MSE: {mse_arima:.3f}, R2: {r2_arima:.3f}")

    # SES WF
    mse_ses, ses_preds = walk_forward_ses(monthly_series_proc, n_test=n_test)
    ses_pred_arr = np.array(ses_preds, dtype=float) if ses_preds else np.array([])
    mae_ses = _calc_mae(test_arr, ses_pred_arr)
    smape_ses = _calc_smape(test_arr, ses_pred_arr)
    if verbose:
        print(f"Walk-forward (1-step) SES MSE: {mse_ses:.3f}")

    # Holt WF
    mse_holt, holt_preds = walk_forward_holt(monthly_series_proc, n_test=n_test)
    holt_pred_arr = np.array(holt_preds, dtype=float) if holt_preds else np.array([])
    mae_holt = _calc_mae(test_arr, holt_pred_arr)
    smape_holt = _calc_smape(test_arr, holt_pred_arr)
    if verbose:
        print(f"Walk-forward (1-step) HOLT MSE: {mse_holt:.3f}")

    # AutoReg WF
    mse_autoreg, ar_preds = walk_forward_autoreg(monthly_series_proc, n_test=n_test, lags=5)
    ar_pred_arr = np.array(ar_preds, dtype=float) if ar_preds else np.array([])
    mae_autoreg = _calc_mae(test_arr, ar_pred_arr)
    smape_autoreg = _calc_smape(test_arr, ar_pred_arr)
    if verbose:
        print(f"Walk-forward (1-step) AUTOREG MSE: {mse_autoreg:.3f}")

    # --- Model selection: choose robust metric for sparse/skewed series ---
    zero_ratio = float((monthly_series_proc == 0).mean()) if n > 0 else 0.0
    try:
        skew_val = float(monthly_series_proc.skew()) if n > 2 else 0.0
    except Exception:
        skew_val = 0.0

    var = np.var(monthly_series_proc.values) if len(monthly_series_proc) > 1 else 1.0
    intermittent_series = zero_ratio >= 0.3
    low_variance_series = var <= 1e-9
    metric_choice = "smape" if (intermittent_series or abs(skew_val) >= 1.0 or low_variance_series) else "mse"

    # --- Model selection: keep ranking and gating on the same score scale ---
    def norm(mse: Optional[float]) -> float:
        if mse is None or not np.isfinite(mse):
            return float("inf")
        return float(mse / (var + 1e-9))

    def _metric_value(norm_mse: float, smape: Optional[float]) -> float:
        if metric_choice == "smape":
            return float(smape) if smape is not None and np.isfinite(smape) else float("inf")
        return norm_mse

    candidates = [
        {
            "name": "arima",
            "mse": mse_arima,
            "norm_mse": norm(mse_arima),
            "smape": smape_arima,
        },
        {
            "name": "ses",
            "mse": mse_ses,
            "norm_mse": norm(mse_ses),
            "smape": smape_ses,
        },
        {
            "name": "holt",
            "mse": mse_holt,
            "norm_mse": norm(mse_holt),
            "smape": smape_holt,
        },
        {
            "name": "autoreg",
            "mse": mse_autoreg,
            "norm_mse": norm(mse_autoreg),
            "smape": smape_autoreg,
        },
    ]

    for c in candidates:
        c["selection_score"] = _metric_value(c["norm_mse"], c["smape"])

    candidates_sorted = sorted(candidates, key=lambda x: x["selection_score"])
    candidate_by_name = {c["name"]: c for c in candidates_sorted}
    chosen = candidates_sorted[0]["name"]

    # Detect mild annual seasonality signal for tie-breaks on longer monthly series.
    seasonal_strength = float("nan")
    if len(monthly_series_proc) >= 18:
        try:
            seasonal_strength = float(monthly_series_proc.autocorr(lag=12))
        except Exception:
            seasonal_strength = float("nan")
    has_detected_seasonality = np.isfinite(seasonal_strength) and seasonal_strength >= 0.35

    baseline_selection_score = (
        baseline_smape if metric_choice == "smape" else norm(baseline_mse)
    )
    selected_score = candidate_by_name[chosen]["selection_score"]
    selection_reason = "best_candidate"

    # If SES is only marginally better but seasonality exists, prefer a non-SES model.
    if chosen == "ses" and has_detected_seasonality and np.isfinite(selected_score):
        for c in candidates_sorted:
            if c["name"] == "ses":
                continue
            if np.isfinite(c["selection_score"]) and c["selection_score"] <= selected_score * 1.03:
                chosen = c["name"]
                selected_score = c["selection_score"]
                selection_reason = "seasonality_tiebreak"
                break

    # Safety: check if chosen model's normalized MSE is unstable
    chosen_norm_mse = candidate_by_name.get(chosen, {}).get("norm_mse", float("inf"))
    if not np.isfinite(chosen_norm_mse) or chosen_norm_mse > MAX_NORMALIZED_MSE:
        print(
            f"⚠️ A model választás bizonytalan (norm_mse={chosen_norm_mse}); "
            "választás egyszerűsítése."
        )
        selection_reason = "stability_fallback"
        if len(monthly_series_proc) >= 12:
            chosen = 'ses' if np.var(monthly_series_proc.values) == 0 else 'holt'
        else:
            chosen = 'holt'
        selected_score = candidate_by_name.get(chosen, {}).get("selection_score", float("inf"))

    # If ARIMA was chosen but has negative R2, switch to simpler model
    if chosen == 'arima' and not np.isfinite(r2_arima):
        pass
    elif chosen == 'arima' and r2_arima < 0:
        print(f"⚠️ ARIMA WF R2 negatív ({r2_arima:.3f}), váltás egyszerűbb modellre.")
        chosen = 'holt'
        selection_reason = "arima_negative_r2"
        selected_score = candidate_by_name.get(chosen, {}).get("selection_score", float("inf"))

    # Baseline gating: only upgrade if chosen model beats seasonal-naive by a margin
    if np.isfinite(baseline_selection_score):
        chosen_selection_score = candidate_by_name.get(chosen, {}).get("selection_score", selected_score)
        improvement_threshold = baseline_selection_score * (1.0 - BASELINE_REL_IMPROVEMENT)
        if np.isfinite(chosen_selection_score) and chosen_selection_score > improvement_threshold:
            if verbose:
                print(
                    "⚠️ A választott modell nem veri a baseline-t elég erősen; "
                    "baseline használata."
                )
            chosen = "baseline"
            selected_score = baseline_selection_score
            selection_reason = "baseline_gate"
        else:
            selected_score = chosen_selection_score

    mean_forecast = None
    ci = None

    def _forecast_is_sane(fc: pd.Series, orig: pd.Series,
                         scale_factor: float = FORECAST_SCALE_FACTOR) -> bool:
        """Check if forecast values are numerically reasonable."""
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

    def try_model(model_name: str) -> bool:
        """Try fitting a specific model."""
        nonlocal mean_forecast, ci

        if model_name == "baseline":
            mean_forecast = seasonal_naive(monthly_series_proc, FORECAST_STEPS)
            ci = None
        elif model_name == "holt":
            mean_forecast, ci = fit_and_forecast_holt(monthly_series_proc, steps=FORECAST_STEPS)
        elif model_name == "ses":
            mean_forecast, ci = fit_and_forecast_ses(monthly_series_proc, steps=FORECAST_STEPS)
        elif model_name == "autoreg":
            _, mean_forecast, ci = fit_and_forecast_autoreg(monthly_series_proc, lags=8,
                                                            steps=FORECAST_STEPS)
        elif model_name == "arima":
            # Use SARIMAX if exog available
            if exog is not None:
                _, mean_forecast, ci = fit_and_forecast_sarimax(
                    monthly_series_proc, order=ARIMA_ORDER,
                    seasonal_order=seasonal_order, steps=FORECAST_STEPS, use_log=False,
                    exog=exog, exog_forecast=exog_forecast)
            else:
                _, mean_forecast, ci = fit_and_forecast_arima(
                    monthly_series_proc, order=ARIMA_ORDER,
                    steps=FORECAST_STEPS, use_log=False)

        return _forecast_is_sane(mean_forecast, monthly_series_proc,
                                scale_factor=FORECAST_SCALE_FACTOR)

    # Try primary model
    ok = try_model(chosen)

    if not ok:
        print(f"⚠️ A választott modell ({chosen}) numerikailag gyanús vagy nem futott: {mean_forecast}")

        # Fallback 1: SARIMAX
        _, mean_sar, ci_sar = fit_and_forecast_sarimax(
            monthly_series_proc, order=ARIMA_ORDER, seasonal_order=seasonal_order,
            steps=FORECAST_STEPS, use_log=False)

        if _forecast_is_sane(mean_sar, monthly_series_proc,
                            scale_factor=FORECAST_SCALE_FACTOR):
            mean_forecast, ci = mean_sar, ci_sar
            print("✅ SARIMAX fallback ok.")
        else:
            # Fallback 2: Time regression
            _, tr_preds, _ = fit_and_forecast_time_regression_boosted(
                monthly_series_proc, steps=FORECAST_STEPS, lags_for_features=3)

            if _forecast_is_sane(tr_preds, monthly_series_proc,
                                scale_factor=FORECAST_SCALE_FACTOR):
                mean_forecast, ci = tr_preds, None
                print("✅ Time-reg fallback ok.")
            else:
                # Fallback 3: Holt
                mean_h, ci_h = fit_and_forecast_holt(monthly_series_proc,
                                                     steps=FORECAST_STEPS)

                if _forecast_is_sane(mean_h, monthly_series_proc,
                                    scale_factor=FORECAST_SCALE_FACTOR):
                    mean_forecast, ci = mean_h, ci_h
                    print("✅ Holt fallback ok.")
                else:
                    # Fallback 4: Seasonal naive
                    mean_forecast = seasonal_naive(monthly_series_proc, FORECAST_STEPS)
                    ci = None
                    print("✅ Seasonal-naive final fallback ok.")

    # Check for flat forecasts and apply fallback
    if is_flat(mean_forecast, rel_tol=0.01):
        print("⚠️ Forecast túl lapos — próbálkozom AutoReg/time-reg fallback-kel.")

        _, ar_preds, _ = fit_and_forecast_autoreg(monthly_series_proc, lags=8,
                                                  steps=FORECAST_STEPS)
        if ar_preds is not None and not is_flat(ar_preds, rel_tol=0.01):
            mean_forecast = ar_preds
            ci = None
            print("✅ AutoReg fallback sikeres.")
        else:
            _, tr_preds, _ = fit_and_forecast_time_regression_boosted(
                monthly_series_proc, steps=FORECAST_STEPS, lags_for_features=3)

            if tr_preds is not None:
                mean_forecast = tr_preds
                ci = None
                print("✅ Time-reg fallback sikeres.")

    # Ensure pd.Series index
    if isinstance(mean_forecast, (np.ndarray, list)):
        mean_forecast = pd.Series(
            mean_forecast,
            index=pd.date_range(start=monthly_series_proc.index[-1] + pd.offsets.MonthEnd(1),
                               periods=len(mean_forecast), freq="ME"))

    # Clamp negative and extremely large values
    try:
        mean_forecast = mean_forecast.clip(lower=0.0)
        max_allowed = max(monthly_series_proc.max() * 20.0, MAX_OUTPUT_CAP)
        mean_forecast = mean_forecast.clip(upper=max_allowed)
        if ci is not None:
            ci["lower"] = ci["lower"].clip(lower=0.0)
            ci["upper"] = ci["upper"].clip(upper=max_allowed)
    except Exception:
        pass

    # Generate baseline for comparison
    try:
        baseline_vals = seasonal_naive(monthly_series_proc, FORECAST_STEPS)
    except Exception:
        baseline_vals = None

    plot_results(monthly_series_proc, forecast_mean=mean_forecast, forecast_ci=ci,
                 baseline_preds=baseline_vals, plot=plot)

    # Print chosen model's predictions at the very end (after all processing)
    if verbose:
        print("\n" + "="*70)
        print(f"✅ VÁLASZTOTT MODELL: {chosen.upper()}")
        print("="*70)
        print("Előrejelzés (pontbecslés) – index, érték:")
        if mean_forecast is not None and isinstance(mean_forecast, pd.Series):
            for idx, val in mean_forecast.items():
                idx_str = idx.strftime("%Y-%m") if hasattr(idx, "strftime") else str(idx)
                print(f"  {idx_str}: {float(val):.2f}")
        print("="*70 + "\n")

    fc_series = pd.Series(mean_forecast.values, index=mean_forecast.index)
    fc_ci = ci

    metrics = {
        "wf_mse_arima": mse_arima,
        "wf_mse_ses": mse_ses,
        "wf_mse_holt": mse_holt,
        "wf_mse_autoreg": mse_autoreg,
        "wf_mse_baseline": baseline_mse,
        "wf_mae_arima": mae_arima,
        "wf_mae_ses": mae_ses,
        "wf_mae_holt": mae_holt,
        "wf_mae_autoreg": mae_autoreg,
        "wf_mae_baseline": baseline_mae,
        "wf_smape_arima": smape_arima,
        "wf_smape_ses": smape_ses,
        "wf_smape_holt": smape_holt,
        "wf_smape_autoreg": smape_autoreg,
        "wf_smape_baseline": baseline_smape,
        "metric_choice": metric_choice,
        "baseline_selection_score": baseline_selection_score if np.isfinite(baseline_selection_score) else None,
        "selected_score": selected_score if np.isfinite(selected_score) else None,
        "selection_reason": selection_reason,
        "seasonal_strength_lag12": seasonal_strength if np.isfinite(seasonal_strength) else None,
        "has_detected_seasonality": bool(has_detected_seasonality),
        "zero_ratio": zero_ratio,
        "series_skew": skew_val,
        "backtest_window_size": n_test,
        "backtest_start": backtest_start.strftime("%Y-%m") if backtest_start is not None else None,
        "backtest_end": backtest_end.strftime("%Y-%m") if backtest_end is not None else None,
        "exog_forecast_method": _infer_exog_forecast_method(exog, exog_forecast),
        "chosen_model": chosen
    }

    return fc_series, fc_ci, metrics

