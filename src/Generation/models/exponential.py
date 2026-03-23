#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exponential smoothing models (SES and Holt).
"""

import numpy as np
import pandas as pd
from typing import Optional, Tuple

from statsmodels.tsa.holtwinters import SimpleExpSmoothing, Holt

from src.Generation.config import CI_ALPHA, Z_SCORE_FOR_CI, FORECAST_STEPS


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
        mean = pd.Series(mean.values, index=idx, name="holt_forecast")
        ci = pd.DataFrame({"lower": lower, "upper": upper}, index=idx)
        ci["lower"] = ci["lower"].clip(lower=0.0)
        return mean, ci

    except Exception as e:
        print(f"⚠️ Holt fit error: {e}")
        return None, None

