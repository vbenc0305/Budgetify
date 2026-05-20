#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Walk-forward cross-validation and model evaluation.
"""

import pandas as pd
import warnings
from typing import List, Tuple

from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import SimpleExpSmoothing, Holt
from sklearn.metrics import mean_squared_error, r2_score

from src.Generation.config import ARIMA_ORDER, MAX_TEST_SIZE
from src.Generation.models import (
    fit_and_forecast_autoreg,
    fit_and_forecast_behavioral_boosted,
    fit_and_forecast_ets,
)
from src.Generation.utils import ensure_monthly_freq


def walk_forward_1step(
    series: pd.Series,
    model_order: Tuple[int, int, int] = ARIMA_ORDER,
    n_test: int = MAX_TEST_SIZE
) -> Tuple[List[float], List[float], float, float]:
    """
    Walk-forward one-step-ahead cross-validation for ARIMA.

    Args:
        series: Input time series
        model_order: ARIMA order (p, d, q)
        n_test: Number of test steps

    Returns:
        Tuple of (predictions, test_values, MSE, R²)
    """
    if n_test >= len(series):
        raise ValueError("n_test túl nagy a sorozathoz.")

    history = ensure_monthly_freq(series.iloc[:-n_test].copy())

    test = series.iloc[-n_test:].tolist()
    preds = []

    for t in range(len(test)):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model = ARIMA(history, order=model_order).fit()
                yhat = float(model.forecast(steps=1).iloc[0])
        except Exception:
            yhat = float(history.iloc[-1])
        preds.append(yhat)
        next_idx = history.index[-1] + pd.offsets.MonthEnd(1)
        history = pd.concat([history, pd.Series([test[t]], index=[next_idx])])
        history = ensure_monthly_freq(history)

    mse = mean_squared_error(test, preds)
    r2 = r2_score(test, preds) if len(test) > 1 else float("nan")

    return preds, test, mse, r2


def walk_forward_ses(
    series: pd.Series,
    n_test: int = MAX_TEST_SIZE
) -> Tuple[float, List[float]]:
    """
    Walk-forward validation for Simple Exponential Smoothing.

    Args:
        series: Input time series
        n_test: Number of test steps

    Returns:
        Tuple of (MSE, predictions)
    """
    history = ensure_monthly_freq(series.iloc[:-n_test].copy())
    ses_preds = []
    test = series.iloc[-n_test:].tolist()

    for t in range(len(test)):
        try:
            history_clip = history.clip(upper=history.mean() + 2 * history.std())
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                s = SimpleExpSmoothing(history_clip).fit(smoothing_level=0.2, optimized=False)
                yhat = float(s.forecast(1).iloc[0])
        except Exception:
            yhat = float(history.iloc[-1])
        ses_preds.append(yhat)
        next_idx = history.index[-1] + pd.offsets.MonthEnd(1)
        history = pd.concat([history, pd.Series([test[t]], index=[next_idx])])
        history = ensure_monthly_freq(history)

    mse = mean_squared_error(test, ses_preds)
    return mse, ses_preds


def walk_forward_holt(
    series: pd.Series,
    n_test: int = MAX_TEST_SIZE
) -> Tuple[float, List[float]]:
    """
    Walk-forward validation for Holt exponential smoothing.

    Args:
        series: Input time series
        n_test: Number of test steps

    Returns:
        Tuple of (MSE, predictions)
    """
    history = ensure_monthly_freq(series.iloc[:-n_test].copy())
    holt_preds = []
    test = series.iloc[-n_test:].tolist()

    for t in range(len(test)):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                hmod = Holt(history, exponential=False, damped_trend=True).fit(optimized=True)
                yhat = float(hmod.forecast(1).iloc[0])
        except Exception:
            yhat = float(history.iloc[-1])
        holt_preds.append(yhat)
        next_idx = history.index[-1] + pd.offsets.MonthEnd(1)
        history = pd.concat([history, pd.Series([test[t]], index=[next_idx])])
        history = ensure_monthly_freq(history)

    mse = mean_squared_error(test, holt_preds)
    return mse, holt_preds


def walk_forward_ets(
    series: pd.Series,
    n_test: int = MAX_TEST_SIZE,
) -> Tuple[float, List[float]]:
    """
    Walk-forward validation for ETS (ExponentialSmoothing).
    """
    try:
        if n_test >= len(series):
            raise ValueError("n_test tul nagy a sorozathoz.")

        history = ensure_monthly_freq(series.iloc[:-n_test].copy())
        if history is None:
            return float("inf"), []
        test = series.iloc[-n_test:].tolist()
        preds: List[float] = []

        for t in range(len(test)):
            try:
                pred_series, _ = fit_and_forecast_ets(history, steps=1)
                if pred_series is None or len(pred_series) == 0:
                    raise ValueError("ETS forecast unavailable")
                yhat = float(pred_series.iloc[0])
            except Exception:
                yhat = float(history.iloc[-1])

            preds.append(yhat)
            next_idx = history.index[-1] + pd.offsets.MonthEnd(1)
            history = pd.concat([history, pd.Series([test[t]], index=[next_idx])])
            history = ensure_monthly_freq(history)

        mse = mean_squared_error(test, preds)
        return mse, preds
    except Exception:
        return float("inf"), []


def walk_forward_autoreg(
    series: pd.Series,
    n_test: int = MAX_TEST_SIZE,
    lags: int = 5
) -> Tuple[float, List[float]]:
    """
    Walk-forward validation for AutoReg model.

    Args:
        series: Input time series
        n_test: Number of test steps
        lags: Lag order for AutoReg

    Returns:
        Tuple of (MSE, predictions)
    """
    try:
        if n_test >= len(series):
            raise ValueError("n_test túl nagy a sorozathoz.")

        history = ensure_monthly_freq(series.iloc[:-n_test].copy())
        test = series.iloc[-n_test:].tolist()
        preds = []

        for t in range(len(test)):
            try:
                _, pred_series, _ = fit_and_forecast_autoreg(history, lags=lags, steps=1)
                if pred_series is None or len(pred_series) == 0:
                    raise ValueError("AutoReg forecast unavailable")
                yhat = float(pred_series.iloc[0])
            except Exception:
                yhat = float(history.iloc[-1])

            preds.append(yhat)
            next_idx = history.index[-1] + pd.offsets.MonthEnd(1)
            history = pd.concat([history, pd.Series([test[t]], index=[next_idx])])
            history = ensure_monthly_freq(history)

        mse = mean_squared_error(test, preds)
        return mse, preds
    except Exception:
        return float("inf"), []


def walk_forward_behavioral(
    series: pd.Series,
    n_test: int = MAX_TEST_SIZE,
    lags: int = 4,
    exog: pd.DataFrame | None = None,
    exog_forecast: pd.DataFrame | None = None,
) -> Tuple[float, List[float]]:
    """
    Walk-forward validation for the behavior-aware boosting model.
    """
    try:
        if n_test >= len(series):
            raise ValueError("n_test túl nagy a sorozathoz.")

        history = ensure_monthly_freq(series.iloc[:-n_test].copy())
        test = series.iloc[-n_test:].tolist()
        preds: List[float] = []

        for t in range(len(test)):
            try:
                exog_hist = None
                exog_fc = None
                if exog is not None and isinstance(exog, pd.DataFrame) and not exog.empty:
                    exog_hist = exog.reindex(history.index).ffill().fillna(0.0)
                    if exog_forecast is not None and isinstance(exog_forecast, pd.DataFrame) and not exog_forecast.empty:
                        future_idx = pd.date_range(
                            start=history.index[-1] + pd.offsets.MonthEnd(1),
                            periods=1,
                            freq="ME",
                        )
                        exog_fc = exog_forecast.reindex(future_idx).ffill().fillna(0.0)

                _, pred_series, _ = fit_and_forecast_behavioral_boosted(
                    history,
                    lags=lags,
                    steps=1,
                    exog=exog_hist,
                    exog_forecast=exog_fc,
                )
                if pred_series is None or len(pred_series) == 0:
                    raise ValueError("Behavioral forecast unavailable")
                yhat = float(pred_series.iloc[0])
            except Exception:
                yhat = float(history.iloc[-1])

            preds.append(yhat)
            next_idx = history.index[-1] + pd.offsets.MonthEnd(1)
            history = pd.concat([history, pd.Series([test[t]], index=[next_idx])])
            history = ensure_monthly_freq(history)

        mse = mean_squared_error(test, preds)
        return mse, preds
    except Exception:
        return float("inf"), []

