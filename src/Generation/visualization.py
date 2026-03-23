#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Visualization utilities for time series and forecasts.
"""

import pandas as pd
import matplotlib.pyplot as plt
from typing import Optional, List
from pathlib import Path


def plot_results(
    series: pd.Series,
    forecast_mean: pd.Series,
    forecast_ci: Optional[pd.DataFrame] = None,
    baseline_preds: Optional[List[float]] = None,
    save_path: Optional[Path] = None,
    plot: bool = False
) -> None:
    """
    Plot historical series, forecast, and confidence interval.

    Args:
        series: Historical time series
        forecast_mean: Forecast mean values
        forecast_ci: Confidence interval DataFrame with "lower" and "upper" columns
        baseline_preds: Optional baseline predictions (e.g., seasonal naive)
        save_path: Optional path to save the figure
        plot: Whether to display the plot
    """
    if not plot:
        return

    plt.figure(figsize=(10, 6))
    plt.plot(series.index, series.values, label="Valós (monthly)", marker="o")

    last_date = series.index[-1]
    if hasattr(forecast_mean, "index") and len(forecast_mean.index) > 0:
        forecast_index = forecast_mean.index
    else:
        forecast_index = pd.date_range(start=last_date + pd.offsets.MonthEnd(1),
                                      periods=len(forecast_mean), freq="ME")

    plt.plot(forecast_index, forecast_mean, label="Forecast", linestyle="--", marker="o")

    try:
        if forecast_ci is not None:
            lower = forecast_ci.iloc[:, 0]
            upper = forecast_ci.iloc[:, 1]
            plt.fill_between(forecast_index, lower, upper, alpha=0.25, label="80% CI")
    except Exception:
        pass

    if baseline_preds is not None:
        try:
            plt.plot(forecast_index, baseline_preds, label="Baseline (seasonal-naive/SES)",
                    linestyle="-.")
        except Exception:
            pass

    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path)
        print(f"Plot elmentve: {save_path}")
    else:
        plt.show()


def seasonal_naive(series: pd.Series, steps: int = 10) -> pd.Series:
    """
    Generate seasonal naive forecasts (use last year's values).

    Falls back to last value if less than 12 months available.

    Args:
        series: Input time series
        steps: Number of forecast steps

    Returns:
        pd.Series: Seasonal naive forecasts
    """
    if len(series) >= 12:
        idx = pd.date_range(start=series.index[-1] + pd.offsets.MonthEnd(1),
                           periods=steps, freq="ME")
        vals = []
        for i in range(steps):
            target = series.index[-1] + pd.offsets.MonthEnd(1) + pd.offsets.MonthEnd(i)
            ref = target - pd.DateOffset(months=12)
            if ref in series.index:
                vals.append(series.loc[ref])
            else:
                vals.append(series.iloc[-1])
        return pd.Series(vals, index=idx)
    else:
        idx = pd.date_range(start=series.index[-1] + pd.offsets.MonthEnd(1),
                           periods=steps, freq="ME")
        return pd.Series([series.iloc[-1]] * steps, index=idx)

