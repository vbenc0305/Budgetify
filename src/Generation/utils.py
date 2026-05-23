#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility functions for data processing and inspection.
"""

import logging
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.Generation.config import WINSORIZE_LOWER_Q, WINSORIZE_UPPER_Q


logger = logging.getLogger(__name__)


def is_flat(series: pd.Series, rel_tol: float = 0.05) -> bool:
    if series is None or len(series) < 2:
        return True

    mean = series.mean()
    if mean == 0:
        return series.std() < 1e-6

    cv = series.std() / abs(mean)
    return cv < rel_tol


def ensure_monthly_freq(series: Optional[pd.Series]) -> Optional[pd.Series]:
    """
    Restore a contiguous month-end frequency metadata when possible.

    This avoids repeated statsmodels frequency inference warnings without
    changing the actual values of the series.
    """
    if series is None:
        return None

    s = series.copy()
    if not isinstance(s.index, pd.DatetimeIndex):
        return s

    try:
        s = s.sort_index()
        idx = pd.DatetimeIndex(pd.to_datetime(s.index))
        if len(idx) >= 2:
            expected = pd.date_range(start=idx[0], periods=len(idx), freq="ME")
            if expected.equals(idx):
                s.index = pd.DatetimeIndex(idx, freq="ME")
                return s

        inferred = pd.infer_freq(idx)
        if inferred is not None:
            s.index = pd.DatetimeIndex(idx, freq=inferred)
    except Exception:
        pass

    return s

def prepare_monthly_series_from_df(
    df: pd.DataFrame,
    date_col: str = "date",
    amount_col: str = "amount"
) -> pd.Series:
    """
    Convert DataFrame to monthly aggregated Series.

    Args:
        df: Input DataFrame with date and amount columns
        date_col: Name of the date column
        amount_col: Name of the amount column

    Returns:
        pd.Series: Monthly aggregated time series

    Raises:
        ValueError: If required columns are missing
    """
    df = df.copy()
    if date_col not in df.columns:
        raise ValueError(f"A '{date_col}' oszlop hiányzik a DataFrame-ből.")
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    if amount_col not in df.columns:
        raise ValueError(f"A '{amount_col}' oszlop hiányzik a DataFrame-ből.")
    df[amount_col] = pd.to_numeric(df[amount_col], errors="coerce").fillna(0.0).abs()
    df = df.dropna(subset=[date_col])
    if df.empty:
        return pd.Series(dtype=float)

    # Remove duplicates by date before aggregation
    before_utils_dupes = len(df)
    df = df.drop_duplicates(subset=[date_col], keep='first')
    if len(df) != before_utils_dupes:
        logger.info(
            "prepare_monthly_series_from_df: removed %s duplicate dates",
            before_utils_dupes - len(df),
        )

    df = df.set_index(date_col).sort_index()
    monthly = df[amount_col].resample("ME").sum().fillna(0)
    monthly = monthly.asfreq("ME", fill_value=0.0)
    monthly = ensure_monthly_freq(monthly)
    return monthly if monthly is not None else pd.Series(dtype=float)


def inspect_series(
    monthly_series: pd.Series,
    plot: bool = False,
    verbose: bool = False
) -> None:
    """
    Inspect and optionally visualize a time series.

    Args:
        monthly_series: Time series to inspect
        plot: Whether to plot the series
        verbose: Whether to print statistics
    """
    if verbose:
        logger.info("\n--- SERIE INSPECT ---\n%s", monthly_series.to_string())
        logger.info("\nLeíró statisztika:\n%s", monthly_series.describe().to_string())
        logger.info("\nNullák száma: %s / %s", int((monthly_series == 0).sum()), len(monthly_series))
    if plot:
        try:
            _, ax = plt.subplots(figsize=(8, 4))
            ax.plot(monthly_series.index, monthly_series.values, marker="o")
            ax.set_title("Monthly series — inspect")
            ax.grid(True)
            plt.show()
        except Exception:
            pass


def winsorize_series(
    s: pd.Series,
    lower_q: float = WINSORIZE_LOWER_Q,
    upper_q: float = WINSORIZE_UPPER_Q
) -> pd.Series:
    """
    Apply winsorization to limit outliers.

    Args:
        s: Input series
        lower_q: Lower quantile threshold
        upper_q: Upper quantile threshold

    Returns:
        pd.Series: Winsorized series
    """
    lo = s.quantile(lower_q)
    hi = s.quantile(upper_q)
    return s.clip(lower=lo, upper=hi)


def safe_expm1_arr(
    arr: np.ndarray,
    cap: float = 700.0,
    max_out: Optional[float] = None
) -> np.ndarray:
    """
    Safe exponential back-transformation with overflow protection.

    Args:
        arr: Input array (typically log-transformed values)
        cap: Upper cap to prevent overflow
        max_out: Optional maximum output value

    Returns:
        np.ndarray: Back-transformed array
    """
    a = np.array(arr, dtype=float)
    a = np.where(a > cap, cap, a)
    with np.errstate(over='ignore', invalid='ignore'):
        out = np.expm1(a)
    out = np.where(np.isfinite(out), out, np.nan)
    out = np.where(out < 0, 0.0, out)
    if max_out is not None:
        out = np.minimum(out, max_out)
    return out

