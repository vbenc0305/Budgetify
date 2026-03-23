#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARIMA and SARIMAX model fitting and forecasting.
"""

import numpy as np
import pandas as pd
from typing import Optional, Tuple

from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX

from src.Generation.config import (
    ARIMA_ORDER, SEASONAL_ORDER, CI_ALPHA,
    FORECAST_STEPS
)
from src.Generation.utils import safe_expm1_arr


def fit_and_forecast_arima(
    series: pd.Series,
    order: Tuple[int, int, int] = ARIMA_ORDER,
    steps: int = FORECAST_STEPS,
    use_log: bool = False
) -> Tuple[Optional[object], Optional[pd.Series], Optional[pd.DataFrame]]:
    """
    Fit ARIMA model and generate forecasts.

    Important: use_log=False by default to avoid exp overflow.

    Args:
        series: Input time series
        order: ARIMA order (p, d, q)
        steps: Number of forecast steps
        use_log: Whether to apply log transformation

    Returns:
        Tuple of (fitted_model, forecast_mean, confidence_interval)
    """
    s = series.copy().astype(float)
    apply_log = bool(use_log)

    if apply_log:
        # disable log if any negative values present
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
        ci = fc.conf_int(alpha=CI_ALPHA)

        if apply_log:
            # safe back-transformation if log was used
            cap = 700.0
            max_out = float(max(series.max() * 10.0, 1e6))
            mean_bt = np.expm1(np.minimum(mean_fc.values, cap))
            lower_log = np.minimum(ci.iloc[:, 0].values, cap)
            upper_log = np.minimum(ci.iloc[:, 1].values, cap)
            lower_bt = safe_expm1_arr(lower_log, cap=cap, max_out=max_out)
            upper_bt = safe_expm1_arr(upper_log, cap=cap, max_out=max_out)

            if mean_fc.index is None or len(mean_fc.index) == 0:
                idx = pd.date_range(start=series.index[-1] + pd.offsets.MonthEnd(1),
                                   periods=len(mean_bt), freq="ME")
            else:
                idx = mean_fc.index

            mean_ser = pd.Series(mean_bt, index=idx)
            ci_df = pd.DataFrame({"lower": lower_bt, "upper": upper_bt}, index=idx)
            ci_df["lower"] = ci_df["lower"].clip(lower=0.0)
            return fit, mean_ser, ci_df
        else:
            if mean_fc.index is None or len(mean_fc.index) == 0:
                idx = pd.date_range(start=series.index[-1] + pd.offsets.MonthEnd(1),
                                   periods=len(mean_fc), freq="ME")
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


def fit_and_forecast_sarimax(
    series: pd.Series,
    order: Tuple[int, int, int] = ARIMA_ORDER,
    seasonal_order: Tuple[int, int, int, int] = SEASONAL_ORDER,
    steps: int = FORECAST_STEPS,
    use_log: bool = False,
    exog: Optional[pd.DataFrame] = None,
    exog_forecast: Optional[pd.DataFrame] = None
) -> Tuple[Optional[object], Optional[pd.Series], Optional[pd.DataFrame]]:
    """
    Fit SARIMAX model with optional exogenous variables.

    Args:
        series: Input time series
        order: ARIMA order (p, d, q)
        seasonal_order: Seasonal order (P, D, Q, s)
        steps: Number of forecast steps
        use_log: Whether to apply log transformation
        exog: Exogenous variables for training
        exog_forecast: Exogenous variables for forecasting

    Returns:
        Tuple of (fitted_model, forecast_mean, confidence_interval)
    """
    s = series.copy().astype(float)
    transform = False

    if use_log:
        if (s < 0).any():
            use_log = False
        else:
            s = np.log1p(s)
            transform = True

    try:
        # align exog to series index if provided
        exog_train = None
        if exog is not None:
            exog_train = exog.reindex(s.index)
            # coerce exog to numeric, drop non-numeric columns
            exog_train = exog_train.apply(pd.to_numeric, errors='coerce').ffill().fillna(0.0).values

        model = SARIMAX(s, order=order, seasonal_order=seasonal_order,
                        exog=exog_train, enforce_stationarity=False,
                        enforce_invertibility=False)
        fit = model.fit(disp=False)

        # exog_forecast: DataFrame indexed by future months
        if exog_forecast is not None:
            exog_fc = exog_forecast.reindex(
                pd.date_range(start=s.index[-1] + pd.offsets.MonthEnd(1),
                             periods=steps, freq="ME"))
            exog_fc = exog_fc.apply(pd.to_numeric, errors='coerce').ffill().fillna(0.0).values
            fc = fit.get_forecast(steps=steps, exog=exog_fc)
        else:
            fc = fit.get_forecast(steps=steps)

        mean = fc.predicted_mean
        ci = fc.conf_int(alpha=CI_ALPHA)

        if transform:
            cap = 700.0
            max_out = float(max(series.max() * 10.0, 1e6))
            mean_bt = np.expm1(np.minimum(mean.values, cap))
            lower_log = np.minimum(ci.iloc[:, 0].values, cap)
            upper_log = np.minimum(ci.iloc[:, 1].values, cap)
            lower_bt = safe_expm1_arr(lower_log, cap=cap, max_out=max_out)
            upper_bt = safe_expm1_arr(upper_log, cap=cap, max_out=max_out)
            idx = pd.date_range(start=series.index[-1] + pd.offsets.MonthEnd(1),
                               periods=len(mean_bt), freq="ME")
            mean = pd.Series(mean_bt, index=idx)
            ci = pd.DataFrame({"lower": lower_bt, "upper": upper_bt}, index=idx)
            ci["lower"] = ci["lower"].clip(lower=0.0)
            return fit, mean, ci
        else:
            idx = pd.date_range(start=series.index[-1] + pd.offsets.MonthEnd(1),
                               periods=len(mean), freq="ME")
            mean.index = idx
            ci.index = idx
            try:
                ci.columns = ["lower", "upper"]
                ci["lower"] = ci["lower"].clip(lower=0.0)
            except Exception:
                pass
            return fit, mean, ci

    except Exception as e:
        print(f"⚠️ SARIMAX fit error (exog aware): {e}")
        return None, None, None

