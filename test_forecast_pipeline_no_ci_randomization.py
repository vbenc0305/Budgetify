from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from src.Generation import Case_one_has_enough_Transact_arima_refactored as pipeline_mod


def test_forecast_pipeline_keeps_model_point_forecast_without_ci_randomization(tmp_path):
    history_idx = pd.date_range("2025-01-31", periods=6, freq="ME")
    monthly_series = pd.Series([120.0, 135.0, 128.0, 142.0, 150.0, 147.0], index=history_idx)

    forecast_idx = pd.date_range(history_idx[-1] + pd.offsets.MonthEnd(1), periods=3, freq="ME")
    fc_series = pd.Series([160.0, 172.5, 181.25], index=forecast_idx)
    fc_ci = pd.DataFrame(
        {
            "lower": [150.0, 161.0, 170.0],
            "upper": [170.0, 184.0, 193.0],
        },
        index=forecast_idx,
    )
    metrics = {"chosen_model": "arima"}

    pipeline = pipeline_mod.ForecastPipeline(out_path=Path(tmp_path) / "forecast.csv")

    with patch(
        "src.Generation.Case_one_has_enough_Transact_arima_refactored.prepare_transaction_data",
        return_value=(monthly_series, None, None, "test_source"),
    ) as mock_prepare, patch(
        "src.Generation.Case_one_has_enough_Transact_arima_refactored.run_short_series_pipeline",
        return_value=(fc_series, fc_ci, metrics),
    ) as mock_run, patch(
        "src.Generation.Case_one_has_enough_Transact_arima_refactored.np.random.uniform",
        side_effect=AssertionError("CI randomization should not run anymore"),
    ):
        result = pipeline.run(uid="u1", plot=False, verbose=False)

    assert result["status"] == "success"
    assert result["data_source"] == "test_source"
    assert result["metrics"] == metrics
    assert result["forecast"] == [
        {"date": "2025-07", "value": 160.0},
        {"date": "2025-08", "value": 172.5},
        {"date": "2025-09", "value": 181.25},
    ]
    assert result["ci"] == [
        {"date": "2025-07", "lower": 150.0, "upper": 170.0},
        {"date": "2025-08", "lower": 161.0, "upper": 184.0},
        {"date": "2025-09", "lower": 170.0, "upper": 193.0},
    ]
    assert np.array_equal(result["raw_arrays"]["history_arr"], monthly_series.values.astype(float))
    assert np.array_equal(result["raw_arrays"]["forecast_arr"], fc_series.values.astype(float))
    mock_prepare.assert_called_once_with(uid="u1", tx_list=None)
    mock_run.assert_called_once_with(monthly_series, exog=None, exog_forecast=None, plot=False, verbose=False)

