#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoRegressive (AR) model fitting and forecasting.
"""

import pandas as pd
from typing import Optional, Tuple

from statsmodels.tsa.ar_model import AutoReg

from src.Generation.config import FORECAST_STEPS


def fit_and_forecast_autoreg(
    series: pd.Series,
    lags: int = 5,
    steps: int = FORECAST_STEPS
) -> Tuple[Optional[object], Optional[pd.Series], Optional[object]]:
    """
    Fit AutoRegressive model with adaptive lag order.

    Tries decreasing lag orders until a fit succeeds, to handle limited data.

    Args:
        series: Input time series
        lags: Desired lag order
        steps: Number of forecast steps

    Returns:
        Tuple of (fitted_model, forecast, confidence_interval)
    """
    try:
        n = len(series)
        if n < 3:
            print(f"⚠️ AutoReg skipped: series too short (n={n}).")
            return None, None, None

        # Try decreasing lag orders until a fit succeeds or we reach 0
        max_lag = min(lags, max(0, n - 1))
        last_exc = None

        for used_lags in range(max_lag, -1, -1):
            try:
                # AutoReg may still fail if effective sample after creating lags is too small
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
                # continue trying with fewer lags
                continue

        # if we reach here, all attempts failed
        print(f"⚠️ AutoReg fit error (all lag orders failed): {last_exc}")
        return None, None, None

    except Exception as e:
        print(f"⚠️ AutoReg fit error: {e}")
        return None, None, None

