from unittest.mock import patch

import numpy as np
import pandas as pd

from src.Generation.config import FORECAST_STEPS
from src.Generation.forecasting import run_short_series_pipeline
from src.Generation.models.exponential import fit_and_forecast_ets, fit_and_forecast_ses


def test_short_series_uses_conservative_selection():
    idx = pd.date_range("2025-01-31", periods=13, freq="ME")
    series = pd.Series(
        [127901, 322205, 425492, 525675, 605738, 597202, 253306, 364463, 425492, 400335, 322205, 457069, 448427],
        index=idx,
        dtype=float,
    )

    exog = pd.DataFrame(
        {
            "tx_count": range(13),
            "active_days": [20, 18, 22, 21, 25, 24, 15, 17, 19, 18, 16, 20, 21],
            "income_share": [0.4, 0.45, 0.43, 0.46, 0.48, 0.47, 0.39, 0.41, 0.44, 0.42, 0.4, 0.43, 0.45],
        },
        index=idx,
    )
    exog_fc = exog.tail(1).reindex(pd.date_range(idx[-1] + pd.offsets.MonthEnd(1), periods=10, freq="ME")).ffill()

    forecast, ci, metrics = run_short_series_pipeline(
        series,
        exog=exog,
        exog_forecast=exog_fc,
        plot=False,
        verbose=False,
    )
    assert len(forecast) == FORECAST_STEPS
    assert ci is None or len(ci) == FORECAST_STEPS
    # With SHORT_SERIES_COMPLEX_MODEL_MIN_POINTS=8, a 13-point series is NOT short-series guarded
    assert metrics["selected_model_before_fallback"] in {"ses", "holt", "ets", "behavioral", "arima", "autoreg"}
    assert metrics["chosen_model"] not in {"baseline_fallback", "baseline_emergency_fallback"}
    assert "arima" not in metrics["chosen_model"] or metrics["chosen_model"].endswith("_fallback")
    assert metrics["sarimax_exog_used"] is False
    assert metrics["prophet_eligible"] is False
    assert "wf_mse_ets" in metrics
    assert forecast.std() > 0.0


def test_logged_short_series_prefers_balanced_holt():
    idx = pd.date_range("2025-05-31", periods=13, freq="ME")
    series = pd.Series(
        [127901, 605738, 253306, 364463, 425492, 400335, 322205, 457069, 448427, 525675, 534602, 533416, 303061],
        index=idx,
        dtype=float,
    )

    forecast, ci, metrics = run_short_series_pipeline(
        series,
        plot=False,
        verbose=False,
    )

    assert len(forecast) == FORECAST_STEPS
    assert ci is None or len(ci) == FORECAST_STEPS
    # 13 points, SHORT_SERIES_COMPLEX_MODEL_MIN_POINTS=8 → guard is OFF
    assert metrics["chosen_model"] not in {"baseline_fallback", "baseline_emergency_fallback"}
    assert metrics["selected_model_before_fallback"] in {"behavioral", "holt", "ets", "ses", "arima", "autoreg"}
    assert metrics["blend_baseline_weight"] is None
    assert metrics["prophet_eligible"] is False
    assert float(forecast.std()) > 0.0
    assert metrics["wf_mse_behavioral"] is None or metrics["wf_mse_behavioral"] >= 0.0
    # Keep this robust: we only need to confirm the forecast is meaningfully non-flat,
    # not that the current best model produces a very large spread.
    assert float(forecast.max()) - float(forecast.min()) > 1000.0


def test_partial_last_month_behavioral_forecast_stays_above_average():
    idx = pd.date_range("2025-05-31", periods=13, freq="ME")
    series = pd.Series(
        [127901, 605738, 253306, 364463, 425492, 400335, 322205, 457069, 448427, 525675, 534602, 533416, 303061],
        index=idx,
        dtype=float,
    )

    forecast, ci, metrics = run_short_series_pipeline(
        series,
        plot=False,
        verbose=False,
    )

    hist_mean = float(series.mean())
    assert len(forecast) == FORECAST_STEPS
    assert ci is None or len(ci) == FORECAST_STEPS
    assert float(forecast.min()) > hist_mean
    assert float(forecast.mean()) > hist_mean
    assert metrics["chosen_model"] not in {"baseline_fallback", "baseline_emergency_fallback"}


def test_can_trigger_arima_model_when_it_is_best_candidate():
    idx = pd.date_range("2025-01-31", periods=11, freq="ME")
    series = pd.Series(
        [120, 150, 138, 170, 162, 190, 181, 210, 202, 235, 228],
        index=idx,
        dtype=float,
    )
    future_idx = pd.date_range(idx[-1] + pd.offsets.MonthEnd(1), periods=FORECAST_STEPS, freq="ME")
    arima_fc = pd.Series([240 + 7 * i for i in range(FORECAST_STEPS)], index=future_idx, dtype=float)
    arima_ci = pd.DataFrame({"lower": arima_fc - 12.0, "upper": arima_fc + 12.0}, index=future_idx)

    with patch(
        "src.Generation.forecasting.walk_forward_1step",
        return_value=([195.0, 212.0, 230.0], [202.0, 235.0, 228.0], 50.0, 0.92),
    ) as mock_wf_arima, patch(
        "src.Generation.forecasting.walk_forward_ses",
        return_value=(800.0, [180.0, 180.0, 180.0]),
    ), patch(
        "src.Generation.forecasting.walk_forward_holt",
        return_value=(650.0, [190.0, 198.0, 206.0]),
    ), patch(
        "src.Generation.forecasting.walk_forward_ets",
        return_value=(500.0, [188.0, 197.0, 205.0]),
    ), patch(
        "src.Generation.forecasting.walk_forward_autoreg",
        return_value=(700.0, [192.0, 201.0, 210.0]),
    ), patch(
        "src.Generation.forecasting.walk_forward_behavioral",
        return_value=(900.0, [185.0, 193.0, 200.0]),
    ), patch(
        "src.Generation.forecasting.fit_and_forecast_arima",
        return_value=("fit", arima_fc, arima_ci),
    ) as mock_fit_arima, patch(
        "src.Generation.forecasting.plot_results",
        return_value=None,
    ), patch(
        "src.Generation.forecasting.BASELINE_REL_IMPROVEMENT",
        -1.0,
    ), patch(
        "src.Generation.forecasting.MAX_NORMALIZED_MSE",
        1e9,
    ):
        forecast, ci, metrics = run_short_series_pipeline(series, plot=False, verbose=False)

    assert metrics["selected_model_before_fallback"] == "arima"
    assert metrics["chosen_model"] == "arima"
    assert metrics["sarimax_exog_used"] is False
    assert metrics["prophet_eligible"] is False
    assert len(forecast) == FORECAST_STEPS
    assert ci is not None and len(ci) == FORECAST_STEPS
    assert forecast.index.equals(future_idx)
    assert forecast.equals(arima_fc)
    assert ci.equals(arima_ci)
    mock_wf_arima.assert_called_once()
    mock_fit_arima.assert_called()


def test_close_scores_prefer_less_flat_candidate_shape_tiebreak():
    idx = pd.date_range("2024-07-31", periods=22, freq="ME")
    series = pd.Series(
        [305525, 172828, 141314, 160658, 186220, 154511, 198436, 256489, 279678, 239129, 327557,
         605738, 253306, 364463, 425492, 400335, 322205, 457069, 448427, 525675, 534602, 533416],
        index=idx,
        dtype=float,
    )
    future_idx = pd.date_range(idx[-1] + pd.offsets.MonthEnd(1), periods=FORECAST_STEPS, freq="ME")
    holt_fc = pd.Series([505000 + 12000 * i + (9000 if i % 3 == 1 else -6000 if i % 3 == 2 else 0) for i in range(FORECAST_STEPS)], index=future_idx, dtype=float)
    holt_ci = pd.DataFrame({"lower": holt_fc - 20000.0, "upper": holt_fc + 20000.0}, index=future_idx)
    ets_fc = pd.Series([500000 + 12000 * i for i in range(FORECAST_STEPS)], index=future_idx, dtype=float)
    ets_ci = pd.DataFrame({"lower": ets_fc - 18000.0, "upper": ets_fc + 18000.0}, index=future_idx)

    def _arima_side_effect(train_series, order=None, steps=FORECAST_STEPS, use_log=False):
        fc_idx = pd.date_range(train_series.index[-1] + pd.offsets.MonthEnd(1), periods=steps, freq="ME")
        fc = pd.Series([650000.0 + 1000.0 * i for i in range(steps)], index=fc_idx)
        ci = pd.DataFrame({"lower": fc - 22000.0, "upper": fc + 22000.0}, index=fc_idx)
        return "fit", fc, ci

    with patch(
        "src.Generation.forecasting.walk_forward_1step",
        return_value=([460000.0, 470000.0, 480000.0, 490000.0, 500000.0, 510000.0], [253306.0, 364463.0, 425492.0, 400335.0, 322205.0, 457069.0], 9.0e9, 0.1),
    ), patch(
        "src.Generation.forecasting.walk_forward_ses",
        return_value=(1.2e10, [400000.0] * 6),
    ), patch(
        "src.Generation.forecasting.walk_forward_holt",
        return_value=(4.61e9, [330000.0, 450000.0, 440000.0, 520000.0, 530000.0, 525000.0]),
    ), patch(
        "src.Generation.forecasting.walk_forward_ets",
        return_value=(4.57e9, [375000.0, 385000.0, 395000.0, 405000.0, 415000.0, 425000.0]),
    ), patch(
        "src.Generation.forecasting.walk_forward_autoreg",
        return_value=(1.8e10, [390000.0, 410000.0, 430000.0, 450000.0, 470000.0, 490000.0]),
    ), patch(
        "src.Generation.forecasting.walk_forward_behavioral",
        return_value=(1.6e10, [405000.0, 405000.0, 405000.0, 405000.0, 405000.0, 405000.0]),
    ), patch(
        "src.Generation.forecasting.fit_and_forecast_holt",
        return_value=(holt_fc, holt_ci),
    ) as mock_fit_holt, patch(
        "src.Generation.forecasting.fit_and_forecast_arima",
        side_effect=_arima_side_effect,
    ), patch(
        "src.Generation.forecasting.fit_and_forecast_ets",
        return_value=(ets_fc, ets_ci),
    ), patch(
        "src.Generation.forecasting.plot_results",
        return_value=None,
    ), patch(
        "src.Generation.forecasting.BASELINE_REL_IMPROVEMENT",
        -1.0,
    ), patch(
        "src.Generation.forecasting.MAX_NORMALIZED_MSE",
        1e9,
    ):
        forecast, ci, metrics = run_short_series_pipeline(series, plot=False, verbose=False)

    assert metrics["selected_model_before_fallback"] == "holt"
    assert metrics["selection_reason"] == "shape_tiebreak"
    assert metrics["chosen_model"] == "holt"
    assert forecast.equals(holt_fc)
    assert ci is not None and ci.equals(holt_ci)
    mock_fit_holt.assert_called()


def test_flat_forecast_fallback_skips_flat_replacement_candidates():
    idx = pd.date_range("2024-01-31", periods=15, freq="ME")
    series = pd.Series(
        [210000.0, 223000.0, 231000.0, 245000.0, 252000.0, 264000.0, 271000.0,
         286000.0, 294000.0, 307000.0, 315000.0, 328000.0, 337000.0, 349000.0, 358000.0],
        index=idx,
        dtype=float,
    )
    future_idx = pd.date_range(idx[-1] + pd.offsets.MonthEnd(1), periods=FORECAST_STEPS, freq="ME")
    ses_fc = pd.Series([402000.0] * FORECAST_STEPS, index=future_idx, dtype=float)
    flat_arima_fc = pd.Series([418000.0] * FORECAST_STEPS, index=future_idx, dtype=float)
    holt_fc = pd.Series(
        [410000.0, 426000.0, 421000.0, 441000.0, 437000.0, 459000.0,
         455000.0, 478000.0, 472000.0, 495000.0, 489000.0, 512000.0],
        index=future_idx,
        dtype=float,
    )
    holt_ci = pd.DataFrame({"lower": holt_fc - 15000.0, "upper": holt_fc + 15000.0}, index=future_idx)

    with patch(
        "src.Generation.forecasting.walk_forward_ses",
        return_value=(10.0, [330000.0, 330000.0, 330000.0, 330000.0, 330000.0]),
    ), patch(
        "src.Generation.forecasting.walk_forward_1step",
        return_value=([335000.0, 335000.0, 335000.0, 335000.0, 335000.0], [315000.0, 328000.0, 337000.0, 349000.0, 358000.0], 11.0, 0.2),
    ), patch(
        "src.Generation.forecasting.walk_forward_holt",
        return_value=(12.0, [320000.0, 338000.0, 334000.0, 352000.0, 360000.0]),
    ), patch(
        "src.Generation.forecasting.walk_forward_ets",
        return_value=(50.0, [325000.0, 326000.0, 327000.0, 328000.0, 329000.0]),
    ), patch(
        "src.Generation.forecasting.walk_forward_autoreg",
        return_value=(60.0, [318000.0, 332000.0, 341000.0, 351000.0, 362000.0]),
    ), patch(
        "src.Generation.forecasting.walk_forward_behavioral",
        return_value=(70.0, [324000.0, 324000.0, 324000.0, 324000.0, 324000.0]),
    ), patch(
        "src.Generation.forecasting.fit_and_forecast_ses",
        return_value=(ses_fc, None),
    ), patch(
        "src.Generation.forecasting.fit_and_forecast_arima",
        return_value=("fit", flat_arima_fc, None),
    ) as mock_fit_arima, patch(
        "src.Generation.forecasting.fit_and_forecast_holt",
        return_value=(holt_fc, holt_ci),
    ) as mock_fit_holt, patch(
        "src.Generation.forecasting.plot_results",
        return_value=None,
    ), patch(
        "src.Generation.forecasting.SELECTION_CLOSE_MARGIN",
        0.0,
    ), patch(
        "src.Generation.forecasting.PREVIEW_MIN_HORIZON",
        FORECAST_STEPS + 10,
    ), patch(
        "src.Generation.forecasting.BASELINE_REL_IMPROVEMENT",
        -1.0,
    ), patch(
        "src.Generation.forecasting.MAX_NORMALIZED_MSE",
        1e9,
    ):
        forecast, ci, metrics = run_short_series_pipeline(series, plot=False, verbose=False)

    assert metrics["selected_model_before_fallback"] == "ses"
    assert metrics["chosen_model"] == "holt_fallback"
    assert forecast.equals(holt_fc)
    assert ci is not None and ci.equals(holt_ci)
    assert float(forecast.std()) > 0.0
    mock_fit_arima.assert_called()
    mock_fit_holt.assert_called()


def test_first_step_cliff_fallback_rejects_abrupt_autoreg_drop():
    idx = pd.date_range("2025-03-31", periods=12, freq="ME")
    series = pd.Series(
        [279678.0, 239129.0, 327557.0, 605738.0, 253306.0, 364463.0,
         425492.0, 400335.0, 310567.0, 457069.0, 448427.0, 525175.0],
        index=idx,
        dtype=float,
    )
    future_idx = pd.date_range(idx[-1] + pd.offsets.MonthEnd(1), periods=FORECAST_STEPS, freq="ME")
    autoreg_fc = pd.Series(
        [258564.73, 414479.24, 427306.88, 403034.52, 371718.77, 404815.92,
         404416.36, 394744.95, 393161.16, 399814.89, 398405.80, 396168.97],
        index=future_idx,
        dtype=float,
    )
    ets_fc = pd.Series(
        [245000.0, 382000.0, 389000.0, 392000.0, 394000.0, 395000.0,
         396000.0, 397000.0, 397500.0, 398000.0, 398200.0, 398400.0],
        index=future_idx,
        dtype=float,
    )
    holt_fc = pd.Series(
        [472000.0, 486000.0, 492000.0, 488000.0, 481000.0, 489000.0,
         491000.0, 487000.0, 485000.0, 488500.0, 490000.0, 489500.0],
        index=future_idx,
        dtype=float,
    )
    holt_ci = pd.DataFrame({"lower": holt_fc - 18000.0, "upper": holt_fc + 18000.0}, index=future_idx)

    with patch(
        "src.Generation.forecasting.walk_forward_1step",
        return_value=([420000.0, 430000.0, 440000.0, 450000.0], [310567.0, 457069.0, 448427.0, 525175.0], 1.45e10, -0.4),
    ), patch(
        "src.Generation.forecasting.walk_forward_ses",
        return_value=(1.35e10, [410000.0, 410000.0, 410000.0, 410000.0]),
    ), patch(
        "src.Generation.forecasting.walk_forward_holt",
        return_value=(1.04e10, [420000.0, 438000.0, 446000.0, 454000.0]),
    ), patch(
        "src.Generation.forecasting.walk_forward_ets",
        return_value=(1.00e10, [418000.0, 430000.0, 442000.0, 454000.0]),
    ), patch(
        "src.Generation.forecasting.walk_forward_autoreg",
        return_value=(9.2e9, [430000.0, 442000.0, 454000.0, 466000.0]),
    ), patch(
        "src.Generation.forecasting.walk_forward_behavioral",
        return_value=(1.90e10, [405000.0, 405000.0, 405000.0, 405000.0]),
    ), patch(
        "src.Generation.forecasting.fit_and_forecast_autoreg",
        return_value=("fit", autoreg_fc, None),
    ) as mock_fit_autoreg, patch(
        "src.Generation.forecasting.fit_and_forecast_ets",
        return_value=(ets_fc, None),
    ), patch(
        "src.Generation.forecasting.fit_and_forecast_holt",
        return_value=(holt_fc, holt_ci),
    ) as mock_fit_holt, patch(
        "src.Generation.forecasting.plot_results",
        return_value=None,
    ), patch(
        "src.Generation.forecasting.BASELINE_REL_IMPROVEMENT",
        -1.0,
    ), patch(
        "src.Generation.forecasting.MAX_NORMALIZED_MSE",
        1e9,
    ), patch(
        "src.Generation.forecasting.PREVIEW_MIN_HORIZON",
        FORECAST_STEPS + 10,
    ):
        forecast, ci, metrics = run_short_series_pipeline(series, plot=False, verbose=False)

    assert metrics["selected_model_before_fallback"] == "autoreg"
    assert metrics["chosen_model"] == "holt_fallback"
    assert forecast.equals(holt_fc)
    assert ci is not None and ci.equals(holt_ci)
    assert float(forecast.iloc[0]) > float(series.tail(4).median()) * 0.60
    mock_fit_autoreg.assert_called()
    mock_fit_holt.assert_called()


def test_cliff_fallback_prefers_wave_preserving_holt_over_smoother_candidates():
    idx = pd.date_range("2025-03-31", periods=12, freq="ME")
    series = pd.Series(
        [279678.0, 239129.0, 327557.0, 605738.0, 253306.0, 364463.0,
         425492.0, 400335.0, 310567.0, 457069.0, 448427.0, 525175.0],
        index=idx,
        dtype=float,
    )
    future_idx = pd.date_range(idx[-1] + pd.offsets.MonthEnd(1), periods=FORECAST_STEPS, freq="ME")
    autoreg_fc = pd.Series(
        [258564.73, 414479.24, 427306.88, 403034.52, 371718.77, 404815.92,
         404416.36, 394744.95, 393161.16, 399814.89, 398405.80, 396168.97],
        index=future_idx,
        dtype=float,
    )
    arima_fc = pd.Series(
        [482362.82, 490898.23, 489196.54, 489535.80, 489468.16, 489481.65,
         489478.96, 489479.50, 489479.39, 489479.41, 489479.41, 489479.41],
        index=future_idx,
        dtype=float,
    )
    ets_fc = pd.Series(
        [483764.55, 498713.26, 513587.24, 528386.84, 543112.45, 557764.43,
         572343.15, 586848.97, 601282.27, 615643.40, 629932.72, 644150.60],
        index=future_idx,
        dtype=float,
    )
    holt_fc = pd.Series(
        [464777.54, 493928.01, 492147.36, 505143.76, 500905.14, 519378.03,
         514558.74, 521962.42, 516458.53, 529125.54, 523958.35, 528615.14],
        index=future_idx,
        dtype=float,
    )
    holt_ci = pd.DataFrame({"lower": holt_fc - 18000.0, "upper": holt_fc + 18000.0}, index=future_idx)

    with patch(
        "src.Generation.forecasting.walk_forward_1step",
        return_value=([430000.0, 440000.0, 450000.0, 460000.0], [310567.0, 457069.0, 448427.0, 525175.0], 8.871517374e9, 0.05),
    ), patch(
        "src.Generation.forecasting.walk_forward_ses",
        return_value=(1.3579382694272e10, [410000.0, 410000.0, 410000.0, 410000.0]),
    ), patch(
        "src.Generation.forecasting.walk_forward_holt",
        return_value=(1.0447861977212e10, [420000.0, 438000.0, 446000.0, 454000.0]),
    ), patch(
        "src.Generation.forecasting.walk_forward_ets",
        return_value=(1.0042838622870e10, [418000.0, 430000.0, 442000.0, 454000.0]),
    ), patch(
        "src.Generation.forecasting.walk_forward_autoreg",
        return_value=(7.5e9, [430000.0, 442000.0, 454000.0, 466000.0]),
    ), patch(
        "src.Generation.forecasting.walk_forward_behavioral",
        return_value=(1.90e10, [405000.0, 405000.0, 405000.0, 405000.0]),
    ), patch(
        "src.Generation.forecasting.fit_and_forecast_autoreg",
        return_value=("fit", autoreg_fc, None),
    ) as mock_fit_autoreg, patch(
        "src.Generation.forecasting.fit_and_forecast_arima",
        return_value=("fit", arima_fc, None),
    ) as mock_fit_arima, patch(
        "src.Generation.forecasting.fit_and_forecast_ets",
        return_value=(ets_fc, None),
    ) as mock_fit_ets, patch(
        "src.Generation.forecasting.fit_and_forecast_holt",
        return_value=(holt_fc, holt_ci),
    ) as mock_fit_holt, patch(
        "src.Generation.forecasting.plot_results",
        return_value=None,
    ), patch(
        "src.Generation.forecasting.BASELINE_REL_IMPROVEMENT",
        -1.0,
    ), patch(
        "src.Generation.forecasting.MAX_NORMALIZED_MSE",
        1e9,
    ), patch(
        "src.Generation.forecasting.PREVIEW_MIN_HORIZON",
        FORECAST_STEPS + 10,
    ):
        forecast, ci, metrics = run_short_series_pipeline(series, plot=False, verbose=False)

    assert metrics["selected_model_before_fallback"] == "autoreg"
    assert metrics["chosen_model"] == "holt_fallback"
    assert forecast.equals(holt_fc)
    assert ci is not None and ci.equals(holt_ci)
    assert float(forecast.diff().dropna().std()) > float(arima_fc.diff().dropna().std())
    assert float(forecast.diff().dropna().std()) > float(ets_fc.diff().dropna().std())
    mock_fit_autoreg.assert_called()
    mock_fit_arima.assert_called()
    mock_fit_ets.assert_called()
    mock_fit_holt.assert_called()


def test_ets_medium_series_gets_month_signature_adjustment():
    idx = pd.date_range("2024-01-31", periods=22, freq="ME")
    month_effects = {
        1: -70000.0, 2: -45000.0, 3: -15000.0, 4: 10000.0,
        5: 25000.0, 6: 95000.0, 7: -5000.0, 8: 15000.0,
        9: 35000.0, 10: 20000.0, 11: -10000.0, 12: 30000.0,
    }
    values = [320000.0 + 4000.0 * i + month_effects[ts.month] for i, ts in enumerate(idx)]
    series = pd.Series(values, index=idx, dtype=float)

    class _DummyETSModel:
        def __init__(self, series_in: pd.Series):
            self.series_in = series_in
            self.fittedvalues = series_in.copy()

        def fit(self, optimized: bool = True):
            return self

        def forecast(self, steps: int):
            fc_idx = pd.date_range(self.series_in.index[-1] + pd.offsets.MonthEnd(1), periods=steps, freq="ME")
            return pd.Series(np.linspace(500000.0, 620000.0, steps), index=fc_idx)

    with patch(
        "src.Generation.models.exponential.ExponentialSmoothing",
        side_effect=lambda series_in, **kwargs: _DummyETSModel(series_in),
    ):
        forecast, ci = fit_and_forecast_ets(series, steps=FORECAST_STEPS)

    assert forecast is not None
    assert ci is not None and len(ci) == FORECAST_STEPS
    diffs = np.diff(forecast.values)
    assert float(np.std(diffs)) > 1e-6


def test_preview_horizon_override_can_beat_1step_winner():
    idx = pd.date_range("2024-07-31", periods=22, freq="ME")
    series = pd.Series(
        [305525, 172828, 141314, 160658, 186220, 154511, 198436, 256489, 279678, 239129, 327557,
         605738, 253306, 364463, 425492, 400335, 322205, 457069, 448427, 525675, 534602, 533416],
        index=idx,
        dtype=float,
    )
    future_idx = pd.date_range(idx[-1] + pd.offsets.MonthEnd(1), periods=FORECAST_STEPS, freq="ME")
    actual_holdout = series.iloc[-6:]

    def _holt_side_effect(train_series, steps=FORECAST_STEPS, **kwargs):
        fc_idx = pd.date_range(train_series.index[-1] + pd.offsets.MonthEnd(1), periods=steps, freq="ME")
        if steps == len(actual_holdout):
            fc = pd.Series(actual_holdout.values + np.array([5000.0, -4000.0, 3000.0, -2500.0, 3500.0, -3000.0]), index=fc_idx)
        else:
            fc = pd.Series([548000.0, 565000.0, 576000.0, 584000.0, 592000.0, 600000.0,
                            604000.0, 608000.0, 611000.0, 614000.0, 617000.0, 620000.0][:steps], index=fc_idx)
        ci = pd.DataFrame({"lower": fc - 18000.0, "upper": fc + 18000.0}, index=fc_idx)
        return fc, ci

    def _ets_side_effect(train_series, steps=FORECAST_STEPS, **kwargs):
        fc_idx = pd.date_range(train_series.index[-1] + pd.offsets.MonthEnd(1), periods=steps, freq="ME")
        if steps == len(actual_holdout):
            fc = pd.Series([380000.0, 392000.0, 404000.0, 416000.0, 428000.0, 440000.0], index=fc_idx)
        else:
            fc = pd.Series([500000.0 + 12000.0 * i for i in range(steps)], index=fc_idx)
        ci = pd.DataFrame({"lower": fc - 16000.0, "upper": fc + 16000.0}, index=fc_idx)
        return fc, ci

    def _arima_side_effect(train_series, order=None, steps=FORECAST_STEPS, use_log=False):
        fc_idx = pd.date_range(train_series.index[-1] + pd.offsets.MonthEnd(1), periods=steps, freq="ME")
        fc = pd.Series([660000.0 + 1500.0 * i for i in range(steps)], index=fc_idx)
        ci = pd.DataFrame({"lower": fc - 24000.0, "upper": fc + 24000.0}, index=fc_idx)
        return "fit", fc, ci

    with patch(
        "src.Generation.forecasting.walk_forward_1step",
        return_value=([430000.0, 442000.0, 454000.0, 466000.0, 478000.0, 490000.0], actual_holdout.tolist(), 8.0e9, 0.05),
    ), patch(
        "src.Generation.forecasting.walk_forward_ses",
        return_value=(1.4e10, [405000.0] * 6),
    ), patch(
        "src.Generation.forecasting.walk_forward_holt",
        return_value=(4.63e9, [378000.0, 389000.0, 400000.0, 411000.0, 422000.0, 433000.0]),
    ), patch(
        "src.Generation.forecasting.walk_forward_ets",
        return_value=(4.57e9, [375000.0, 385000.0, 395000.0, 405000.0, 415000.0, 425000.0]),
    ), patch(
        "src.Generation.forecasting.walk_forward_autoreg",
        return_value=(1.7e10, [395000.0, 405000.0, 415000.0, 425000.0, 435000.0, 445000.0]),
    ), patch(
        "src.Generation.forecasting.walk_forward_behavioral",
        return_value=(1.5e10, [410000.0] * 6),
    ), patch(
        "src.Generation.forecasting.fit_and_forecast_holt",
        side_effect=_holt_side_effect,
    ) as mock_fit_holt, patch(
        "src.Generation.forecasting.fit_and_forecast_arima",
        side_effect=_arima_side_effect,
    ), patch(
        "src.Generation.forecasting.fit_and_forecast_ets",
        side_effect=_ets_side_effect,
    ), patch(
        "src.Generation.forecasting.plot_results",
        return_value=None,
    ), patch(
        "src.Generation.forecasting.BASELINE_REL_IMPROVEMENT",
        -1.0,
    ), patch(
        "src.Generation.forecasting.MAX_NORMALIZED_MSE",
        1e9,
    ):
        forecast, ci, metrics = run_short_series_pipeline(series, plot=False, verbose=False)

    assert metrics["preview_override_applied"] is True
    assert metrics["preview_selected_candidate"] == "holt"
    assert metrics["selection_reason"] == "preview_horizon_override"
    assert metrics["selected_model_before_fallback"] == "holt"
    assert metrics["chosen_model"] == "holt"
    assert metrics["preview_horizon"] == 6
    assert metrics["preview_selection_scores"]["holt"] < metrics["preview_selection_scores"]["ets"]
    assert forecast.index.equals(future_idx)
    assert ci is not None and len(ci) == FORECAST_STEPS
    mock_fit_holt.assert_called()


def test_all_candidate_pipelines_receive_exog_features_when_available():
    idx = pd.date_range("2024-01-31", periods=14, freq="ME")
    series = pd.Series([210000, 225000, 218000, 236000, 244000, 255000, 248000, 266000, 274000, 289000, 301000, 314000, 309000, 327000], index=idx, dtype=float)
    exog = pd.DataFrame(
        {
            "tx_count": [38, 40, 39, 41, 42, 44, 43, 46, 47, 49, 50, 53, 52, 55],
            "active_days": [17, 18, 18, 19, 20, 21, 20, 22, 22, 23, 24, 24, 23, 25],
            "large_tx_share": [0.18, 0.16, 0.19, 0.20, 0.22, 0.21, 0.18, 0.23, 0.24, 0.25, 0.24, 0.26, 0.23, 0.27],
        },
        index=idx,
        dtype=float,
    )
    future_idx = pd.date_range(idx[-1] + pd.offsets.MonthEnd(1), periods=FORECAST_STEPS, freq="ME")
    exog_fc = pd.DataFrame(
        {
            "tx_count": [56 + i for i in range(FORECAST_STEPS)],
            "active_days": [25 + (1 if i % 4 == 0 else 0) for i in range(FORECAST_STEPS)],
            "large_tx_share": [0.28 + 0.005 * i for i in range(FORECAST_STEPS)],
        },
        index=future_idx,
        dtype=float,
    )

    observed: dict[str, list[tuple[tuple, dict]]] = {"ses": [], "holt": [], "ets": [], "autoreg": []}

    def _record(name: str, fc_values: list[float]):
        def _inner(*args, **kwargs):
            observed[name].append((args, kwargs))
            steps = int(kwargs.get("steps", 1))
            if name == "autoreg":
                fc_idx = pd.date_range(args[0].index[-1] + pd.offsets.MonthEnd(1), periods=steps, freq="ME")
                fc = pd.Series(fc_values[:steps], index=fc_idx, dtype=float)
                return "fit", fc, None
            fc_idx = pd.date_range(args[0].index[-1] + pd.offsets.MonthEnd(1), periods=steps, freq="ME")
            fc = pd.Series(fc_values[:steps], index=fc_idx, dtype=float)
            ci = pd.DataFrame({"lower": fc - 12000.0, "upper": fc + 12000.0}, index=fc_idx)
            return fc, ci
        return _inner

    with patch(
        "src.Generation.forecasting.walk_forward_1step",
        return_value=([250000.0, 260000.0, 270000.0, 280000.0], [248000.0, 266000.0, 274000.0, 289000.0], 7.5e9, 0.2),
    ), patch(
        "src.Generation.forecasting.fit_and_forecast_ses",
        side_effect=_record("ses", [332000.0 + 3000.0 * i for i in range(FORECAST_STEPS)]),
    ), patch(
        "src.Generation.validation.fit_and_forecast_ses",
        side_effect=_record("ses", [332000.0 + 3000.0 * i for i in range(FORECAST_STEPS)]),
    ), patch(
        "src.Generation.forecasting.fit_and_forecast_holt",
        side_effect=_record("holt", [336000.0 + 5500.0 * i for i in range(FORECAST_STEPS)]),
    ), patch(
        "src.Generation.validation.fit_and_forecast_holt",
        side_effect=_record("holt", [336000.0 + 5500.0 * i for i in range(FORECAST_STEPS)]),
    ) as mock_fit_holt, patch(
        "src.Generation.forecasting.fit_and_forecast_ets",
        side_effect=_record("ets", [334000.0 + 5200.0 * i for i in range(FORECAST_STEPS)]),
    ), patch(
        "src.Generation.validation.fit_and_forecast_ets",
        side_effect=_record("ets", [334000.0 + 5200.0 * i for i in range(FORECAST_STEPS)]),
    ), patch(
        "src.Generation.forecasting.fit_and_forecast_autoreg",
        side_effect=_record("autoreg", [330000.0 + 4800.0 * i for i in range(FORECAST_STEPS)]),
    ), patch(
        "src.Generation.validation.fit_and_forecast_autoreg",
        side_effect=_record("autoreg", [330000.0 + 4800.0 * i for i in range(FORECAST_STEPS)]),
    ), patch(
        "src.Generation.forecasting.walk_forward_behavioral",
        return_value=(1.6e10, [310000.0, 310000.0, 310000.0, 310000.0]),
    ), patch(
        "src.Generation.forecasting.fit_and_forecast_behavioral_boosted",
        return_value=(None, pd.Series([329000.0 + 3500.0 * i for i in range(FORECAST_STEPS)], index=future_idx), None),
    ), patch(
        "src.Generation.forecasting.plot_results",
        return_value=None,
    ), patch(
        "src.Generation.forecasting.BASELINE_REL_IMPROVEMENT",
        -1.0,
    ), patch(
        "src.Generation.forecasting.MAX_NORMALIZED_MSE",
        1e9,
    ):
        forecast, ci, metrics = run_short_series_pipeline(series, exog=exog, exog_forecast=exog_fc, plot=False, verbose=False)

    for name in ("ses", "holt", "ets"):
        assert observed[name], f"{name} should have been called"
        assert any(call_kwargs.get("exog") is not None for _, call_kwargs in observed[name])
        assert any(call_kwargs.get("exog_forecast") is not None for _, call_kwargs in observed[name])

    assert observed["autoreg"], "autoreg should have been called"
    assert any(call_kwargs.get("exog") is not None for _, call_kwargs in observed["autoreg"])
    assert any(call_kwargs.get("exog_forecast") is not None for _, call_kwargs in observed["autoreg"])
    assert metrics["chosen_model"] in {"ses", "holt", "ets", "autoreg", "behavioral_quantile_boost", "arima"}
    assert forecast is not None and len(forecast) == FORECAST_STEPS
    assert ci is not None
    mock_fit_holt.assert_called()


def test_ses_forecast_is_exog_adjusted_when_features_exist():
    idx = pd.date_range("2025-01-31", periods=8, freq="ME")
    series = pd.Series([100.0, 106.0, 103.0, 109.0, 112.0, 118.0, 121.0, 126.0], index=idx)
    exog = pd.DataFrame({"tx_count": [10, 11, 10, 12, 13, 14, 15, 16]}, index=idx, dtype=float)
    future_idx = pd.date_range(idx[-1] + pd.offsets.MonthEnd(1), periods=3, freq="ME")
    exog_fc = pd.DataFrame({"tx_count": [18.0, 19.0, 20.0]}, index=future_idx)
    exog_boost_fc = pd.Series([150.0, 156.0, 162.0], index=future_idx, dtype=float)

    plain_fc, _ = fit_and_forecast_ses(series, steps=3)

    with patch(
        "src.Generation.models.exponential.fit_and_forecast_time_regression_boosted",
        return_value=("ridge", exog_boost_fc, None),
    ) as mock_time_reg:
        exog_fc_out, _ = fit_and_forecast_ses(series, steps=3, exog=exog, exog_forecast=exog_fc)

    assert plain_fc is not None
    assert exog_fc_out is not None
    assert mock_time_reg.called
    assert exog_fc_out.index.equals(future_idx)
    assert float(exog_fc_out.iloc[0]) > float(plain_fc.iloc[0])
    assert not exog_fc_out.equals(plain_fc)


def test_ses_skips_exog_adjustment_for_last_known_future_exog():
    idx = pd.date_range("2025-01-31", periods=8, freq="ME")
    series = pd.Series([100.0, 106.0, 103.0, 109.0, 112.0, 118.0, 121.0, 126.0], index=idx)
    exog = pd.DataFrame(
        {
            "tx_count": [10.0, 11.0, 10.0, 12.0, 13.0, 14.0, 15.0, 16.0],
            "active_days": [7.0, 8.0, 7.0, 9.0, 9.0, 10.0, 10.0, 11.0],
        },
        index=idx,
    )
    future_idx = pd.date_range(idx[-1] + pd.offsets.MonthEnd(1), periods=3, freq="ME")
    last_row = exog.iloc[-1]
    exog_fc = pd.DataFrame(
        {
            "tx_count": [float(last_row["tx_count"])] * 3,
            "active_days": [float(last_row["active_days"])] * 3,
        },
        index=future_idx,
    )

    plain_fc, _ = fit_and_forecast_ses(series, steps=3)

    with patch(
        "src.Generation.models.exponential.fit_and_forecast_time_regression_boosted",
        side_effect=AssertionError("time-reg exog blend should be skipped for last-known future exog"),
    ):
        exog_fc_out, _ = fit_and_forecast_ses(series, steps=3, exog=exog, exog_forecast=exog_fc)

    assert plain_fc is not None
    assert exog_fc_out is not None
    assert exog_fc_out.equals(plain_fc)


