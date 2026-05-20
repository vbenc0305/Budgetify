#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Behavior-aware forecasting models for short, volatile monthly series.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Any, Dict, Optional, Tuple

from sklearn.ensemble import GradientBoostingRegressor

from src.Generation.config import (
    FORECAST_STEPS,
    BEHAVIORAL_MIN_LAGS,
    BEHAVIORAL_MAX_LAGS,
    BEHAVIORAL_RECENCY_WEIGHT_MAX,
    BEHAVIORAL_SPIKE_WEIGHT,
    BEHAVIORAL_TURN_WEIGHT,
    BEHAVIORAL_SPIKE_DECAY,
    BEHAVIORAL_MOMENTUM_DECAY,
    BEHAVIORAL_ACCEL_DECAY,
    BEHAVIORAL_DELTA_STD_CAP,
    BEHAVIORAL_DELTA_REL_CAP,
    BEHAVIORAL_REBOUND_GAIN,
    BEHAVIORAL_PERSISTENCE_GAIN,
    BEHAVIORAL_REBOUND_DECAY,
    BEHAVIORAL_SIGNATURE_DECAY,
    BEHAVIORAL_VARIANCE_FLOOR_RATIO,
    Z_SCORE_FOR_CI,
)
from src.Generation.utils import ensure_monthly_freq


BEHAVIORAL_MODEL_NAME = "behavioral_quantile_boost"
BehavioralTrainingData = Tuple[pd.DataFrame, list[str], np.ndarray, np.ndarray, np.ndarray, np.ndarray]


def _exclude_partial_last_month(series: pd.Series) -> Tuple[pd.Series, bool]:
    if len(series) < 6:
        return series, False

    try:
        last_idx = pd.Timestamp(series.index[-1])
        today = pd.Timestamp.today()
    except Exception:
        return series, False

    # Guard against dropping true historical month-end values.
    if last_idx.to_period("M") != today.to_period("M"):
        return series, False

    prev_window = series.iloc[-5:-1].astype(float)
    if prev_window.empty:
        return series, False

    last_val = float(series.iloc[-1])
    prev_mean = float(prev_window.mean())
    prev_median = float(prev_window.median())
    is_partial = (
        last_val < 0.65 * max(prev_mean, 1.0)
        and last_val < 0.72 * max(prev_median, 1.0)
    )
    if not is_partial or len(series) <= 4:
        return series, False

    return series.iloc[:-1].copy(), True


def _coerce_exog(
    series: pd.Series,
    exog: Optional[pd.DataFrame],
    steps: int,
    exog_forecast: Optional[pd.DataFrame] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    exog_hist = pd.DataFrame(index=series.index)
    if exog is not None and isinstance(exog, pd.DataFrame) and not exog.empty:
        exog_hist = exog.reindex(series.index)
        exog_hist = exog_hist.apply(pd.to_numeric, errors="coerce").ffill().fillna(0.0)

    future_idx = pd.date_range(
        start=series.index[-1] + pd.offsets.MonthEnd(1), periods=steps, freq="ME"
    )
    exog_future = pd.DataFrame(index=future_idx)

    if exog_hist.empty:
        return exog_hist, exog_future

    if exog_forecast is not None and isinstance(exog_forecast, pd.DataFrame) and not exog_forecast.empty:
        exog_future = exog_forecast.reindex(future_idx)
        exog_future = exog_future.apply(pd.to_numeric, errors="coerce").ffill().fillna(0.0)
        missing_cols = [c for c in exog_hist.columns if c not in exog_future.columns]
        for col in missing_cols:
            exog_future[col] = float(exog_hist.iloc[-1].get(col, 0.0))
        exog_future = exog_future[exog_hist.columns]
    else:
        last_row = exog_hist.iloc[-1].values.reshape(1, -1)
        exog_future = pd.DataFrame(
            np.tile(last_row, (steps, 1)),
            index=future_idx,
            columns=exog_hist.columns,
        )

    return exog_hist, exog_future


def _choose_lags(n: int, requested: int) -> int:
    upper = min(BEHAVIORAL_MAX_LAGS, requested, max(1, n - 2))
    lower = min(BEHAVIORAL_MIN_LAGS, upper)
    return max(lower, upper)


def _build_feature_frame(series: pd.Series, lags: int) -> pd.DataFrame:
    df = pd.DataFrame({"y": series.astype(float).values}, index=series.index)
    for i in range(1, lags + 1):
        df[f"lag{i}"] = df["y"].shift(i)

    shifted = df["y"].shift(1)
    df["roll_mean_3"] = shifted.rolling(3, min_periods=1).mean()
    df["roll_mean_6"] = shifted.rolling(6, min_periods=1).mean()
    df["roll_std_3"] = shifted.rolling(3, min_periods=1).std(ddof=0).fillna(0.0)
    df["roll_std_6"] = shifted.rolling(6, min_periods=1).std(ddof=0).fillna(0.0)
    df["roll_max_3"] = shifted.rolling(3, min_periods=1).max()
    df["roll_min_3"] = shifted.rolling(3, min_periods=1).min()
    df["momentum_1"] = df["lag1"] - df["lag2"]
    df["momentum_2"] = df["lag2"] - df["lag3"] if lags >= 3 else 0.0
    df["acceleration"] = df["momentum_1"] - df["momentum_2"]
    denom3 = df["roll_mean_3"].abs() + 1.0
    df["ratio_to_mean_3"] = df["lag1"] / denom3
    df["shock_z"] = (df["lag1"] - df["roll_mean_3"]) / (df["roll_std_3"] + 1.0)
    df["range_3"] = df["roll_max_3"] - df["roll_min_3"]
    df["cv_3"] = df["roll_std_3"] / denom3
    df["month_sin"] = np.sin(2 * np.pi * (df.index.month - 1) / 12.0)
    df["month_cos"] = np.cos(2 * np.pi * (df.index.month - 1) / 12.0)
    df["quarter_sin"] = np.sin(2 * np.pi * (df.index.quarter - 1) / 4.0)
    df["quarter_cos"] = np.cos(2 * np.pi * (df.index.quarter - 1) / 4.0)
    df["t"] = np.arange(len(df), dtype=float)
    return df


def _feature_columns(lags: int, exog_cols: list[str]) -> list[str]:
    lag_cols = [f"lag{i}" for i in range(1, lags + 1)]
    base_cols = [
        "roll_mean_3",
        "roll_mean_6",
        "roll_std_3",
        "roll_std_6",
        "roll_max_3",
        "roll_min_3",
        "momentum_1",
        "momentum_2",
        "acceleration",
        "ratio_to_mean_3",
        "shock_z",
        "range_3",
        "cv_3",
        "month_sin",
        "month_cos",
        "quarter_sin",
        "quarter_cos",
        "t",
    ]
    return lag_cols + base_cols + exog_cols


def _prepare_training_data(
    series: pd.Series,
    lags: int,
    exog_hist: pd.DataFrame,
) -> BehavioralTrainingData:
    df = _build_feature_frame(series, lags)
    exog_cols: list[str] = []
    if not exog_hist.empty:
        prefixed = exog_hist.add_prefix("exog_")
        df = df.join(prefixed, how="left")
        exog_cols = list(prefixed.columns)

    df["delta_target"] = df["y"] - df["lag1"]
    feat_cols = _feature_columns(lags, exog_cols)
    df = df.dropna()

    if df.empty:
        raise ValueError("Behavioral model has no valid training rows")

    target = df["y"].to_numpy(dtype=float)
    delta_target = df["delta_target"].to_numpy(dtype=float)
    X = df[feat_cols].to_numpy(dtype=float)

    recent_weights = np.linspace(1.0, BEHAVIORAL_RECENCY_WEIGHT_MAX, len(df))
    spike_ref = df["roll_std_3"].to_numpy(dtype=float) + 1.0
    spike_mask = np.abs(delta_target) >= spike_ref
    turn_mask = np.sign(delta_target) != np.sign(df["momentum_1"].to_numpy(dtype=float))
    weights = recent_weights * np.where(spike_mask, BEHAVIORAL_SPIKE_WEIGHT, 1.0)
    weights *= np.where(turn_mask, BEHAVIORAL_TURN_WEIGHT, 1.0)
    training_data: BehavioralTrainingData = (df, feat_cols, X, target, delta_target, weights)
    return training_data


def _fit_models(
    X: np.ndarray,
    y: np.ndarray,
    delta_y: np.ndarray,
    weights: np.ndarray,
) -> Dict[str, GradientBoostingRegressor]:
    level_model = GradientBoostingRegressor(
        loss="huber",
        learning_rate=0.04,
        n_estimators=180,
        max_depth=2,
        subsample=0.9,
        random_state=42,
    )
    delta_model = GradientBoostingRegressor(
        loss="huber",
        learning_rate=0.05,
        n_estimators=160,
        max_depth=2,
        subsample=0.95,
        random_state=43,
    )
    q_low_model = GradientBoostingRegressor(
        loss="quantile",
        alpha=0.15,
        learning_rate=0.05,
        n_estimators=140,
        max_depth=2,
        subsample=0.95,
        random_state=44,
    )
    q_high_model = GradientBoostingRegressor(
        loss="quantile",
        alpha=0.85,
        learning_rate=0.05,
        n_estimators=140,
        max_depth=2,
        subsample=0.95,
        random_state=45,
    )

    level_model.fit(X, y, sample_weight=weights)
    delta_model.fit(X, delta_y, sample_weight=weights)
    q_low_model.fit(X, y, sample_weight=weights)
    q_high_model.fit(X, y, sample_weight=weights)

    return {
        "level": level_model,
        "delta": delta_model,
        "q_low": q_low_model,
        "q_high": q_high_model,
    }


def _make_feature_row(
    history: pd.Series,
    lags: int,
    step_index: int,
    exog_row: Optional[pd.Series],
    exog_cols: list[str],
) -> pd.DataFrame:
    history = history.astype(float)
    row_index = pd.DatetimeIndex([history.index[-1] + pd.offsets.MonthEnd(1)])
    row = pd.DataFrame(index=row_index)
    last_vals = history.values
    for i in range(1, lags + 1):
        row[f"lag{i}"] = float(last_vals[-i]) if len(last_vals) >= i else float(last_vals[0])

    recent = history.tail(min(6, len(history)))
    recent3 = history.tail(min(3, len(history)))
    recent_std_3 = float(recent3.std(ddof=0)) if len(recent3) > 1 else 0.0
    recent_std_6 = float(recent.std(ddof=0)) if len(recent) > 1 else recent_std_3
    row["roll_mean_3"] = float(recent3.mean())
    row["roll_mean_6"] = float(recent.mean())
    row["roll_std_3"] = recent_std_3
    row["roll_std_6"] = recent_std_6
    row["roll_max_3"] = float(recent3.max())
    row["roll_min_3"] = float(recent3.min())

    lag1 = float(row["lag1"].iloc[0])
    lag2 = float(row["lag2"].iloc[0]) if "lag2" in row else lag1
    lag3 = float(row["lag3"].iloc[0]) if "lag3" in row else lag2
    momentum_1 = lag1 - lag2
    momentum_2 = lag2 - lag3
    row["momentum_1"] = momentum_1
    row["momentum_2"] = momentum_2
    row["acceleration"] = momentum_1 - momentum_2
    row["ratio_to_mean_3"] = lag1 / (abs(float(row["roll_mean_3"].iloc[0])) + 1.0)
    row["shock_z"] = (lag1 - float(row["roll_mean_3"].iloc[0])) / (recent_std_3 + 1.0)
    row["range_3"] = float(row["roll_max_3"].iloc[0] - row["roll_min_3"].iloc[0])
    row["cv_3"] = recent_std_3 / (abs(float(row["roll_mean_3"].iloc[0])) + 1.0)

    future_month = row_index[0].month
    future_quarter = row_index[0].quarter
    row["month_sin"] = np.sin(2 * np.pi * (future_month - 1) / 12.0)
    row["month_cos"] = np.cos(2 * np.pi * (future_month - 1) / 12.0)
    row["quarter_sin"] = np.sin(2 * np.pi * (future_quarter - 1) / 4.0)
    row["quarter_cos"] = np.cos(2 * np.pi * (future_quarter - 1) / 4.0)
    row["t"] = float(len(history) + step_index)

    for col in exog_cols:
        source_name = col.replace("exog_", "", 1)
        row[col] = float(exog_row.get(source_name, 0.0)) if exog_row is not None else 0.0

    return row


def _behavioral_postprocess(
    history: pd.Series,
    step: int,
    level_pred: float,
    delta_pred: float,
    q_low: float,
    q_high: float,
) -> Dict[str, float]:
    recent = history.tail(min(6, len(history))).astype(float)
    recent3 = history.tail(min(3, len(history))).astype(float)
    last_val = float(history.iloc[-1])
    recent_mean = float(recent.mean()) if len(recent) > 0 else last_val
    recent_std = float(recent.std(ddof=0)) if len(recent) > 1 else 0.0
    diffs = recent.diff().dropna().astype(float)
    median_diff = float(diffs.median()) if len(diffs) > 0 else 0.0
    accel = float(diffs.iloc[-1] - diffs.iloc[-2]) if len(diffs) >= 2 else 0.0
    last_diff = float(diffs.iloc[-1]) if len(diffs) > 0 else 0.0
    prior_diffs = diffs.iloc[:-1] if len(diffs) > 1 else diffs.iloc[0:0]
    prior_scale = float(np.median(np.abs(prior_diffs))) if len(prior_diffs) > 0 else abs(last_diff)
    prior_scale = max(prior_scale, recent_std, 1.0)
    prior_trend = float(prior_diffs.median()) if len(prior_diffs) > 0 else median_diff
    recent_baseline = float(recent3.median()) if len(recent3) > 0 else recent_mean
    shock = last_val - recent_baseline
    shock_scale = abs(shock) / (recent_std + 1.0)

    delta_cap = max(
        BEHAVIORAL_DELTA_STD_CAP * max(recent_std, 1.0),
        BEHAVIORAL_DELTA_REL_CAP * max(recent_mean, 1.0),
        float(np.max(np.abs(diffs))) if len(diffs) > 0 else 0.0,
    )
    delta_adj = float(np.clip(delta_pred, -delta_cap, delta_cap))
    level_from_delta = last_val + delta_adj

    spike_strength = 0.0
    if shock_scale >= 1.25:
        spike_strength = 0.62
    elif shock_scale >= 0.75:
        spike_strength = 0.40
    elif shock_scale >= 0.40:
        spike_strength = 0.24

    isolated_shock = (
        abs(last_diff) >= 1.35 * prior_scale
        and (np.sign(last_diff) != np.sign(prior_trend) or abs(last_diff) >= 2.0 * prior_scale)
    )
    if isolated_shock:
        shock_component = (-shock) * spike_strength * BEHAVIORAL_REBOUND_GAIN * (BEHAVIORAL_REBOUND_DECAY ** step)
    else:
        shock_component = shock * spike_strength * BEHAVIORAL_PERSISTENCE_GAIN * (BEHAVIORAL_SPIKE_DECAY ** step)

    momentum_component = median_diff * 0.40 * (BEHAVIORAL_MOMENTUM_DECAY ** step)
    accel_component = np.clip(accel, -delta_cap, delta_cap) * 0.30 * (BEHAVIORAL_ACCEL_DECAY ** step)

    pred = 0.42 * level_pred + 0.58 * level_from_delta
    pred = pred + shock_component + momentum_component + accel_component

    dynamic_floor = max(0.0, recent_mean - 2.6 * recent_std)
    dynamic_cap = max(
        float(history.max()) * 1.75,
        recent_mean + 3.4 * max(recent_std, 1.0) + abs(shock_component),
        last_val + delta_cap,
    )
    pred = float(np.clip(pred, dynamic_floor, dynamic_cap))

    spread_base = max(q_high - q_low, recent_std * 1.15, abs(pred - level_pred) * 0.8)
    lower = max(0.0, pred - 0.65 * Z_SCORE_FOR_CI * spread_base)
    upper = pred + 0.95 * Z_SCORE_FOR_CI * spread_base
    return {
        "pred": float(pred),
        "lower": float(lower),
        "upper": float(max(lower, upper)),
    }


def _enforce_behavioral_variability(
    history: pd.Series,
    forecast: pd.Series,
    ci: Optional[pd.DataFrame],
) -> Tuple[pd.Series, Optional[pd.DataFrame]]:
    recent = history.tail(min(6, len(history))).astype(float)
    diffs = recent.diff().dropna().astype(float)
    if len(diffs) < 2 or len(forecast) < 2:
        return forecast, ci

    forecast_std = float(forecast.std(ddof=0)) if len(forecast) > 1 else 0.0
    recent_diff_std = float(diffs.std(ddof=0)) if len(diffs) > 1 else 0.0
    recent_range = float(recent.max() - recent.min()) if len(recent) > 0 else 0.0
    target_std = max(
        BEHAVIORAL_VARIANCE_FLOOR_RATIO * max(recent_diff_std, 1.0),
        0.12 * recent_range,
    )
    if forecast_std >= target_std:
        return forecast, ci

    signature_src = diffs.tail(min(4, len(diffs))).to_numpy(dtype=float)
    if signature_src.size == 0:
        return forecast, ci
    signature = np.resize(signature_src, len(forecast))
    signature = signature - float(np.mean(signature))
    sig_std = float(np.std(signature))
    if sig_std <= 1e-9:
        return forecast, ci
    signature = signature / sig_std

    amplitude = max(target_std - forecast_std, 0.0)
    amplitude = min(amplitude, 0.55 * max(recent_diff_std, recent_range / 3.0, 1.0))
    decay = np.array([BEHAVIORAL_SIGNATURE_DECAY ** i for i in range(len(forecast))], dtype=float)
    adjustments = amplitude * signature * decay

    adjusted = forecast.astype(float).copy()
    adjusted_vals = adjusted.values + adjustments
    lower_bound = max(0.0, float(recent.mean()) - 2.4 * max(float(recent.std(ddof=0)), 1.0))
    upper_bound = max(float(history.max()) * 1.8, float(recent.mean()) + 3.5 * max(float(recent.std(ddof=0)), 1.0))
    adjusted[:] = np.clip(adjusted_vals, lower_bound, upper_bound)

    if ci is not None:
        ci = ci.copy()
        spread = np.maximum(ci["upper"].values - ci["lower"].values, np.abs(adjustments) * 1.2)
        ci["lower"] = np.clip(adjusted.values - 0.55 * spread, 0.0, None)
        ci["upper"] = np.maximum(adjusted.values + 0.80 * spread, ci["lower"].values)

    return adjusted, ci


def fit_and_forecast_behavioral_boosted(
    series: pd.Series,
    steps: int = FORECAST_STEPS,
    lags: int = BEHAVIORAL_MAX_LAGS,
    exog: Optional[pd.DataFrame] = None,
    exog_forecast: Optional[pd.DataFrame] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[pd.Series], Optional[pd.DataFrame]]:
    """
    Forecast with recency-weighted gradient boosting plus explicit shock persistence.

    The model intentionally learns recent behavioral shifts instead of collapsing
    everything toward a low-variance monthly average.
    """
    try:
        series_norm = ensure_monthly_freq(series)
        if series_norm is None:
            return None, None, None
        series = series_norm.astype(float)
        study_series, partial_last_month_excluded = _exclude_partial_last_month(series)
        if len(study_series) < 4:
            study_series = series
            partial_last_month_excluded = False

        n = len(study_series)
        if n < 4:
            return None, None, None

        used_lags = _choose_lags(n, lags)
        exog_hist, exog_future = _coerce_exog(study_series, exog, steps=steps, exog_forecast=exog_forecast)
        train_df, feat_cols, X, y, delta_y, weights = _prepare_training_data(study_series, used_lags, exog_hist)
        models = _fit_models(X, y, delta_y, weights)

        history = study_series.copy()
        preds: list[float] = []
        lowers: list[float] = []
        uppers: list[float] = []
        exog_cols = [c for c in feat_cols if c.startswith("exog_")]

        for step in range(steps):
            exog_row = exog_future.iloc[step] if not exog_future.empty and step < len(exog_future) else None
            feat_row = _make_feature_row(history, used_lags, step, exog_row, exog_cols)
            feat_input = feat_row[feat_cols].to_numpy(dtype=float)

            level_pred = float(models["level"].predict(feat_input)[0])
            delta_pred = float(models["delta"].predict(feat_input)[0])
            q_low_raw = float(models["q_low"].predict(feat_input)[0])
            q_high_raw = float(models["q_high"].predict(feat_input)[0])
            q_low = min(q_low_raw, q_high_raw)
            q_high = max(q_low_raw, q_high_raw)
            postprocessed = _behavioral_postprocess(
                history=history,
                step=step,
                level_pred=level_pred,
                delta_pred=delta_pred,
                q_low=q_low,
                q_high=q_high,
            )
            pred = float(postprocessed["pred"])
            lower = float(postprocessed["lower"])
            upper = float(postprocessed["upper"])

            future_idx = history.index[-1] + pd.offsets.MonthEnd(1)
            preds.append(pred)
            lowers.append(lower)
            uppers.append(upper)
            history = pd.concat([history, pd.Series([pred], index=[future_idx])])
            history_norm = ensure_monthly_freq(history)
            if history_norm is not None:
                history = history_norm

        idx = pd.date_range(start=study_series.index[-1] + pd.offsets.MonthEnd(1), periods=steps, freq="ME")
        forecast = pd.Series(preds, index=idx, name=f"{BEHAVIORAL_MODEL_NAME}_forecast").clip(lower=0.0)
        ci = pd.DataFrame({"lower": lowers, "upper": uppers}, index=idx)
        ci["lower"] = ci["lower"].clip(lower=0.0)
        ci["upper"] = np.maximum(ci["upper"], ci["lower"])
        forecast, ci = _enforce_behavioral_variability(study_series, forecast, ci)

        model_info: Dict[str, Any] = {
            "name": BEHAVIORAL_MODEL_NAME,
            "lags": used_lags,
            "feature_columns": feat_cols,
            "training_rows": int(len(train_df)),
            "exog_columns": [c.replace("exog_", "", 1) for c in exog_cols],
            "partial_last_month_excluded": bool(partial_last_month_excluded),
            "study_points": int(len(study_series)),
        }
        return model_info, forecast, ci

    except Exception as e:
        print(f"⚠️ Behavioral boost fit error: {e}")
        return None, None, None

