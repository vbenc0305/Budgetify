#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exponential smoothing models (SES and Holt).
"""

import numpy as np
import pandas as pd
from typing import Optional, Tuple

from statsmodels.tsa.holtwinters import SimpleExpSmoothing, Holt, ExponentialSmoothing

from src.Generation.config import (
    Z_SCORE_FOR_CI,
    FORECAST_STEPS,
    ETS_SIGNATURE_MIN_POINTS,
    ETS_SIGNATURE_MIN_LAG12_AUTOCORR,
    ETS_SIGNATURE_MAX_REL_ADJ,
    ETS_SIGNATURE_DECAY,
)


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


def fit_and_forecast_ses(
    series: pd.Series,
    steps: int = FORECAST_STEPS
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
        return mean, ci

    except Exception as e:
        print(f"⚠️ SES fit error: {e}")
        return None, None


def fit_and_forecast_holt(
    series: pd.Series,
    steps: int = FORECAST_STEPS
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
        return mean, ci

    except Exception as e:
        print(f"⚠️ Holt fit error: {e}")
        return None, None


def fit_and_forecast_ets(
    series: pd.Series,
    steps: int = FORECAST_STEPS,
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
        return mean, ci

    except Exception as e:
        print(f"⚠️ ETS fit error: {e}")
        return None, None


