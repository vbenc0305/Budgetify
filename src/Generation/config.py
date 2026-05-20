#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration constants for the forecasting pipeline.
"""

from pathlib import Path
from typing import Tuple

# --- Time series configuration ---
TARGET: str = "amount"
FORECAST_STEPS: int = 12
MIN_POINTS: int = 3  # minimum points for model fitting (conservative)

# --- ARIMA/SARIMAX configuration ---
ARIMA_ORDER: Tuple[int, int, int] = (1, 1, 1)
ARIMA_SHORT_ORDER: Tuple[int, int, int] = (0, 1, 1)
SEASONAL_ORDER: Tuple[int, int, int, int] = (1, 1, 1, 12)
SEASONAL_MIN_POINTS: int = 10  # require at least 24 months for seasonal terms
SHORT_SERIES_COMPLEX_MODEL_MIN_POINTS: int = 10
SARIMAX_EXOG_MIN_POINTS: int = 10
ETS_MIN_POINTS: int = 10

# --- Feature engineering configuration ---
LAGS_FOR_FEATURES: int = 3
DEFAULT_LAG_ORDER: int = 8
SHORT_SERIES_MAX_AUTOREG_LAGS: int = 3

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
SELECTION_CLOSE_MARGIN: float = 0.03  # treat close model scores as effectively tied
SELECTION_SMOOTH_VOL_FLOOR: float = 0.78  # below this vol ratio the candidate is considered too smooth
SELECTION_SHAPE_IMPROVEMENT: float = 0.05  # minimum shape-score gain to override a tied winner

# --- ETS seasonal-signature adjustment ---
ETS_SIGNATURE_MIN_POINTS: int = 18
ETS_SIGNATURE_MIN_LAG12_AUTOCORR: float = 0.18
ETS_SIGNATURE_MAX_REL_ADJ: float = 0.18
ETS_SIGNATURE_DECAY: float = 0.97

# --- Ridge regression configuration ---
RIDGE_ALPHA: float = 0.8

# --- Behavior-aware short-series forecasting ---
BEHAVIORAL_MIN_LAGS: int = 2
BEHAVIORAL_MAX_LAGS: int = 5
BEHAVIORAL_RECENCY_WEIGHT_MAX: float = 3.5
BEHAVIORAL_SPIKE_WEIGHT: float = 2.2
BEHAVIORAL_TURN_WEIGHT: float = 1.4
BEHAVIORAL_SPIKE_DECAY: float = 0.82
BEHAVIORAL_MOMENTUM_DECAY: float = 0.90
BEHAVIORAL_ACCEL_DECAY: float = 0.78
BEHAVIORAL_DELTA_STD_CAP: float = 1.9
BEHAVIORAL_DELTA_REL_CAP: float = 0.18
BEHAVIORAL_VARIANCE_TOLERANCE: float = 0.18
BEHAVIORAL_REBOUND_GAIN: float = 0.58
BEHAVIORAL_PERSISTENCE_GAIN: float = 0.34
BEHAVIORAL_REBOUND_DECAY: float = 0.87
BEHAVIORAL_SIGNATURE_DECAY: float = 0.93
BEHAVIORAL_VARIANCE_FLOOR_RATIO: float = 0.32

# --- Series flatness detection ---
FLATNESS_TOLERANCE: float = 0.02

# --- Walk-forward validation ---
MAX_TEST_SIZE: int = 5
BACKTEST_MIN: int = 3
BACKTEST_MAX: int = 6
