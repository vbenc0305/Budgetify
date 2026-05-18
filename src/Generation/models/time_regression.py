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
    alpha: float = RIDGE_ALPHA,
    exog: Optional[pd.DataFrame] = None,
    exog_forecast: Optional[pd.DataFrame] = None,
) -> Tuple[Optional[object], Optional[pd.Series], Optional[object]]:
    """
    Fit Ridge regression with lagged features, seasonal features, and optional exogenous variables.

    Features include:
    - Lagged values of the target
    - Time trend
    - Monthly seasonality (sin/cos features)
    - Exogenous variables (if provided)

    Args:
        series: Input time series
        steps: Number of forecast steps
        lags_for_features: Number of lag features to use
        alpha: Ridge regularization parameter
        exog: Optional exogenous variables aligned to series index
        exog_forecast: Optional exogenous variables for the forecast horizon

    Returns:
        Tuple of (fitted_model, forecast, confidence_interval)
    """
    try:
        n = len(series)
        if n < 3:
            return None, None, None

        df = pd.DataFrame({"y": series.values}, index=series.index)
        used_lags = min(lags_for_features, max(1, n - 2))

        # Create lag features
        for i in range(1, used_lags + 1):
            df[f"lag{i}"] = df["y"].shift(i)

        # Create time and seasonal features
        df["t"] = np.arange(n)
        months = series.index.month.values
        df["month_sin"] = np.sin(2 * np.pi * (months - 1) / 12.0)
        df["month_cos"] = np.cos(2 * np.pi * (months - 1) / 12.0)

        # Align and join exog features if provided
        exog_cols: list = []
        exog_last_row: list = []
        exog_forecast_arr: Optional[np.ndarray] = None

        if exog is not None and isinstance(exog, pd.DataFrame) and not exog.empty:
            exog_clean = exog.reindex(series.index)
            exog_clean = exog_clean.apply(pd.to_numeric, errors='coerce').ffill().fillna(0.0)
            exog_cols = list(exog_clean.columns)
            for col in exog_cols:
                df[col] = exog_clean[col].values
            exog_last_row = exog_clean.iloc[-1].tolist()

            # Prepare exog values for forecast steps
            if exog_forecast is not None and isinstance(exog_forecast, pd.DataFrame) and not exog_forecast.empty:
                fc_idx = pd.date_range(
                    start=series.index[-1] + pd.offsets.MonthEnd(1),
                    periods=steps, freq="ME"
                )
                exog_fc_clean = exog_forecast.reindex(fc_idx, method='nearest').fillna(0.0)
                exog_fc_clean = exog_fc_clean.apply(pd.to_numeric, errors='coerce').ffill().fillna(0.0)
                exog_forecast_arr = exog_fc_clean[exog_cols].values if all(c in exog_fc_clean.columns for c in exog_cols) else None
            # If no exog_forecast, we'll reuse last known row for every step (set below)

        df = df.dropna()
        lag_features = [f"lag{i}" for i in range(1, used_lags + 1)]
        feat_cols = lag_features + ["t", "month_sin", "month_cos"] + exog_cols

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

            base_feat = last_vals[-used_lags:] + [last_t, month_sin, month_cos]

            if exog_cols:
                if exog_forecast_arr is not None and step < len(exog_forecast_arr):
                    exog_row = exog_forecast_arr[step].tolist()
                else:
                    exog_row = exog_last_row  # last known (naive forward-fill)
                base_feat = base_feat + exog_row

            feat = np.array(base_feat).reshape(1, -1)
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

