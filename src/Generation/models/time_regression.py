#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Time-series regression model using Ridge regression with features.
"""

import numpy as np
import pandas as pd
from typing import Optional, Tuple

from sklearn.linear_model import Ridge

from src.Generation.config import FORECAST_STEPS, LAGS_FOR_FEATURES, RIDGE_ALPHA


def fit_and_forecast_time_regression_boosted(
    series: pd.Series,
    steps: int = FORECAST_STEPS,
    lags_for_features: int = LAGS_FOR_FEATURES,
    alpha: float = RIDGE_ALPHA
) -> Tuple[Optional[object], Optional[pd.Series], Optional[object]]:
    """
    Fit Ridge regression with lagged features and seasonal features.

    Features include:
    - Lagged values of the target
    - Time trend
    - Monthly seasonality (sin/cos features)

    Args:
        series: Input time series
        steps: Number of forecast steps
        lags_for_features: Number of lag features to use
        alpha: Ridge regularization parameter

    Returns:
        Tuple of (fitted_model, forecast, confidence_interval)
    """
    try:
        n = len(series)
        if n < 3:
            return None, None, None

        df = pd.DataFrame({"y": series.values})
        used_lags = min(lags_for_features, max(1, n - 2))

        # Create lag features
        for i in range(1, used_lags + 1):
            df[f"lag{i}"] = df["y"].shift(i)

        # Create time and seasonal features
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

        # Generate forecasts
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

        idx = pd.date_range(start=series.index[-1] + pd.offsets.MonthEnd(1),
                           periods=steps, freq="ME")
        preds = pd.Series(preds, index=idx, name="time_reg_ridge_forecast")
        preds = preds.clip(lower=0.0)

        return reg, preds, None

    except Exception as e:
        print("⚠️ Time-reg (Ridge) fit error:", e)
        return None, None, None

