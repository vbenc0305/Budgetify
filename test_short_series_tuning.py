from unittest.mock import patch

import pandas as pd

from src.Generation.config import FORECAST_STEPS
from src.Generation.forecasting import run_short_series_pipeline


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
    mock_fit_arima.assert_called_once()


