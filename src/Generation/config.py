#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration constants for the forecasting pipeline.
"""

from pathlib import Path
from typing import Tuple

# --- Time series configuration ---
TARGET: str = "amount"
FORECAST_STEPS: int = 10
MIN_POINTS: int = 3  # minimum points for model fitting (conservative)

# --- ARIMA/SARIMAX configuration ---
ARIMA_ORDER: Tuple[int, int, int] = (1, 1, 1)
SEASONAL_ORDER: Tuple[int, int, int, int] = (1, 1, 1, 12)
SEASONAL_MIN_POINTS: int = 12  # require at least 24 months for seasonal terms

# --- Feature engineering configuration ---
LAGS_FOR_FEATURES: int = 3
DEFAULT_LAG_ORDER: int = 8

# --- Outlier handling ---
WINSORIZE_LOWER_Q: float = 0.01
WINSORIZE_UPPER_Q: float = 0.99

# --- Confidence interval ---
CI_ALPHA: float = 0.2  # 80% confidence interval
Z_SCORE_FOR_CI: float = 1.2816  # z-score for 80% CI

# --- Default user ID and output path ---
UID_BASE: str = "3Dye4gBbAdPQSto3WbqgkBu6lrj2"
OUT_PATH: Path = Path("forecast_output.csv")

# --- Model selection thresholds ---
MAX_NORMALIZED_MSE: float = 1e3  # threshold for very unstable models
FORECAST_SCALE_FACTOR: float = 10.0  # max allowed forecast / max historical value
MAX_OUTPUT_CAP: float = 1e7  # absolute max forecast value
BASELINE_REL_IMPROVEMENT: float = 0.05  # require 5% improvement over seasonal naive

# --- Ridge regression configuration ---
RIDGE_ALPHA: float = 0.8

# --- Series flatness detection ---
FLATNESS_TOLERANCE: float = 0.02

# --- Walk-forward validation ---
MAX_TEST_SIZE: int = 5
BACKTEST_MIN: int = 3
BACKTEST_MAX: int = 6
