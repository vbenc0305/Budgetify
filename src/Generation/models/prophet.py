#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prophet model fitting and forecasting.
"""

from __future__ import annotations

import pandas as pd
import importlib
from typing import Optional, Tuple

from src.Generation.config import CI_ALPHA, FORECAST_STEPS
from src.Generation.utils import ensure_monthly_freq


def fit_and_forecast_prophet(
    series: pd.Series,
    steps: int = FORECAST_STEPS,
    exog: Optional[pd.DataFrame] = None,
    exog_forecast: Optional[pd.DataFrame] = None,
) -> Tuple[Optional[object], Optional[pd.Series], Optional[pd.DataFrame]]:
    """
    Fit a Prophet model and forecast monthly spending.

    Prophet is optional dependency; if not installed, this function returns None outputs.
    """
    try:
        prophet_module = importlib.import_module("prophet")
        Prophet = getattr(prophet_module, "Prophet")
    except Exception:
        return None, None, None

    try:
        series_norm = ensure_monthly_freq(series.astype(float))
        if series_norm is None or len(series_norm) < 2:
            return None, None, None

        train_df = pd.DataFrame({"ds": pd.to_datetime(series_norm.index), "y": series_norm.values.astype(float)})

        exog_cols: list[str] = []
        exog_hist = pd.DataFrame(index=series_norm.index)
        if exog is not None and isinstance(exog, pd.DataFrame) and not exog.empty:
            exog_hist = exog.reindex(series_norm.index)
            exog_hist = exog_hist.apply(pd.to_numeric, errors="coerce").ffill().fillna(0.0)
            exog_cols = list(exog_hist.columns)
            for col in exog_cols:
                train_df[col] = exog_hist[col].values

        model = Prophet(
            yearly_seasonality=(len(series_norm) >= 18),
            weekly_seasonality=False,
            daily_seasonality=False,
            interval_width=float(1.0 - CI_ALPHA),
        )

        for col in exog_cols:
            model.add_regressor(col)

        model.fit(train_df)

        future = model.make_future_dataframe(periods=steps, freq="ME", include_history=False)
        if exog_cols:
            if exog_forecast is not None and isinstance(exog_forecast, pd.DataFrame) and not exog_forecast.empty:
                exog_fc = exog_forecast.reindex(pd.DatetimeIndex(future["ds"])).ffill().fillna(0.0)
                exog_fc = exog_fc.reindex(columns=exog_cols, fill_value=0.0)
            else:
                last_row = exog_hist.iloc[-1]
                exog_fc = pd.DataFrame([last_row.values] * len(future), columns=exog_cols, index=pd.DatetimeIndex(future["ds"]))
            for col in exog_cols:
                future[col] = exog_fc[col].values

        pred = model.predict(future)

        idx = pd.DatetimeIndex(pred["ds"])
        mean_fc = pd.Series(pred["yhat"].values.astype(float), index=idx, name="prophet_forecast").clip(lower=0.0)
        ci = pd.DataFrame(
            {
                "lower": pred["yhat_lower"].values.astype(float),
                "upper": pred["yhat_upper"].values.astype(float),
            },
            index=idx,
        )
        ci["lower"] = ci["lower"].clip(lower=0.0)
        ci["upper"] = ci[["upper", "lower"]].max(axis=1)

        return model, mean_fc, ci

    except Exception as e:
        print(f"⚠️ Prophet fit error: {e}")
        return None, None, None

