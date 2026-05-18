#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoRegressive (AR) model fitting and forecasting.
"""

import numpy as np
import pandas as pd
from typing import Optional, Tuple, cast

from statsmodels.tsa.ar_model import AutoReg

from src.Generation.config import (
    FORECAST_STEPS, SHORT_SERIES_COMPLEX_MODEL_MIN_POINTS,
    SHORT_SERIES_MAX_AUTOREG_LAGS,
)
from src.Generation.utils import ensure_monthly_freq


def fit_and_forecast_autoreg(
    series: pd.Series,
    lags: int = 5,
    steps: int = FORECAST_STEPS,
    exog: Optional[pd.DataFrame] = None,
    exog_forecast: Optional[pd.DataFrame] = None,
) -> Tuple[Optional[object], Optional[pd.Series], Optional[object]]:
    """
    Fit AutoRegressive model with adaptive lag order and optional exogenous variables.

    Tries decreasing lag orders until a fit succeeds, to handle limited data.

    Args:
        series: Input time series
        lags: Desired lag order
        steps: Number of forecast steps
        exog: Optional exogenous variables aligned to series index
        exog_forecast: Optional exogenous variables for the forecast horizon

    Returns:
        Tuple of (fitted_model, forecast, confidence_interval)
    """
    try:
        series_norm = ensure_monthly_freq(series)
        if series_norm is None:
            return None, None, None
        series = cast(pd.Series, series_norm)
        n = len(series)
        if n < 3:
            print(f"⚠️ AutoReg skipped: series too short (n={n}).")
            return None, None, None

        # Align and clean exog to match series index
        exog_train = None
        if exog is not None and isinstance(exog, pd.DataFrame) and not exog.empty:
            exog_train = exog.reindex(series.index)
            exog_train = exog_train.apply(pd.to_numeric, errors='coerce').ffill().fillna(0.0)

        # Build exog for forecast horizon (steps rows)
        exog_oos = None
        if exog_train is not None:
            if exog_forecast is not None and isinstance(exog_forecast, pd.DataFrame) and not exog_forecast.empty:
                exog_oos = exog_forecast.apply(pd.to_numeric, errors='coerce').ffill().fillna(0.0)
                exog_oos = exog_oos.reindex(
                    pd.date_range(start=series.index[-1] + pd.offsets.MonthEnd(1),
                                  periods=steps, freq="ME"),
                    method='nearest'
                ).fillna(0.0)
            else:
                # repeat last known exog row for all forecast steps
                last_row = exog_train.iloc[-1].values.reshape(1, -1)
                exog_oos = pd.DataFrame(
                    np.tile(last_row, (steps, 1)),
                    columns=exog_train.columns,
                    index=pd.date_range(start=series.index[-1] + pd.offsets.MonthEnd(1),
                                        periods=steps, freq="ME")
                )
            exog_oos_values = exog_oos.values
        else:
            exog_oos_values = None

        # Try decreasing lag orders until a fit succeeds or we reach 0
        max_lag_by_sample = max(1, (n - 1) // 3)
        max_lag = min(lags, max_lag_by_sample, max(0, n - 1))
        if n < SHORT_SERIES_COMPLEX_MODEL_MIN_POINTS:
            max_lag = min(max_lag, SHORT_SERIES_MAX_AUTOREG_LAGS)
        last_exc = None

        for used_lags in range(max_lag, -1, -1):
            try:
                # AutoReg may still fail if effective sample after creating lags is too small
                exog_vals = exog_train.values if exog_train is not None else None
                model = AutoReg(series, lags=used_lags, old_names=False, exog=exog_vals).fit()
                start = len(series)
                end = start + steps - 1
                preds = model.predict(start=start, end=end, exog_oos=exog_oos_values, dynamic=False)

                idx = pd.date_range(start=series.index[-1] + pd.offsets.MonthEnd(1),
                                   periods=steps, freq="ME")
                preds = pd.Series(preds.values, index=idx, name="autoreg_forecast")
                preds = preds.clip(lower=0.0)

                return model, preds, None

            except Exception as e:
                last_exc = e
                # continue trying with fewer lags
                continue

        # if we reach here, all attempts failed — retry without exog as fallback
        if exog_train is not None:
            for used_lags in range(max_lag, -1, -1):
                try:
                    model = AutoReg(series, lags=used_lags, old_names=False).fit()
                    start = len(series)
                    end = start + steps - 1
                    preds = model.predict(start=start, end=end, dynamic=False)
                    idx = pd.date_range(start=series.index[-1] + pd.offsets.MonthEnd(1),
                                       periods=steps, freq="ME")
                    preds = pd.Series(preds.values, index=idx, name="autoreg_forecast")
                    preds = preds.clip(lower=0.0)
                    return model, preds, None
                except Exception as e:
                    last_exc = e
                    continue

        print(f"⚠️ AutoReg fit error (all lag orders failed): {last_exc}")
        return None, None, None

    except Exception as e:
        print(f"⚠️ AutoReg fit error: {e}")
        return None, None, None

