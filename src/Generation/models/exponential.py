#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exponential smoothing models (SES and Holt).
"""

import logging
from typing import Optional, Tuple

import numpy as np
import pandas as pd

from statsmodels.tsa.holtwinters import SimpleExpSmoothing, Holt, ExponentialSmoothing

from src.Generation.models.time_regression import fit_and_forecast_time_regression_boosted
from src.Generation.config import (
    Z_SCORE_FOR_CI,
    FORECAST_STEPS,
    ETS_SIGNATURE_MIN_POINTS,
    ETS_SIGNATURE_MIN_LAG12_AUTOCORR,
    ETS_SIGNATURE_MAX_REL_ADJ,
    ETS_SIGNATURE_DECAY,
)
from src.Generation.utils import ensure_monthly_freq


logger = logging.getLogger(__name__)


def _safe_lag12_autocorr(series: pd.Series) -> float:
    if len(series) < 13:
        return float("nan")
    try:
        return float(series.astype(float).autocorr(lag=12))
    except Exception:
        return float("nan")


def _apply_month_signature_adjustment(series: pd.Series, forecast: Optional[pd.Series]) -> Optional[pd.Series]:
    """
    Inject a conservative month-of-year signature into non-seasonal ETS forecasts.

    This keeps medium-length monthly forecasts from collapsing into an almost
    perfectly straight line when there is a detectable annual signature but not
    enough history for a full seasonal ETS fit.
    """
    if forecast is None or len(forecast) == 0 or len(series) < ETS_SIGNATURE_MIN_POINTS:
        return forecast

    lag12_autocorr = _safe_lag12_autocorr(series)
    if not np.isfinite(lag12_autocorr) or lag12_autocorr < ETS_SIGNATURE_MIN_LAG12_AUTOCORR:
        return forecast

    hist = series.astype(float)
    overall_mean = float(hist.mean())
    if not np.isfinite(overall_mean) or overall_mean <= 0.0:
        return forecast

    month_means = hist.groupby(hist.index.month).mean()
    month_counts = hist.groupby(hist.index.month).size()
    recent = hist.tail(min(12, len(hist)))
    recent_std = float(recent.std(ddof=0)) if len(recent) > 1 else float(hist.std(ddof=0))
    recent_std = max(recent_std, 1.0)
    season_strength = min(
        1.0,
        max(0.0, (lag12_autocorr - ETS_SIGNATURE_MIN_LAG12_AUTOCORR) / max(1e-9, 1.0 - ETS_SIGNATURE_MIN_LAG12_AUTOCORR)),
    )
    if season_strength <= 0.0:
        return forecast

    adjusted = forecast.astype(float).copy()
    for step_idx, ts in enumerate(adjusted.index):
        month = int(ts.month)
        month_mean = float(month_means.get(month, overall_mean))
        support = float(month_counts.get(month, 0))
        support_weight = min(1.0, support / 2.0)
        shrink = 0.55 * season_strength * support_weight
        raw_effect = month_mean - overall_mean
        max_adjustment = min(
            ETS_SIGNATURE_MAX_REL_ADJ * max(abs(float(adjusted.loc[ts])), 1.0),
            0.85 * recent_std,
        )
        seasonal_adjustment = float(
            np.clip(raw_effect * shrink * (ETS_SIGNATURE_DECAY ** step_idx), -max_adjustment, max_adjustment)
        )
        adjusted.loc[ts] = max(0.0, float(adjusted.loc[ts]) + seasonal_adjustment)

    return adjusted


def _apply_variability_floor(series: pd.Series, forecast: Optional[pd.Series]) -> Optional[pd.Series]:
    """
    Add a light decaying recent-signature component when the forecast is much
    smoother than the last few observed month-to-month moves.
    """
    if forecast is None or len(forecast) < 3 or len(series) < 6:
        return forecast

    recent = series.tail(min(6, len(series))).astype(float)
    diffs = recent.diff().dropna().astype(float)
    if len(diffs) < 2:
        return forecast

    forecast_std = float(forecast.std(ddof=0)) if len(forecast) > 1 else 0.0
    recent_diff_std = float(diffs.std(ddof=0)) if len(diffs) > 1 else 0.0
    recent_range = float(recent.max() - recent.min()) if len(recent) > 0 else 0.0
    target_std = max(0.10 * recent_range, 0.28 * max(recent_diff_std, 1.0))
    if forecast_std >= target_std:
        return forecast

    signature_src = diffs.tail(min(4, len(diffs))).to_numpy(dtype=float)
    if signature_src.size == 0:
        return forecast
    signature = np.resize(signature_src, len(forecast))
    signature = signature - float(np.mean(signature))
    sig_std = float(np.std(signature))
    if sig_std <= 1e-9:
        return forecast
    signature = signature / sig_std

    amplitude = max(target_std - forecast_std, 0.0)
    amplitude = min(amplitude, 0.32 * max(recent_diff_std, recent_range / 3.0, 1.0))
    decay = np.array([0.94 ** i for i in range(len(forecast))], dtype=float)
    adjustments = amplitude * signature * decay

    adjusted = forecast.astype(float).copy()
    lower_bound = max(0.0, float(recent.mean()) - 2.25 * max(float(recent.std(ddof=0)), 1.0))
    upper_bound = max(float(series.max()) * 1.65, float(recent.mean()) + 3.0 * max(float(recent.std(ddof=0)), 1.0))
    adjusted[:] = np.clip(adjusted.values + adjustments, lower_bound, upper_bound)
    return adjusted


def _prepare_exog_inputs(
    series: pd.Series,
    steps: int,
    exog: Optional[pd.DataFrame],
    exog_forecast: Optional[pd.DataFrame],
) -> tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    if exog is None or not isinstance(exog, pd.DataFrame) or exog.empty:
        return None, None

    exog_hist = exog.reindex(series.index)
    exog_hist = exog_hist.apply(pd.to_numeric, errors="coerce").ffill().fillna(0.0)
    if exog_hist.empty:
        return None, None

    future_idx = pd.date_range(start=series.index[-1] + pd.offsets.MonthEnd(1), periods=steps, freq="ME")
    if exog_forecast is not None and isinstance(exog_forecast, pd.DataFrame) and not exog_forecast.empty:
        exog_future = exog_forecast.reindex(future_idx)
        exog_future = exog_future.apply(pd.to_numeric, errors="coerce").ffill().fillna(0.0)
        missing_cols = [c for c in exog_hist.columns if c not in exog_future.columns]
        for col in missing_cols:
            exog_future[col] = float(exog_hist.iloc[-1].get(col, 0.0))
        exog_future = exog_future[exog_hist.columns]
    else:
        last_row = exog_hist.iloc[-1].values.reshape(1, -1)
        exog_future = pd.DataFrame(np.tile(last_row, (steps, 1)), index=future_idx, columns=exog_hist.columns)

    return exog_hist, exog_future


def _exog_blend_weight(series: pd.Series, exog_hist: pd.DataFrame) -> float:
    if exog_hist.empty or len(series) < 6:
        return 0.0

    corrs: list[float] = []
    target = pd.Series(series.astype(float).values, index=series.index)
    for col in exog_hist.columns:
        col_vals = pd.to_numeric(exog_hist[col], errors="coerce").ffill().fillna(0.0)
        if float(col_vals.std(ddof=0)) <= 1e-9:
            continue
        corr = float(abs(target.corr(col_vals)))
        if np.isfinite(corr):
            corrs.append(corr)

    if not corrs:
        return 0.0

    signal = float(np.mean(sorted(corrs, reverse=True)[: min(3, len(corrs))]))
    history_factor = min(1.0, len(series) / 18.0)
    return float(np.clip((0.12 + 0.28 * signal) * history_factor, 0.10, 0.34))


def _has_meaningful_future_exog_signal(
    exog_hist: pd.DataFrame,
    exog_future: pd.DataFrame,
    atol: float = 1e-9,
) -> bool:
    """Return True only when future exog contains real projected signal.

    If every non-deterministic future feature is effectively just the last known
    value carried forward, exog blending is more likely to inject unstable
    synthetic dynamics than to improve the base exponential forecast.
    """
    if exog_hist.empty or exog_future.empty:
        return False

    deterministic_cols = {
        "month_sin", "month_cos", "month",
        "is_start_of_month", "is_end_of_month",
        "quarter", "day_of_week", "day_of_month",
        "days_in_month", "week_of_year", "year",
    }
    informative_cols = [c for c in exog_hist.columns if c in exog_future.columns and c not in deterministic_cols]
    if not informative_cols:
        return False

    try:
        last_row = exog_hist.iloc[-1][informative_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
        future_vals = exog_future[informative_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
        if future_vals.empty:
            return False

        diff_from_last = (future_vals - last_row.values).abs()
        has_level_change = bool((diff_from_last > atol).any().any())
        has_internal_variation = bool((future_vals.nunique(dropna=False) > 1).any())
        return has_level_change or has_internal_variation
    except Exception:
        return False


def _apply_exog_adjustment(
    series: pd.Series,
    forecast: Optional[pd.Series],
    ci: Optional[pd.DataFrame],
    exog: Optional[pd.DataFrame],
    exog_forecast: Optional[pd.DataFrame],
    model_name: str,
) -> tuple[Optional[pd.Series], Optional[pd.DataFrame]]:
    if forecast is None or len(forecast) == 0:
        return forecast, ci

    exog_hist, exog_future = _prepare_exog_inputs(series, len(forecast), exog, exog_forecast)
    if exog_hist is None or exog_future is None:
        return forecast, ci
    if not _has_meaningful_future_exog_signal(exog_hist, exog_future):
        return forecast, ci

    weight = _exog_blend_weight(series, exog_hist)
    if weight <= 0.0:
        return forecast, ci

    try:
        series_norm = ensure_monthly_freq(series)
        series_for_exog = series_norm if series_norm is not None else series
        _, exog_fc, _ = fit_and_forecast_time_regression_boosted(
            series_for_exog,
            steps=len(forecast),
            exog=exog_hist,
            exog_forecast=exog_future,
        )
    except Exception:
        exog_fc = None

    if exog_fc is None or len(exog_fc) != len(forecast):
        return forecast, ci

    exog_fc = pd.Series(exog_fc.values, index=forecast.index, dtype=float, name=f"{model_name}_exog_fc")
    adjusted = forecast.astype(float) + weight * (exog_fc.astype(float) - forecast.astype(float))
    adjusted = adjusted.clip(lower=0.0)

    if ci is not None and isinstance(ci, pd.DataFrame) and {"lower", "upper"}.issubset(ci.columns):
        shifted_ci = ci.copy()
        shift = adjusted.values - forecast.values
        shifted_ci["lower"] = (shifted_ci["lower"].values + shift).clip(min=0.0)
        shifted_ci["upper"] = np.maximum(shifted_ci["upper"].values + shift, shifted_ci["lower"].values)
        ci = shifted_ci

    return adjusted, ci


def fit_and_forecast_ses(
    series: pd.Series,
    steps: int = FORECAST_STEPS,
    exog: Optional[pd.DataFrame] = None,
    exog_forecast: Optional[pd.DataFrame] = None,
) -> Tuple[Optional[pd.Series], Optional[pd.DataFrame]]:
    """
    Fit Simple Exponential Smoothing model.

    Args:
        series: Input time series
        steps: Number of forecast steps

    Returns:
        Tuple of (forecast_mean, confidence_interval)
    """
    try:
        model = SimpleExpSmoothing(series).fit(optimized=True)
        mean = model.forecast(steps)
        resid = model.fittedvalues - series
        resid_std = resid.std(ddof=1) if len(resid) > 1 else np.std(series)
        z = Z_SCORE_FOR_CI
        lower = mean - z * resid_std
        upper = mean + z * resid_std

        idx = pd.date_range(start=series.index[-1] + pd.offsets.MonthEnd(1),
                           periods=len(mean), freq="ME")
        mean = pd.Series(mean.values, index=idx, name="ses_forecast")
        ci = pd.DataFrame({"lower": lower, "upper": upper}, index=idx)
        ci["lower"] = ci["lower"].clip(lower=0.0)
        mean, ci = _apply_exog_adjustment(series, mean, ci, exog, exog_forecast, model_name="ses")
        return mean, ci

    except Exception as e:
        logger.warning("SES fit error: %s", e)
        return None, None


def fit_and_forecast_holt(
    series: pd.Series,
    steps: int = FORECAST_STEPS,
    exog: Optional[pd.DataFrame] = None,
    exog_forecast: Optional[pd.DataFrame] = None,
) -> Tuple[Optional[pd.Series], Optional[pd.DataFrame]]:
    """
    Fit Holt (exponential smoothing with trend) model.

    Args:
        series: Input time series
        steps: Number of forecast steps

    Returns:
        Tuple of (forecast_mean, confidence_interval)
    """
    try:
        model = Holt(series, exponential=False, damped_trend=True).fit(optimized=True)
        mean = model.forecast(steps)
        resid = model.fittedvalues - series
        resid_std = resid.std(ddof=1) if len(resid) > 1 else np.std(series)
        z = Z_SCORE_FOR_CI
        lower = mean - z * resid_std
        upper = mean + z * resid_std

        idx = pd.date_range(start=series.index[-1] + pd.offsets.MonthEnd(1),
                           periods=len(mean), freq="ME")
        raw_mean = pd.Series(mean.values, index=idx, name="holt_forecast")
        mean = _apply_month_signature_adjustment(series, raw_mean)
        mean = _apply_variability_floor(series, mean)
        shift = mean.values - raw_mean.values
        ci = pd.DataFrame({"lower": lower + shift, "upper": upper + shift}, index=idx)
        ci["lower"] = ci["lower"].clip(lower=0.0)
        mean, ci = _apply_exog_adjustment(series, mean, ci, exog, exog_forecast, model_name="holt")
        return mean, ci

    except Exception as e:
        logger.warning("Holt fit error: %s", e)
        return None, None


def fit_and_forecast_ets(
    series: pd.Series,
    steps: int = FORECAST_STEPS,
    exog: Optional[pd.DataFrame] = None,
    exog_forecast: Optional[pd.DataFrame] = None,
) -> Tuple[Optional[pd.Series], Optional[pd.DataFrame]]:
    """
    Fit ETS model (ExponentialSmoothing) with adaptive seasonal component.

    Uses additive trend and enables additive seasonality when there is
    enough monthly history.
    """
    try:
        use_seasonal = len(series) >= 24
        seasonal = "add" if use_seasonal else None
        seasonal_periods = 12 if use_seasonal else None

        model = ExponentialSmoothing(
            series,
            trend="add",
            damped_trend=True,
            seasonal=seasonal,
            seasonal_periods=seasonal_periods,
            initialization_method="estimated",
        ).fit(optimized=True)

        mean = model.forecast(steps)
        resid = model.fittedvalues - series
        resid_std = resid.std(ddof=1) if len(resid) > 1 else np.std(series)
        z = Z_SCORE_FOR_CI
        lower = mean - z * resid_std
        upper = mean + z * resid_std

        idx = pd.date_range(start=series.index[-1] + pd.offsets.MonthEnd(1),
                           periods=len(mean), freq="ME")
        raw_mean = pd.Series(mean.values, index=idx, name="ets_forecast")
        mean = raw_mean
        if not use_seasonal:
            mean = _apply_month_signature_adjustment(series, mean)
        mean = _apply_variability_floor(series, mean)
        shift = mean.values - raw_mean.values
        ci = pd.DataFrame({"lower": lower + shift, "upper": upper + shift}, index=idx)
        ci["lower"] = ci["lower"].clip(lower=0.0)
        ci["upper"] = ci[["upper", "lower"]].max(axis=1)
        mean, ci = _apply_exog_adjustment(series, mean, ci, exog, exog_forecast, model_name="ets")
        return mean, ci

    except Exception as e:
        logger.warning("ETS fit error: %s", e)
        return None, None


