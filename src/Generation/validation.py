#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Walk-forward cross-validation and model evaluation.
"""

import pandas as pd
import numpy as np
from typing import List, Tuple

from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import SimpleExpSmoothing, Holt
from sklearn.metrics import mean_squared_error, r2_score

from src.Generation.config import ARIMA_ORDER, MAX_TEST_SIZE
from src.Generation.models import fit_and_forecast_autoreg


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

    history = series.iloc[:-n_test].copy()

    # ensure frequency is present to avoid statsmodels inferring warnings
    try:
        history = history.asfreq('ME')
    except Exception:
        pass

    test = series.iloc[-n_test:].tolist()
    preds = []

    for t in range(len(test)):
        try:
            model = ARIMA(history, order=model_order).fit()
            yhat = float(model.forecast(steps=1).iloc[0])
        except Exception:
            yhat = float(history.iloc[-1])
        preds.append(yhat)
        next_idx = history.index[-1] + pd.offsets.MonthEnd(1)
        history = pd.concat([history, pd.Series([test[t]], index=[next_idx])])

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
    history = series.iloc[:-n_test].tolist()
    ses_preds = []
    test = series.iloc[-n_test:].tolist()

    for t in range(len(test)):
        try:
            series = series.clip(upper=series.mean() + 2 * series.std())
            s = SimpleExpSmoothing(pd.Series(history)).fit(    smoothing_level=0.2,
    optimized=False)
            yhat = float(s.forecast(1).iloc[0])
        except Exception:
            yhat = float(history[-1])
        ses_preds.append(yhat)
        history.append(test[t])

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
    history = series.iloc[:-n_test].copy()
    holt_preds = []
    test = series.iloc[-n_test:].tolist()

    for t in range(len(test)):
        try:
            hmod = Holt(history).fit(optimized=True)
            yhat = float(hmod.forecast(1).iloc[0])
        except Exception:
            yhat = float(history.iloc[-1])
        holt_preds.append(yhat)
        next_idx = history.index[-1] + pd.offsets.MonthEnd(1)
        history = pd.concat([history, pd.Series([test[t]], index=[next_idx])])

    mse = mean_squared_error(test, holt_preds)
    return mse, holt_preds


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
        _, ar_preds_wf, _ = fit_and_forecast_autoreg(series.iloc[:-n_test],
                                                     lags=lags, steps=n_test)
        test = series.iloc[-n_test:].tolist()
        mse = mean_squared_error(test, ar_preds_wf.values)
        return mse, ar_preds_wf.tolist()
    except Exception:
        return float("inf"), []

