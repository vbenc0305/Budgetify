#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main forecasting pipeline orchestration.
"""

import logging

import numpy as np
import pandas as pd
from typing import Any, Optional, cast

from src.Generation.config import (
    FORECAST_STEPS, MIN_POINTS, ARIMA_ORDER, ARIMA_SHORT_ORDER, SEASONAL_ORDER,
    MAX_NORMALIZED_MSE, FORECAST_SCALE_FACTOR, MAX_OUTPUT_CAP, BASELINE_REL_IMPROVEMENT,
    BACKTEST_MIN, BACKTEST_MAX, SEASONAL_MIN_POINTS,
    SHORT_SERIES_COMPLEX_MODEL_MIN_POINTS, SARIMAX_EXOG_MIN_POINTS,
    DEFAULT_LAG_ORDER, SHORT_SERIES_MAX_AUTOREG_LAGS, ETS_MIN_POINTS,
    BEHAVIORAL_MAX_LAGS, BEHAVIORAL_VARIANCE_TOLERANCE,
    SELECTION_CLOSE_MARGIN, SELECTION_SMOOTH_VOL_FLOOR, SELECTION_SHAPE_IMPROVEMENT,
    PREVIEW_MIN_HORIZON, PREVIEW_TOP_K, PREVIEW_OVERRIDE_MARGIN, PREVIEW_SCORE_WEIGHT,
)
from src.Generation.utils import winsorize_series, inspect_series, is_flat, ensure_monthly_freq
from src.Generation.validation import (
    walk_forward_1step, walk_forward_ses, walk_forward_holt, walk_forward_autoreg,
    walk_forward_behavioral, walk_forward_ets,
)
from src.Generation.models import (
    fit_and_forecast_arima, fit_and_forecast_sarimax, fit_and_forecast_ses,
    fit_and_forecast_holt, fit_and_forecast_ets, fit_and_forecast_autoreg, fit_and_forecast_behavioral_boosted,
    fit_and_forecast_time_regression_boosted,
)
from src.Generation.visualization import plot_results, seasonal_naive


logger = logging.getLogger(__name__)

# ── TEST OVERRIDE ──────────────────────────────────────────────────────────────
# Set to a model name (e.g. "ses", "holt", "arima", "autoreg", "behavioral") to force that
# model every run. Set to None to restore normal model-selection behaviour.
_FORCE_MODEL: str | None = None
# ──────────────────────────────────────────────────────────────────────────────


def run_short_series_pipeline(
    monthly_series: pd.Series,
    exog: Optional[pd.DataFrame] = None,
    exog_forecast: Optional[pd.DataFrame] = None,
    plot: bool = False,
    verbose: bool = False
) -> tuple:
    """
    Main forecasting pipeline with automatic model selection.

    Performs walk-forward validation across multiple models (ARIMA, SES, Holt,
    AutoReg, behavior-aware boosting),
    selects the best model, and applies fallback mechanisms if needed.

    Args:
        monthly_series: Input monthly time series
        exog: Optional exogenous variables
        exog_forecast: Optional future exogenous variables
        plot: Whether to plot results
        verbose: Whether to print detailed logs

    Returns:
        Tuple of (forecast_series, confidence_interval, metrics_dict)
    """
    if len(monthly_series) < MIN_POINTS:
        raise ValueError(f"Adatmennyiség túl kevés (min {MIN_POINTS} hónap ajánlott).")

    inspect_series(monthly_series, plot=plot, verbose=verbose)

    # Winsorize outliers
    monthly_series_proc = winsorize_series(monthly_series)
    monthly_series_proc = ensure_monthly_freq(monthly_series_proc)
    if monthly_series_proc is None:
        raise ValueError("A havi idősor frekvenciája nem állítható helyre.")
    monthly_series_proc = cast(pd.Series, monthly_series_proc)

    seasonal_order = SEASONAL_ORDER
    if len(monthly_series_proc) < SEASONAL_MIN_POINTS:
        seasonal_order = (0, 0, 0, 0)
        if verbose:
            logger.info(
                f"⚠️ Rövid idősor ({len(monthly_series_proc)} pont) — "
                "szezonalitás kikapcsolva."
            )

    # --- Walk-forward validation across models ---
    n = len(monthly_series_proc)
    short_series_guard = n < SHORT_SERIES_COMPLEX_MODEL_MIN_POINTS
    arima_order = ARIMA_SHORT_ORDER if short_series_guard else ARIMA_ORDER
    autoreg_lags = min(
        SHORT_SERIES_MAX_AUTOREG_LAGS if short_series_guard else DEFAULT_LAG_ORDER,
        max(1, (n - 1) // 3),
    )
    can_use_exog = bool(
        exog is not None and n >= SARIMAX_EXOG_MIN_POINTS
    )
    n_test = min(BACKTEST_MAX, max(BACKTEST_MIN, n // 3))
    n_test = min(n_test, n - 1)

    backtest_start = None
    backtest_end = None
    if n_test > 0:
        try:
            backtest_start = monthly_series_proc.index[-n_test]
            backtest_end = monthly_series_proc.index[-1]
        except Exception:
            backtest_start = None
            backtest_end = None

    def _calc_mae(y_true: np.ndarray, y_pred: np.ndarray) -> Optional[float]:
        if y_true.size == 0 or y_pred.size == 0:
            return None
        if y_true.size != y_pred.size:
            return None
        return float(np.mean(np.abs(y_true - y_pred)))

    def _calc_smape(y_true: np.ndarray, y_pred: np.ndarray, eps: float = 1e-6) -> Optional[float]:
        if y_true.size == 0 or y_pred.size == 0:
            return None
        if y_true.size != y_pred.size:
            return None
        denom = np.abs(y_true) + np.abs(y_pred) + eps
        return float(200.0 * np.mean(np.abs(y_true - y_pred) / denom))

    def _calc_recency_weighted_mse(y_true: np.ndarray, y_pred: np.ndarray) -> Optional[float]:
        if y_true.size == 0 or y_pred.size == 0 or y_true.size != y_pred.size:
            return None
        weights = np.linspace(1.0, 2.5, y_true.size)
        return float(np.average((y_true - y_pred) ** 2, weights=weights))

    def _calc_turning_point_score(y_true: np.ndarray, y_pred: np.ndarray) -> Optional[float]:
        if y_true.size < 2 or y_pred.size < 2 or y_true.size != y_pred.size:
            return None
        true_diff = np.sign(np.diff(y_true))
        pred_diff = np.sign(np.diff(y_pred))
        return float(np.mean(true_diff == pred_diff))

    def _calc_volatility_ratio(y_true: np.ndarray, y_pred: np.ndarray) -> Optional[float]:
        if y_true.size < 2 or y_pred.size < 2 or y_true.size != y_pred.size:
            return None
        true_std = float(np.std(np.diff(y_true)))
        pred_std = float(np.std(np.diff(y_pred)))
        if true_std <= 1e-9:
            return 1.0 if pred_std <= 1e-9 else None
        return float(pred_std / true_std)

    def _calc_spike_recall(y_true: np.ndarray, y_pred: np.ndarray) -> Optional[float]:
        if y_true.size < 2 or y_pred.size < 2 or y_true.size != y_pred.size:
            return None
        true_diff = np.diff(y_true)
        pred_diff = np.diff(y_pred)
        spike_threshold = max(float(np.std(true_diff)), float(np.mean(np.abs(true_diff))), 1.0)
        spike_mask = np.abs(true_diff) >= spike_threshold
        if not np.any(spike_mask):
            return 1.0
        matched = np.sign(true_diff[spike_mask]) == np.sign(pred_diff[spike_mask])
        return float(np.mean(matched))

    def _infer_exog_forecast_method(
        exog_df: Optional[pd.DataFrame],
        exog_fc: Optional[pd.DataFrame]
    ) -> str:
        if exog_fc is None:
            return "none"
        if exog_df is None or not isinstance(exog_df, pd.DataFrame) or exog_df.empty:
            return "provided"
        try:
            cols = [c for c in exog_fc.columns if c in exog_df.columns]
            if not cols:
                return "provided"
            last_row = exog_df.iloc[-1][cols]
            last_row = pd.to_numeric(last_row, errors="coerce").fillna(0.0).values
            fc_vals = exog_fc[cols].apply(pd.to_numeric, errors="coerce").fillna(0.0).values
            if fc_vals.size == 0:
                return "provided"
            repeated = np.allclose(fc_vals, last_row, rtol=0.0, atol=1e-9)
            return "last_known_ffill" if repeated else "provided"
        except Exception:
            return "provided"

    test_series = monthly_series_proc.iloc[-n_test:]
    test_arr = test_series.values if n_test > 0 else np.array([])

    # Seasonal-naive baseline WF
    baseline_mse = None
    baseline_mae = None
    baseline_smape = None
    baseline_wf_preds = None
    try:
        history = monthly_series_proc.iloc[:-n_test].copy()
        test = monthly_series_proc.iloc[-n_test:]
        preds = []
        for i in range(len(test)):
            cur_idx = test.index[i]
            ref_idx = cur_idx - pd.DateOffset(months=12)
            if len(history) >= 12 and ref_idx in history.index:
                pred = float(history.loc[ref_idx])
            else:
                pred = float(history.iloc[-1])
            preds.append(pred)
            history = pd.concat([history, pd.Series([test.iloc[i]], index=[cur_idx])])
        baseline_wf_preds = preds
        baseline_pred_arr = np.array(preds, dtype=float)
        baseline_mse = float(np.mean((test.values - baseline_pred_arr) ** 2))
        baseline_mae = _calc_mae(test.values, baseline_pred_arr)
        baseline_smape = _calc_smape(test.values, baseline_pred_arr)
        if verbose:
            logger.info("Walk-forward (1-step) BASELINE MSE: %.3f", baseline_mse)
    except Exception:
        baseline_mse = None
        baseline_mae = None
        baseline_smape = None
        baseline_wf_preds = None

    # ARIMA WF
    if short_series_guard:
        preds_arima, test_vals, mse_arima, r2_arima = [], [], float("inf"), float("nan")
        arima_pred_arr = np.array([])
        arima_test_arr = np.array([])
        mae_arima = None
        smape_arima = None
        if verbose:
            logger.info(
                f"Walk-forward (1-step) ARIMA skipped: rövid sorozat (n={n}) "
                "miatt túl kockázatos lenne a paraméterbecslés."
            )
    else:
        preds_arima, test_vals, mse_arima, r2_arima = walk_forward_1step(
            monthly_series_proc, model_order=arima_order, n_test=n_test,
            exog=exog, exog_forecast=exog_forecast)
        arima_pred_arr = np.array(preds_arima, dtype=float) if preds_arima else np.array([])
        arima_test_arr = np.array(test_vals, dtype=float) if test_vals else np.array([])
        mae_arima = _calc_mae(arima_test_arr, arima_pred_arr)
        smape_arima = _calc_smape(arima_test_arr, arima_pred_arr)
        if verbose:
            logger.info("Walk-forward (1-step) ARIMA MSE: %.3f, R2: %.3f", mse_arima, r2_arima)

    # SES WF
    mse_ses, ses_preds = walk_forward_ses(monthly_series_proc, n_test=n_test, exog=exog, exog_forecast=exog_forecast)
    ses_pred_arr = np.array(ses_preds, dtype=float) if ses_preds else np.array([])
    mae_ses = _calc_mae(test_arr, ses_pred_arr)
    smape_ses = _calc_smape(test_arr, ses_pred_arr)
    if verbose:
        logger.info("Walk-forward (1-step) SES MSE: %.3f", mse_ses)

    # Holt WF
    mse_holt, holt_preds = walk_forward_holt(monthly_series_proc, n_test=n_test, exog=exog, exog_forecast=exog_forecast)
    holt_pred_arr = np.array(holt_preds, dtype=float) if holt_preds else np.array([])
    mae_holt = _calc_mae(test_arr, holt_pred_arr)
    smape_holt = _calc_smape(test_arr, holt_pred_arr)
    if verbose:
        logger.info("Walk-forward (1-step) HOLT MSE: %.3f", mse_holt)

    # ETS WF
    ets_eligible = n >= ETS_MIN_POINTS
    if ets_eligible:
        mse_ets, ets_preds = walk_forward_ets(monthly_series_proc, n_test=n_test, exog=exog, exog_forecast=exog_forecast)
        ets_pred_arr = np.array(ets_preds, dtype=float) if ets_preds else np.array([])
        mae_ets = _calc_mae(test_arr, ets_pred_arr)
        smape_ets = _calc_smape(test_arr, ets_pred_arr)
        if verbose and np.isfinite(mse_ets):
            logger.info("Walk-forward (1-step) ETS MSE: %.3f", mse_ets)
    else:
        mse_ets, ets_preds = float("inf"), []
        ets_pred_arr = np.array([])
        mae_ets = None
        smape_ets = None
        if verbose:
            logger.info("Walk-forward (1-step) ETS skipped: minimum %s points required (n=%s).", ETS_MIN_POINTS, n)

    # AutoReg WF
    if short_series_guard:
        mse_autoreg, ar_preds = float("inf"), []
        ar_pred_arr = np.array([])
        mae_autoreg = None
        smape_autoreg = None
        if verbose:
            logger.info(
                f"Walk-forward (1-step) AUTOREG skipped: rövid sorozat (n={n}) "
                "miatt túl nagy lenne az overfit esélye."
            )
    else:
        mse_autoreg, ar_preds = walk_forward_autoreg(
            monthly_series_proc, n_test=n_test, lags=autoreg_lags, exog=exog, exog_forecast=exog_forecast)
        ar_pred_arr = np.array(ar_preds, dtype=float) if ar_preds else np.array([])
        mae_autoreg = _calc_mae(test_arr, ar_pred_arr)
        smape_autoreg = _calc_smape(test_arr, ar_pred_arr)
        if verbose:
            logger.info("Walk-forward (1-step) AUTOREG MSE: %.3f", mse_autoreg)

    # Behavioral WF
    behavioral_lags = min(BEHAVIORAL_MAX_LAGS, max(2, autoreg_lags + 1))
    mse_behavioral, behavioral_preds = walk_forward_behavioral(
        monthly_series_proc,
        n_test=n_test,
        lags=behavioral_lags,
        exog=exog,
        exog_forecast=exog_forecast,
    )
    behavioral_pred_arr = np.array(behavioral_preds, dtype=float) if behavioral_preds else np.array([])
    mae_behavioral = _calc_mae(test_arr, behavioral_pred_arr)
    smape_behavioral = _calc_smape(test_arr, behavioral_pred_arr)
    rw_mse_behavioral = _calc_recency_weighted_mse(test_arr, behavioral_pred_arr)
    turning_behavioral = _calc_turning_point_score(test_arr, behavioral_pred_arr)
    vol_ratio_behavioral = _calc_volatility_ratio(test_arr, behavioral_pred_arr)
    spike_recall_behavioral = _calc_spike_recall(test_arr, behavioral_pred_arr)
    if verbose and np.isfinite(mse_behavioral):
        logger.info(
            "Walk-forward (1-step) BEHAVIORAL "
            f"MSE: {mse_behavioral:.3f}, turn={turning_behavioral}, vol_ratio={vol_ratio_behavioral}"
        )

    # Prophet removed from the active pipeline because repeated refits made the
    # end-to-end forecasting path too slow for production use.
    prophet_eligible = False
    mse_prophet, prophet_preds = float("inf"), []
    prophet_pred_arr = np.array([])
    mae_prophet = None
    smape_prophet = None

    # --- Model selection: choose robust metric for sparse/skewed series ---
    zero_ratio = float((monthly_series_proc == 0).mean()) if n > 0 else 0.0
    try:
        skew_val = float(monthly_series_proc.skew()) if n > 2 else 0.0
    except Exception:
        skew_val = 0.0

    var = np.var(monthly_series_proc.values) if len(monthly_series_proc) > 1 else 1.0
    intermittent_series = zero_ratio >= 0.3
    low_variance_series = var <= 1e-9
    metric_choice = "smape" if (intermittent_series or abs(skew_val) >= 1.0 or low_variance_series) else "mse"

    # --- Model selection: keep ranking and gating on the same score scale ---
    def norm(mse: Optional[float]) -> float:
        if mse is None or not np.isfinite(mse):
            return float("inf")
        return float(mse / (var + 1e-9))

    def _metric_value(norm_mse: float, smape: Optional[float]) -> float:
        if metric_choice == "smape":
            return float(smape) if smape is not None and np.isfinite(smape) else float("inf")
        return norm_mse

    def _behavior_selection_score(
        norm_mse_val: float,
        smape_val: Optional[float],
        rw_mse_val: Optional[float],
        turn_score: Optional[float],
        vol_ratio: Optional[float],
        spike_recall: Optional[float],
    ) -> float:
        base_score = _metric_value(norm_mse_val, smape_val)
        if not np.isfinite(base_score):
            return float("inf")

        rw_norm = norm(rw_mse_val) if rw_mse_val is not None else base_score
        turn_penalty = 1.0 - float(turn_score) if turn_score is not None and np.isfinite(turn_score) else 0.5
        spike_penalty = 1.0 - float(spike_recall) if spike_recall is not None and np.isfinite(spike_recall) else 0.5
        if vol_ratio is None or not np.isfinite(vol_ratio) or vol_ratio <= 0:
            vol_penalty = 0.5
        else:
            vol_penalty = max(0.0, abs(vol_ratio - 1.0) - BEHAVIORAL_VARIANCE_TOLERANCE)

        return float(
            0.45 * base_score
            + 0.25 * rw_norm
            + 0.15 * turn_penalty
            + 0.10 * vol_penalty
            + 0.05 * spike_penalty
        )

    def _shape_score(candidate: dict[str, Any]) -> float:
        turn_score = _as_opt_float(candidate.get("turn_score"))
        spike_recall = _as_opt_float(candidate.get("spike_recall"))
        vol_ratio = _as_opt_float(candidate.get("vol_ratio"))
        turn_penalty = 1.0 - turn_score if turn_score is not None else 0.45
        spike_penalty = 1.0 - spike_recall if spike_recall is not None else 0.45
        if vol_ratio is None or not np.isfinite(vol_ratio) or vol_ratio <= 0:
            vol_penalty = 0.45
        else:
            vol_penalty = max(0.0, abs(vol_ratio - 1.0) - BEHAVIORAL_VARIANCE_TOLERANCE)
        return float(0.45 * turn_penalty + 0.35 * vol_penalty + 0.20 * spike_penalty)

    def _forecast_shape_preservation_score(fc: Optional[pd.Series]) -> float:
        """Lower is better: reward forecasts that preserve recent variability shape."""
        if fc is None or len(fc) < 3 or len(monthly_series_proc) < 6:
            return float("inf")

        try:
            recent = cast(pd.Series, monthly_series_proc.tail(min(6, len(monthly_series_proc))).astype(float))
            recent_diffs = recent.diff().dropna().astype(float)
            fc_float = cast(pd.Series, fc.astype(float))
            fc_diffs = fc_float.diff().dropna().astype(float)
            if len(recent_diffs) < 2 or len(fc_diffs) < 2:
                return float("inf")

            recent_diff_std = float(recent_diffs.std(ddof=0))
            fc_diff_std = float(fc_diffs.std(ddof=0))
            recent_range = float(recent.max() - recent.min())
            fc_range = float(fc_float.max() - fc_float.min())
            recent_mean = float(abs(recent.mean())) + 1e-9
            recent_median = float(recent.median())
            first_step_gap = abs(float(fc_float.iloc[0]) - float(recent.iloc[-1])) / recent_mean
            floor_penalty = max(0.0, (recent_median * 0.72 - float(fc_float.min())) / max(recent_median, 1.0))

            prev_recent = recent.iloc[:-1]
            rebound_penalty = 0.0
            if len(prev_recent) >= 2:
                prev_anchor = float(prev_recent.median())
                last_actual = float(recent.iloc[-1])
                if np.isfinite(prev_anchor) and prev_anchor > 0.0 and last_actual < prev_anchor * 0.72:
                    rebound_target = prev_anchor * 0.85
                    rebound_penalty = max(0.0, (rebound_target - float(fc_float.mean())) / prev_anchor)

            vol_ratio_penalty = abs(fc_diff_std - recent_diff_std) / max(recent_diff_std, 1.0)
            range_ratio_penalty = abs(fc_range - recent_range) / max(recent_range, 1.0)
            monotone_penalty = 1.0 if float(fc_diffs.std(ddof=0)) <= max(0.08 * max(recent_diff_std, 1.0), 1e-9) else 0.0
            return float(
                0.42 * vol_ratio_penalty
                + 0.18 * range_ratio_penalty
                + 0.12 * first_step_gap
                + 0.08 * monotone_penalty
                + 0.12 * floor_penalty
                + 0.08 * rebound_penalty
            )
        except Exception:
            return float("inf")

    def _align_forecast_to_index(fc: Optional[pd.Series], target_index: pd.Index) -> Optional[pd.Series]:
        if fc is None:
            return None
        try:
            fc = cast(pd.Series, fc.astype(float))
        except Exception:
            return None

        if len(fc) != len(target_index):
            return None
        if fc.index.equals(target_index):
            return fc

        try:
            reindexed = fc.reindex(target_index)
            if not reindexed.isna().any():
                return cast(pd.Series, reindexed.astype(float))
        except Exception:
            pass

        return pd.Series(fc.values, index=target_index, dtype=float)

    def _slice_preview_exog(target_index: pd.Index, train_index: pd.Index) -> tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        if exog is None or not isinstance(exog, pd.DataFrame) or exog.empty:
            return None, None
        try:
            preview_exog_train = exog.reindex(train_index).apply(pd.to_numeric, errors="coerce").ffill().fillna(0.0)
            preview_exog_future = exog.reindex(target_index).apply(pd.to_numeric, errors="coerce").ffill().fillna(0.0)
            return preview_exog_train, preview_exog_future
        except Exception:
            return None, None

    def _forecast_candidate_for_preview(
        model_name: str,
        train_series: pd.Series,
        horizon: int,
        target_index: pd.Index,
    ) -> Optional[pd.Series]:
        preview_exog_train, preview_exog_future = _slice_preview_exog(target_index, train_series.index)
        try:
            if model_name == "behavioral":
                _, fc, _ = fit_and_forecast_behavioral_boosted(
                    train_series,
                    lags=behavioral_lags,
                    steps=horizon,
                    exog=preview_exog_train,
                    exog_forecast=preview_exog_future,
                )
            elif model_name == "holt":
                fc, _ = fit_and_forecast_holt(train_series, steps=horizon, exog=preview_exog_train, exog_forecast=preview_exog_future)
            elif model_name == "ets":
                fc, _ = fit_and_forecast_ets(train_series,
                                             steps=horizon,
                                             exog=preview_exog_train,
                                             exog_forecast=preview_exog_future)
            elif model_name == "ses":
                fc, _ = fit_and_forecast_ses(train_series, steps=horizon, exog=preview_exog_train, exog_forecast=preview_exog_future)
            elif model_name == "autoreg":
                _, fc, _ = fit_and_forecast_autoreg(
                    train_series,
                    lags=autoreg_lags,
                    steps=horizon,
                    exog=preview_exog_train,
                    exog_forecast=preview_exog_future,
                )
            elif model_name == "arima":
                preview_can_use_exog = bool(
                    preview_exog_train is not None and len(train_series) >= SARIMAX_EXOG_MIN_POINTS
                )
                if preview_can_use_exog:
                    _, fc, _ = fit_and_forecast_sarimax(
                        train_series,
                        order=arima_order,
                        seasonal_order=seasonal_order,
                        steps=horizon,
                        use_log=False,
                        exog=preview_exog_train,
                        exog_forecast=preview_exog_future,
                    )
                else:
                    _, fc, _ = fit_and_forecast_arima(
                        train_series,
                        order=arima_order,
                        steps=horizon,
                        use_log=False,
                    )
            else:
                return None
        except Exception:
            return None

        return _align_forecast_to_index(fc, target_index)

    def _calc_preview_score(train_series: pd.Series, actual_series: pd.Series, candidate: dict[str, Any]) -> Optional[dict[str, Any]]:
        fc = _forecast_candidate_for_preview(candidate["name"], train_series, len(actual_series), actual_series.index)
        if fc is None or len(fc) != len(actual_series):
            return None

        y_true = actual_series.values.astype(float)
        y_pred = fc.values.astype(float)
        mse_val = float(np.mean((y_true - y_pred) ** 2))
        smape_val = _calc_smape(y_true, y_pred)
        turn_score = _calc_turning_point_score(y_true, y_pred)
        vol_ratio = _calc_volatility_ratio(y_true, y_pred)
        spike_recall = _calc_spike_recall(y_true, y_pred)
        preview_primary = _metric_value(norm(mse_val), smape_val)
        preview_shape = _shape_score(
            {
                "turn_score": turn_score,
                "vol_ratio": vol_ratio,
                "spike_recall": spike_recall,
            }
        )
        preview_selection_score = float(
            (1.0 - PREVIEW_SCORE_WEIGHT) * preview_primary
            + PREVIEW_SCORE_WEIGHT * preview_shape
        )
        return {
            "forecast": fc,
            "mse": mse_val,
            "smape": smape_val,
            "turn_score": turn_score,
            "vol_ratio": vol_ratio,
            "spike_recall": spike_recall,
            "selection_score": preview_selection_score,
        }

    def _regularize_short_forecast(
        base_name: str,
        ses_fc: Optional[pd.Series],
        holt_fc: Optional[pd.Series],
    ) -> Optional[pd.Series]:
        """
        Two-layer expressive forecaster for short monthly series.

        LAYER 1 – Fourier Ridge seasonal shape  (α = 3)
            Fits the smooth month-of-year spending curve as multiplicative
            ratios to the training mean.  α = 3 is intentionally moderate:
            captures the seasonal shape without interpolating every noise
            point, so training residuals are non-trivial and usable below.

        LAYER 2 – Spike residual projection
            residual[m] = actual_ratio[m] – Fourier_fitted_ratio[m]
            This delta captures the month-specific behavioural overshoot or
            undershoot that the smooth sinusoid misses (e.g. the extra +130k
            June surplus or the extra −140k July cliff).  Each spike is
            forward-projected but exponentially confidence-damped:
              contribution = spike × 0.70 × 0.65^horizon
            so near-term months are bold and far-future months revert to
            the smooth Fourier curve.

        LAYER 3 – Anchor + mild trend
            Absolute level = mean of last 4 confirmed full months.  Median-
            based trend clipped to ±8 % per month, decaying at 0.85^step.

        Partial-month guard: the first and last months of the recorded
        series are excluded from training when they look like partial months
        (< 65 % of the adjacent 4-month mean).
        """
        if ses_fc is None and holt_fc is None:
            return None
        if ses_fc is None:
            return holt_fc
        if holt_fc is None:
            return ses_fc

        idx = holt_fc.index if base_name == "holt" else ses_fc.index
        steps_local = len(idx)

        # ──────────────────────────────────────────────────────────────────
        # Branch A  ≥ 12 months  →  Fourier Ridge + spike residual layer
        # ──────────────────────────────────────────────────────────────────
        if len(monthly_series_proc) >= 12:
            try:
                from sklearn.linear_model import Ridge as _Ridge

                n_hist = len(monthly_series_proc)

                # 1. Detect partial boundary months
                first_val = float(monthly_series_proc.iloc[0])
                next_4_mean = (
                    float(monthly_series_proc.iloc[1:5].mean())
                    if n_hist >= 5 else float(monthly_series_proc.mean())
                )
                partial_first = first_val < 0.65 * next_4_mean

                last_val = float(monthly_series_proc.iloc[-1])
                prior_4_mean = (
                    float(monthly_series_proc.iloc[-5:-1].mean())
                    if n_hist >= 5 else float(monthly_series_proc.mean())
                )
                partial_last = last_val < 0.65 * prior_4_mean

                start_idx = 1 if partial_first else 0
                end_idx = (n_hist - 1) if partial_last else n_hist
                train_s = monthly_series_proc.iloc[start_idx:end_idx]
                n_tr = len(train_s)

                if n_tr < 6:
                    raise ValueError("Not enough clean training points")

                train_mean = float(train_s.mean())
                if train_mean < 1.0:
                    raise ValueError("Near-zero training mean")

                # 2. Multiplicative ratios relative to training mean
                y_ratio = train_s.values.astype(float) / train_mean
                m_tr = np.array([ts.month for ts in train_s.index], dtype=float)

                # 3. Fourier feature builder (3 harmonics: 12-, 6-, 4-month)
                def _fmat(months: np.ndarray) -> np.ndarray:
                    cols = []
                    for k in range(1, 4):
                        cols.append(np.sin(2 * np.pi * k * months / 12))
                        cols.append(np.cos(2 * np.pi * k * months / 12))
                    return np.column_stack(cols)

                X_tr = _fmat(m_tr)

                # α = 3: moderate — preserves seasonal shape AND leaves
                # non-trivial training residuals for the spike layer.
                # (α = 0.1 near-OLS destroys residuals; α = 20 destroys shape)
                ridge = _Ridge(alpha=3.0, fit_intercept=True)
                ridge.fit(X_tr, y_ratio)

                # 4. Spike layer: per-calendar-month residual
                smooth_tr = ridge.predict(X_tr)
                spike_ratio = y_ratio - smooth_tr
                spike_by_m = {
                    int(m_tr[i]): float(spike_ratio[i])
                    for i in range(n_tr)
                }

                # 5. Anchor + trend (last 4 confirmed full months)
                anchor_window = min(4, n_tr)
                anchor_level = float(train_s.iloc[-anchor_window:].mean())
                anchor_diffs = train_s.iloc[-anchor_window:].diff().dropna()
                raw_trend = float(anchor_diffs.median()) if len(anchor_diffs) > 0 else 0.0
                trend_clip = 0.08 * max(anchor_level, 1.0)
                trend = float(np.clip(raw_trend, -trend_clip, trend_clip))

                # 6. Forecast
                m_fc = np.array([ts.month for ts in idx], dtype=float)
                X_fc = _fmat(m_fc)
                smooth_fc = ridge.predict(X_fc)

                # Spike cap: ±35 % of anchor keeps the model bold but sane
                spike_cap = 0.35 * anchor_level

                fc_vals_list: list = []
                for i, m in enumerate(m_fc.astype(int)):
                    seasonal = float(smooth_fc[i]) * anchor_level
                    raw_spike = spike_by_m.get(m, 0.0) * anchor_level
                    spike = float(np.clip(raw_spike, -spike_cap, spike_cap))
                    # 70 % base confidence, decays 35 % per forecast step
                    spike_contrib = spike * 0.70 * (0.65 ** i)
                    trend_comp = trend * (0.85 ** i)
                    fc_vals_list.append(seasonal + spike_contrib + trend_comp)

                reg = pd.Series(fc_vals_list, index=idx, name="fourier_ridge_spike")
                return reg.clip(lower=0.0)

            except Exception:
                pass  # fall through to Branch B

        # ──────────────────────────────────────────────────────────────────
        # Branch B  < 12 months  →  trend-forward model forecast
        # ──────────────────────────────────────────────────────────────────
        model_fc = holt_fc if base_name == "holt" else ses_fc
        recent_window = min(6, len(monthly_series_proc))
        recent = monthly_series_proc.tail(recent_window).astype(float)
        recent_median = float(recent.median())
        last_val_b = float(monthly_series_proc.iloc[-1])

        recent_diffs = recent.diff().dropna()
        raw_trend_b = float(recent_diffs.median()) if len(recent_diffs) > 0 else 0.0
        trend_clip_b = 0.25 * max(recent_median, 1.0)
        trend_b = float(np.clip(raw_trend_b, -trend_clip_b, trend_clip_b))

        drift = np.array([trend_b * (0.90 ** i) for i in range(steps_local)], dtype=float)
        level = last_val_b + drift
        reg_vals = 0.70 * model_fc.values + 0.30 * level
        reg = pd.Series(reg_vals, index=idx, name=f"short_behavioral_{base_name}")
        return reg.clip(lower=0.0)

    def _as_opt_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            f = float(value)
        except (TypeError, ValueError):
            return None
        return f if np.isfinite(f) else None

    candidates: list[dict[str, Any]] = [
        {
            "name": "arima",
            "mse": mse_arima,
            "norm_mse": norm(mse_arima),
            "smape": smape_arima,
            "rw_mse": _calc_recency_weighted_mse(arima_test_arr, arima_pred_arr),
            "turn_score": _calc_turning_point_score(arima_test_arr, arima_pred_arr),
            "vol_ratio": _calc_volatility_ratio(arima_test_arr, arima_pred_arr),
            "spike_recall": _calc_spike_recall(arima_test_arr, arima_pred_arr),
            "eligible": not short_series_guard,
        },
        {
            "name": "ses",
            "mse": mse_ses,
            "norm_mse": norm(mse_ses),
            "smape": smape_ses,
            "rw_mse": _calc_recency_weighted_mse(test_arr, ses_pred_arr),
            "turn_score": _calc_turning_point_score(test_arr, ses_pred_arr),
            "vol_ratio": _calc_volatility_ratio(test_arr, ses_pred_arr),
            "spike_recall": _calc_spike_recall(test_arr, ses_pred_arr),
            "eligible": True,
        },
        {
            "name": "holt",
            "mse": mse_holt,
            "norm_mse": norm(mse_holt),
            "smape": smape_holt,
            "rw_mse": _calc_recency_weighted_mse(test_arr, holt_pred_arr),
            "turn_score": _calc_turning_point_score(test_arr, holt_pred_arr),
            "vol_ratio": _calc_volatility_ratio(test_arr, holt_pred_arr),
            "spike_recall": _calc_spike_recall(test_arr, holt_pred_arr),
            "eligible": True,
        },
        {
            "name": "ets",
            "mse": mse_ets,
            "norm_mse": norm(mse_ets),
            "smape": smape_ets,
            "rw_mse": _calc_recency_weighted_mse(test_arr, ets_pred_arr),
            "turn_score": _calc_turning_point_score(test_arr, ets_pred_arr),
            "vol_ratio": _calc_volatility_ratio(test_arr, ets_pred_arr),
            "spike_recall": _calc_spike_recall(test_arr, ets_pred_arr),
            "eligible": ets_eligible,
        },
        {
            "name": "autoreg",
            "mse": mse_autoreg,
            "norm_mse": norm(mse_autoreg),
            "smape": smape_autoreg,
            "rw_mse": _calc_recency_weighted_mse(test_arr, ar_pred_arr),
            "turn_score": _calc_turning_point_score(test_arr, ar_pred_arr),
            "vol_ratio": _calc_volatility_ratio(test_arr, ar_pred_arr),
            "spike_recall": _calc_spike_recall(test_arr, ar_pred_arr),
            "eligible": not short_series_guard,
        },
        {
            "name": "behavioral",
            "mse": mse_behavioral,
            "norm_mse": norm(mse_behavioral),
            "smape": smape_behavioral,
            "rw_mse": rw_mse_behavioral,
            "turn_score": turning_behavioral,
            "vol_ratio": vol_ratio_behavioral,
            "spike_recall": spike_recall_behavioral,
            "eligible": True,
        },
    ]

    for c in candidates:
        if "selection_score" not in c:
            base_selection_score = (
                _metric_value(float(c["norm_mse"]), _as_opt_float(c.get("smape")))
                if bool(c["eligible"]) else float("inf")
            )
            if c["name"] == "behavioral":
                c["selection_score"] = _behavior_selection_score(
                    float(c["norm_mse"]),
                    _as_opt_float(c.get("smape")),
                    _as_opt_float(c.get("rw_mse")),
                    _as_opt_float(c.get("turn_score")),
                    _as_opt_float(c.get("vol_ratio")),
                    _as_opt_float(c.get("spike_recall")),
                )
            else:
                c["selection_score"] = base_selection_score

    candidates_sorted = sorted(candidates, key=lambda x: x["selection_score"])
    candidate_by_name = {c["name"]: c for c in candidates_sorted}
    eligible_candidates = [c for c in candidates_sorted if c["eligible"]]
    # Fallback to minimal SES model if no eligible candidates (which shouldn't happen)
    chosen = eligible_candidates[0]["name"] if eligible_candidates else "ses"

    # Detect mild annual seasonality signal for tie-breaks on longer monthly series.
    seasonal_strength = float("nan")
    if len(monthly_series_proc) >= 18:
        try:
            seasonal_strength = float(monthly_series_proc.autocorr(lag=12))
        except Exception:
            seasonal_strength = float("nan")
    has_detected_seasonality = np.isfinite(seasonal_strength) and seasonal_strength >= 0.35

    baseline_selection_score = (
        baseline_smape if metric_choice == "smape" else norm(baseline_mse)
    )
    selected_score = candidate_by_name[chosen]["selection_score"]
    selection_reason = "best_candidate"
    preview_horizon = min(FORECAST_STEPS, n_test)
    preview_scores_by_name: dict[str, float] = {}
    preview_selected_candidate: Optional[str] = None
    preview_override_applied = False

    # Short, human-driven monthly series should prefer models that preserve volatility,
    # even when plain MSE is only marginally better for smoother alternatives.
    behavioral_candidate = candidate_by_name.get("behavioral")
    if short_series_guard and behavioral_candidate is not None and np.isfinite(behavioral_candidate["selection_score"]):
        behavioral_turn = _as_opt_float(behavioral_candidate.get("turn_score"))
        behavioral_vol = _as_opt_float(behavioral_candidate.get("vol_ratio"))
        if chosen != "behavioral" and np.isfinite(selected_score):
            is_behaviorally_close = behavioral_candidate["selection_score"] <= selected_score * 1.08
            preserves_turns = behavioral_turn is not None and behavioral_turn >= 0.50
            preserves_variance = (
                behavioral_vol is not None and np.isfinite(behavioral_vol)
                and 0.70 <= float(behavioral_vol) <= 1.45
            )
            if is_behaviorally_close and (preserves_turns or preserves_variance):
                chosen = "behavioral"
                selected_score = behavioral_candidate["selection_score"]
                selection_reason = "behavioral_short_series_priority"

    # If SES is only marginally better but seasonality exists, prefer a non-SES model.
    if chosen == "ses" and has_detected_seasonality and np.isfinite(selected_score):
        for c in candidates_sorted:
            if c["name"] == "ses":
                continue
            if np.isfinite(c["selection_score"]) and c["selection_score"] <= selected_score * 1.03:
                chosen = c["name"]
                selected_score = c["selection_score"]
                selection_reason = "seasonality_tiebreak"
                break

    # If multiple candidates are effectively tied on the primary score, prefer
    # the one that better preserves month-to-month shape instead of always
    # collapsing to the smoothest trend line.
    current_candidate = candidate_by_name.get(chosen)
    if current_candidate is not None and np.isfinite(selected_score):
        current_shape_score = _shape_score(current_candidate)
        current_vol_ratio = _as_opt_float(current_candidate.get("vol_ratio"))
        current_is_too_smooth = (
            current_vol_ratio is not None
            and np.isfinite(current_vol_ratio)
            and current_vol_ratio < SELECTION_SMOOTH_VOL_FLOOR
        )
        close_alternatives = [
            c for c in eligible_candidates
            if c["name"] != chosen
            and np.isfinite(c["selection_score"])
            and c["selection_score"] <= selected_score * (1.0 + SELECTION_CLOSE_MARGIN)
        ]
        best_alternative = None
        best_alternative_shape = float("inf")
        for alt in close_alternatives:
            alt_shape_score = _shape_score(alt)
            alt_vol_ratio = _as_opt_float(alt.get("vol_ratio"))
            alt_has_healthier_variance = (
                alt_vol_ratio is not None
                and np.isfinite(alt_vol_ratio)
                and SELECTION_SMOOTH_VOL_FLOOR <= alt_vol_ratio <= 1.55
            )
            clearly_better_shape = alt_shape_score + SELECTION_SHAPE_IMPROVEMENT < current_shape_score
            preferred_smoothness_fix = current_is_too_smooth and alt_has_healthier_variance and alt_shape_score <= current_shape_score + 0.02
            if (clearly_better_shape or preferred_smoothness_fix) and alt_shape_score < best_alternative_shape:
                best_alternative = alt
                best_alternative_shape = alt_shape_score

        if best_alternative is not None:
            chosen = best_alternative["name"]
            selected_score = best_alternative["selection_score"]
            selection_reason = "shape_tiebreak"

    if (
        _FORCE_MODEL is None
        and not short_series_guard
        and preview_horizon >= PREVIEW_MIN_HORIZON
        and len(monthly_series_proc) > preview_horizon
    ):
        preview_train = monthly_series_proc.iloc[:-preview_horizon].copy()
        preview_actual = monthly_series_proc.iloc[-preview_horizon:].copy()
        preview_candidates = [
            c for c in eligible_candidates[:PREVIEW_TOP_K]
            if np.isfinite(c["selection_score"])
        ]
        preview_ranked: list[tuple[float, str]] = []
        for cand in preview_candidates:
            preview_result = _calc_preview_score(preview_train, preview_actual, cand)
            if preview_result is None:
                continue
            cand["preview_mse"] = preview_result["mse"]
            cand["preview_smape"] = preview_result["smape"]
            cand["preview_turn_score"] = preview_result["turn_score"]
            cand["preview_vol_ratio"] = preview_result["vol_ratio"]
            cand["preview_spike_recall"] = preview_result["spike_recall"]
            cand["preview_selection_score"] = preview_result["selection_score"]
            preview_scores_by_name[cand["name"]] = float(preview_result["selection_score"])
            preview_ranked.append((float(preview_result["selection_score"]), cand["name"]))

        preview_ranked.sort(key=lambda item: item[0])
        if preview_ranked:
            preview_selected_candidate = preview_ranked[0][1]
            chosen_preview_score = preview_scores_by_name.get(chosen)
            best_preview_score = preview_ranked[0][0]
            if (
                chosen_preview_score is not None
                and preview_selected_candidate != chosen
                and best_preview_score <= chosen_preview_score * (1.0 - PREVIEW_OVERRIDE_MARGIN)
            ):
                chosen = preview_selected_candidate
                selected_score = candidate_by_name.get(chosen, {}).get("selection_score", selected_score)
                selection_reason = "preview_horizon_override"
                preview_override_applied = True

    # Safety: check if chosen model's normalized MSE is unstable
    chosen_norm_mse = candidate_by_name.get(chosen, {}).get("norm_mse", float("inf"))
    if not np.isfinite(chosen_norm_mse) or chosen_norm_mse > MAX_NORMALIZED_MSE:
        logger.warning(
            f"⚠️ A model választás bizonytalan (norm_mse={chosen_norm_mse}); "
            "választás egyszerűsítése."
        )
        selection_reason = "stability_fallback"
        if len(monthly_series_proc) >= 12:
            chosen = 'behavioral' if short_series_guard else ('ses' if np.var(monthly_series_proc.values) == 0 else 'holt')
        else:
            chosen = 'behavioral'
        selected_score = candidate_by_name.get(chosen, {}).get("selection_score", float("inf"))

    # If ARIMA was chosen but has negative R2, switch to simpler model
    if chosen == 'arima' and not np.isfinite(r2_arima):
        pass
    elif chosen == 'arima' and r2_arima < 0:
        logger.warning("ARIMA WF R2 negatív (%.3f), váltás egyszerűbb modellre.", r2_arima)
        chosen = 'holt'
        selection_reason = "arima_negative_r2"
        selected_score = candidate_by_name.get(chosen, {}).get("selection_score", float("inf"))

    # Baseline gating: only upgrade if chosen model beats seasonal-naive by a margin
    # If not beating baseline, fall back to minimal SES model instead of baseline
    if np.isfinite(baseline_selection_score) and not short_series_guard:
        chosen_selection_score = float(candidate_by_name.get(chosen, {}).get("selection_score", selected_score))
        improvement_threshold = baseline_selection_score * (1.0 - BASELINE_REL_IMPROVEMENT)
        if np.isfinite(chosen_selection_score) and chosen_selection_score > improvement_threshold:
            if verbose:
                logger.info(
                    "⚠️ A választott modell nem veri a baseline-t elég erősen; "
                    "minimális SES modellre váltás."
                )
            chosen = "ses"
            selected_score = candidate_by_name.get("ses", {}).get("selection_score", baseline_selection_score)
            selection_reason = "baseline_gate"
        else:
            selected_score = chosen_selection_score

    mean_forecast = None
    ci = None
    final_model_name = chosen

    def _has_unjustified_first_step_cliff(
        fc: Optional[pd.Series],
        orig: pd.Series,
        floor_ratio: float = 0.60,
    ) -> bool:
        """Flag forecasts whose first point drops implausibly far below the recent level.

        We compare the first forecast point to the median of the last few confirmed
        months, not just the final month, so a single spike does not dominate the
        handoff check. If the latest observed month is already heavily depressed
        versus the immediately preceding months, we allow a lower first forecast.
        """
        if fc is None or not isinstance(fc, pd.Series) or len(fc) == 0 or len(orig) < 4:
            return False

        try:
            recent = cast(pd.Series, orig.tail(min(4, len(orig))).astype(float))
            first_val = float(fc.iloc[0])
            anchor = float(recent.median())
            if not np.isfinite(first_val) or not np.isfinite(anchor) or anchor <= 0.0:
                return False

            severe_downside = first_val < anchor * floor_ratio
            if not severe_downside:
                return False

            prev_recent = recent.iloc[:-1]
            if len(prev_recent) == 0:
                return True

            prev_anchor = float(prev_recent.median())
            last_actual = float(recent.iloc[-1])
            latest_already_depressed = (
                np.isfinite(prev_anchor)
                and prev_anchor > 0.0
                and last_actual < prev_anchor * 0.70
            )
            return not latest_already_depressed
        except Exception:
            return False

    def _has_unjustified_downside_collapse(
        fc: Optional[pd.Series],
        orig: pd.Series,
    ) -> bool:
        """Flag forecasts that collapse too far below the recent baseline.

        This is stricter than the first-step cliff check: it looks across the full
        horizon and protects against candidates that are wavy but drift into an
        implausibly deep downturn.
        """
        if fc is None or not isinstance(fc, pd.Series) or len(fc) == 0 or len(orig) < 4:
            return False

        try:
            recent = cast(pd.Series, orig.tail(min(4, len(orig))).astype(float))
            recent_median = float(recent.median())
            fc_min = float(fc.min())
            fc_mean = float(fc.mean())
            if not np.isfinite(recent_median) or recent_median <= 0.0:
                return False

            if fc_min < recent_median * 0.55:
                return True

            prev_recent = recent.iloc[:-1]
            if len(prev_recent) >= 2:
                prev_anchor = float(prev_recent.median())
                last_actual = float(recent.iloc[-1])
                if np.isfinite(prev_anchor) and prev_anchor > 0.0 and last_actual < prev_anchor * 0.72:
                    if fc_mean < prev_anchor * 0.82 or fc_min < prev_anchor * 0.68:
                        return True
            return False
        except Exception:
            return False

    def _forecast_is_sane(fc: Optional[pd.Series], orig: pd.Series,
                         scale_factor: float = FORECAST_SCALE_FACTOR) -> bool:
        """Check if forecast values are numerically reasonable."""
        if fc is None or not isinstance(fc, pd.Series):
            return False
        if fc.isna().any():
            return False
        if np.isinf(fc.values).any():
            return False
        if (fc < 0).any():
            return False
        if orig.max() > 0 and (fc.max() > orig.max() * scale_factor):
            return False
        return True

    def try_model(model_name: str) -> bool:
        """Try fitting a specific model."""
        nonlocal mean_forecast, ci, final_model_name

        if model_name == "baseline":
            mean_forecast = seasonal_naive(monthly_series_proc, FORECAST_STEPS)
            ci = None
        elif model_name == "behavioral":
            _, mean_forecast, ci = fit_and_forecast_behavioral_boosted(
                monthly_series_proc,
                lags=behavioral_lags,
                steps=FORECAST_STEPS,
                exog=exog if exog is not None else None,
                exog_forecast=exog_forecast if exog_forecast is not None else None,
            )
            if mean_forecast is not None:
                final_model_name = "behavioral_quantile_boost"
        elif model_name == "holt":
            mean_forecast, ci = fit_and_forecast_holt(monthly_series_proc, steps=FORECAST_STEPS, exog=exog, exog_forecast=exog_forecast)
            if short_series_guard and _FORCE_MODEL is None:
                ses_fc, _ = fit_and_forecast_ses(monthly_series_proc, steps=FORECAST_STEPS, exog=exog, exog_forecast=exog_forecast)
                reg_fc = _regularize_short_forecast("holt", ses_fc, mean_forecast)
                if reg_fc is not None:
                    mean_forecast = reg_fc
                    ci = None
                    final_model_name = (reg_fc.name or "short_behavioral_holt")
        elif model_name == "ets":
            mean_forecast, ci = fit_and_forecast_ets(monthly_series_proc, steps=FORECAST_STEPS, exog=exog, exog_forecast=exog_forecast)
        elif model_name == "ses":
            mean_forecast, ci = fit_and_forecast_ses(monthly_series_proc, steps=FORECAST_STEPS, exog=exog, exog_forecast=exog_forecast)
            if short_series_guard and _FORCE_MODEL is None:
                holt_fc, _ = fit_and_forecast_holt(monthly_series_proc, steps=FORECAST_STEPS, exog=exog, exog_forecast=exog_forecast)
                reg_fc = _regularize_short_forecast("ses", mean_forecast, holt_fc)
                if reg_fc is not None:
                    mean_forecast = reg_fc
                    ci = None
                    final_model_name = (reg_fc.name or "short_behavioral_ses")
        elif model_name == "autoreg":
            _, mean_forecast, ci = fit_and_forecast_autoreg(
                monthly_series_proc, lags=autoreg_lags, steps=FORECAST_STEPS,
                exog=exog if exog is not None else None,
                exog_forecast=exog_forecast if exog_forecast is not None else None)
        elif model_name == "arima":
            # Use SARIMAX if exog available
            if can_use_exog:
                _, mean_forecast, ci = fit_and_forecast_sarimax(
                    monthly_series_proc, order=arima_order,
                    seasonal_order=seasonal_order, steps=FORECAST_STEPS, use_log=False,
                    exog=exog, exog_forecast=exog_forecast)
            else:
                _, mean_forecast, ci = fit_and_forecast_arima(
                    monthly_series_proc, order=arima_order,
                    steps=FORECAST_STEPS, use_log=False)
        return _forecast_is_sane(mean_forecast, monthly_series_proc,
                                scale_factor=FORECAST_SCALE_FACTOR)

    # Try primary model
    if _FORCE_MODEL is not None:
        chosen = str(_FORCE_MODEL)
    ok = try_model(chosen)

    def _best_non_baseline_fallback(
        label: str,
        require_non_flat: bool = False,
        reject_first_step_cliff: bool = False,
    ) -> None:
        """Try every real model in ascending WF-MSE order and use the first sane result.
        The seasonal-naive baseline is NEVER chosen here — it is only kept as an
        absolute last resort inside the None-guard further below."""
        nonlocal mean_forecast, ci, final_model_name

        def _candidate_is_acceptable(fc_candidate: Optional[pd.Series]) -> bool:
            if not _forecast_is_sane(fc_candidate, monthly_series_proc, scale_factor=FORECAST_SCALE_FACTOR):
                return False
            if require_non_flat and is_flat(fc_candidate, rel_tol=0.01):
                return False
            if reject_first_step_cliff and _has_unjustified_first_step_cliff(fc_candidate, monthly_series_proc):
                return False
            if (require_non_flat or reject_first_step_cliff) and _has_unjustified_downside_collapse(fc_candidate, monthly_series_proc):
                return False
            return True

        # Build a ranked list of (mse, name, forecast_fn) for all real models.
        # Any model with infinite / NaN MSE goes to the back.
        def _safe_mse(v):
            return float(v) if (v is not None and np.isfinite(float(v))) else float("inf")

        ranked = sorted([
            (_safe_mse(mse_behavioral), "behavioral",
             lambda: fit_and_forecast_behavioral_boosted(
                 monthly_series_proc, lags=behavioral_lags, steps=FORECAST_STEPS,
                 exog=exog, exog_forecast=exog_forecast)),
            (_safe_mse(mse_holt), "holt",
             lambda: (None, *fit_and_forecast_holt(monthly_series_proc, steps=FORECAST_STEPS, exog=exog, exog_forecast=exog_forecast))),
            (_safe_mse(mse_ets) if ets_eligible else float("inf"), "ets",
             lambda: (None, *fit_and_forecast_ets(monthly_series_proc, steps=FORECAST_STEPS, exog=exog, exog_forecast=exog_forecast))),
            (_safe_mse(mse_ses), "ses",
             lambda: (None, *fit_and_forecast_ses(monthly_series_proc, steps=FORECAST_STEPS, exog=exog, exog_forecast=exog_forecast))),
            (_safe_mse(mse_autoreg) if not short_series_guard else float("inf"), "autoreg",
             lambda: fit_and_forecast_autoreg(
                 monthly_series_proc, lags=autoreg_lags, steps=FORECAST_STEPS,
                 exog=exog, exog_forecast=exog_forecast)),
            (_safe_mse(mse_arima) if not short_series_guard else float("inf"), "arima",
             lambda: fit_and_forecast_arima(
                 monthly_series_proc, order=arima_order, steps=FORECAST_STEPS, use_log=False)),
        ], key=lambda x: x[0])

        # Also append SARIMAX and time-reg as unranked safety nets (no WF MSE available)
        extra = [
            ("sarimax_fallback",
             lambda: fit_and_forecast_sarimax(
                 monthly_series_proc, order=arima_order, seasonal_order=seasonal_order,
                 steps=FORECAST_STEPS, use_log=False)),
            ("time_reg_fallback",
             lambda: fit_and_forecast_time_regression_boosted(
                 monthly_series_proc, steps=FORECAST_STEPS, lags_for_features=3,
                 exog=exog, exog_forecast=exog_forecast)),
        ]

        accepted_ranked: list[tuple[float, float, str, pd.Series, Any]] = []

        for mse_score, name, fn in ranked:
            try:
                result = fn()
                # result may be (model_info, fc, ci_df) or (fc, ci_df) depending on wrapper
                if isinstance(result, tuple) and len(result) == 3:
                    _, fc_candidate, ci_candidate = result
                elif isinstance(result, tuple) and len(result) == 2:
                    fc_candidate, ci_candidate = result
                else:
                    continue
                if _candidate_is_acceptable(fc_candidate):
                    if require_non_flat or reject_first_step_cliff:
                        accepted_ranked.append((
                            float(mse_score),
                            _forecast_shape_preservation_score(fc_candidate),
                            name,
                            fc_candidate,
                            ci_candidate,
                        ))
                    else:
                        mean_forecast, ci = fc_candidate, ci_candidate
                        final_model_name = f"{name}_fallback"
                        logger.info("%s → %s fallback ok.", label, name)
                        return
            except Exception:
                continue

        if accepted_ranked:
            best_mse = min(item[0] for item in accepted_ranked)
            close_candidates = [item for item in accepted_ranked if item[0] <= best_mse * 1.25]
            _, _, best_name, best_fc, best_ci = min(close_candidates, key=lambda item: (item[1], item[0]))
            mean_forecast, ci = best_fc, best_ci
            final_model_name = f"{best_name}_fallback"
            logger.info("%s → %s fallback ok (shape-aware).", label, best_name)
            return

        for extra_name, fn in extra:
            try:
                result = fn()
                if isinstance(result, tuple) and len(result) == 3:
                    _, fc_candidate, ci_candidate = result
                elif isinstance(result, tuple) and len(result) == 2:
                    fc_candidate, ci_candidate = result
                else:
                    continue
                if _candidate_is_acceptable(fc_candidate):
                    mean_forecast, ci = fc_candidate, ci_candidate
                    final_model_name = extra_name
                    logger.info("%s → %s ok.", label, extra_name)
                    return
            except Exception:
                continue

        if require_non_flat:
            logger.warning("%s: nem találtam elég stabil és nem lapos alternatívát.", label)
        elif reject_first_step_cliff:
            logger.warning("%s: nem találtam elég stabil, induláskor nem beszakadó alternatívát.", label)
        else:
            logger.warning("%s: minden modell sikertelenül futott, None marad.", label)

    if not ok:
        logger.warning("A választott modell (%s) numerikailag gyanús vagy nem futott: %s", chosen, mean_forecast)
        _best_non_baseline_fallback("primary fallback")

    # Check for flat forecasts and replace with best non-baseline model
    if _FORCE_MODEL is None and mean_forecast is not None and is_flat(mean_forecast, rel_tol=0.01):
        logger.warning("Forecast túl lapos — legjobb nem-baseline modellre váltok.")
        prev_fc, prev_ci, prev_name = mean_forecast, ci, final_model_name
        _best_non_baseline_fallback("flat fallback", require_non_flat=True)
        # If _best helper found nothing better, keep what we had
        if mean_forecast is None or is_flat(mean_forecast, rel_tol=0.01):
            mean_forecast, ci, final_model_name = prev_fc, prev_ci, prev_name

    # Reject forecasts that start with an implausibly sharp cliff versus the recent months.
    if _FORCE_MODEL is None and mean_forecast is not None and _has_unjustified_first_step_cliff(mean_forecast, monthly_series_proc):
        logger.warning("Forecast első pontja túl nagy lefelé ugrást mutat — alternatív modellt keresek.")
        prev_fc, prev_ci, prev_name = mean_forecast, ci, final_model_name
        _best_non_baseline_fallback("cliff fallback", reject_first_step_cliff=True)
        if mean_forecast is None or _has_unjustified_first_step_cliff(mean_forecast, monthly_series_proc):
            mean_forecast, ci, final_model_name = prev_fc, prev_ci, prev_name

    # Ensure pd.Series index
    if isinstance(mean_forecast, (np.ndarray, list)):
        mean_forecast = pd.Series(
            mean_forecast,
            index=pd.date_range(start=monthly_series_proc.index[-1] + pd.offsets.MonthEnd(1),
                               periods=len(mean_forecast), freq="ME"))

    if mean_forecast is None:
        logger.warning("Emergency: mean_forecast is None, trying best non-baseline model.")
        _best_non_baseline_fallback("emergency fallback")

    # Absolute last resort: if every model failed numerically, fall back to seasonal-naive
    if mean_forecast is None:
        mean_forecast = seasonal_naive(monthly_series_proc, FORECAST_STEPS)
        ci = None
        final_model_name = "baseline_emergency_fallback"
        logger.warning("Emergency: minden modell sikertelenül futott — seasonal-naive baseline.")

    # Clamp negative and extremely large values
    try:
        mean_forecast = mean_forecast.clip(lower=0.0)
        max_allowed = max(monthly_series_proc.max() * 20.0, MAX_OUTPUT_CAP)
        mean_forecast = mean_forecast.clip(upper=max_allowed)
        ci_df = ci if isinstance(ci, pd.DataFrame) else None
        if ci_df is not None:
            ci_df["lower"] = ci_df["lower"].clip(lower=0.0)
            ci_df["upper"] = ci_df["upper"].clip(upper=max_allowed)
            ci = ci_df
    except Exception:
        pass

    # Generate baseline for comparison
    try:
        baseline_vals = seasonal_naive(monthly_series_proc, FORECAST_STEPS)
    except Exception:
        baseline_vals = None

    plot_results(monthly_series_proc, forecast_mean=mean_forecast, forecast_ci=ci,
                 baseline_preds=(baseline_vals.tolist() if baseline_vals is not None else None), plot=plot)

    # Print chosen model's predictions at the very end (after all processing)
    if verbose:
        logger.info("\n%s", "=" * 70)
        logger.info("VÁLASZTOTT MODELL: %s", final_model_name.upper())
        logger.info("%s", "=" * 70)
        logger.info("Előrejelzés (pontbecslés) – index, érték:")
        if mean_forecast is not None and isinstance(mean_forecast, pd.Series):
            for idx, val in mean_forecast.items():
                idx_str = idx.strftime("%Y-%m") if hasattr(idx, "strftime") else str(idx)
                logger.info("  %s: %.2f", idx_str, float(val))
        logger.info("%s\n", "=" * 70)

    fc_series = pd.Series(mean_forecast.values, index=mean_forecast.index)
    fc_ci = ci

    metrics = {
        "wf_mse_arima": mse_arima,
        "wf_mse_ses": mse_ses,
        "wf_mse_holt": mse_holt,
        "wf_mse_ets": mse_ets,
        "wf_mse_autoreg": mse_autoreg,
        "wf_mse_behavioral": mse_behavioral,
        "wf_mse_baseline": baseline_mse,
        "wf_mse_prophet": mse_prophet,
        "wf_mae_arima": mae_arima,
        "wf_mae_ses": mae_ses,
        "wf_mae_holt": mae_holt,
        "wf_mae_ets": mae_ets,
        "wf_mae_autoreg": mae_autoreg,
        "wf_mae_behavioral": mae_behavioral,
        "wf_mae_baseline": baseline_mae,
        "wf_mae_prophet": mae_prophet,
        "wf_smape_arima": smape_arima,
        "wf_smape_ses": smape_ses,
        "wf_smape_holt": smape_holt,
        "wf_smape_ets": smape_ets,
        "wf_smape_autoreg": smape_autoreg,
        "wf_smape_behavioral": smape_behavioral,
        "wf_smape_baseline": baseline_smape,
        "wf_smape_prophet": smape_prophet,
        "wf_rw_mse_behavioral": rw_mse_behavioral,
        "wf_turning_score_behavioral": turning_behavioral,
        "wf_volatility_ratio_behavioral": vol_ratio_behavioral,
        "wf_spike_recall_behavioral": spike_recall_behavioral,
        "metric_choice": metric_choice,
        "baseline_selection_score": baseline_selection_score if np.isfinite(baseline_selection_score) else None,
        "selected_score": selected_score if np.isfinite(selected_score) else None,
        "selection_reason": selection_reason,
        "short_series_guard": bool(short_series_guard),
        "complex_models_skipped": bool(short_series_guard),
        "arima_order_used": list(arima_order),
        "seasonal_order_used": list(seasonal_order),
        "autoreg_lags_used": int(autoreg_lags),
        "sarimax_exog_used": bool(can_use_exog and (final_model_name == "arima" or "sarimax" in final_model_name)),
        "prophet_eligible": bool(prophet_eligible),
        "ets_eligible": bool(ets_eligible),
        "blend_component": None,
        "blend_baseline_weight": None,
        "seasonal_strength_lag12": seasonal_strength if np.isfinite(seasonal_strength) else None,
        "has_detected_seasonality": bool(has_detected_seasonality),
        "zero_ratio": zero_ratio,
        "series_skew": skew_val,
        "forecast_std": float(fc_series.std()) if len(fc_series) > 1 else 0.0,
        "forecast_cv": float(fc_series.std() / (abs(fc_series.mean()) + 1e-9)) if len(fc_series) > 1 else 0.0,
        "preview_horizon": int(preview_horizon) if preview_horizon >= PREVIEW_MIN_HORIZON else 0,
        "preview_selected_candidate": preview_selected_candidate,
        "preview_override_applied": bool(preview_override_applied),
        "preview_selection_scores": preview_scores_by_name,
        "backtest_window_size": n_test,
        "backtest_start": backtest_start.strftime("%Y-%m") if backtest_start is not None else None,
        "backtest_end": backtest_end.strftime("%Y-%m") if backtest_end is not None else None,
        "exog_forecast_method": _infer_exog_forecast_method(exog, exog_forecast),
        "chosen_model": final_model_name,
        "selected_model_before_fallback": chosen,
    }

    return fc_series, fc_ci, metrics
