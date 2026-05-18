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
    assert metrics["selected_model_before_fallback"] in {"ses", "holt", "behavioral", "arima", "autoreg"}
    assert metrics["chosen_model"] not in {"baseline_fallback", "baseline_emergency_fallback"}
    assert "arima" not in metrics["chosen_model"] or metrics["chosen_model"].endswith("_fallback")
    assert metrics["sarimax_exog_used"] is False
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
    assert metrics["selected_model_before_fallback"] in {"behavioral", "holt", "ses", "arima", "autoreg"}
    assert metrics["blend_baseline_weight"] is None
    assert float(forecast.std()) > 0.0
    assert metrics["wf_mse_behavioral"] is None or metrics["wf_mse_behavioral"] >= 0.0
    assert float(forecast.max()) - float(forecast.min()) > 50000.0

