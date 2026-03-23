#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main forecasting pipeline wrapper and entry point.

This is a thin wrapper around the refactored forecasting components.
It provides backward compatibility and a clean interface for external code.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional, List, Dict, Any

from src.Generation.config import UID_BASE, OUT_PATH, FORECAST_STEPS
from src.Generation.data_preparation import prepare_transaction_data
from src.Generation.forecasting import run_short_series_pipeline


class ForecastPipeline:
    """
    Main forecasting pipeline wrapper.

    Pipeline flow:
      1. Load transactions (from DB or provided list)
      2. Feature engineering
      3. Build monthly aggregates (panel)
      4. Prepare exogenous variables
      5. Model selection and forecasting
      6. Return structured results

    Returns a dictionary with:
        - status: "success" | "no_data"
        - data_source: "from_db" | "demo" | "no_data"
        - history: list of {"date": "YYYY-MM", "value": float}
        - forecast: list of {"date": "YYYY-MM", "value": float}
        - ci: list of {"date": "YYYY-MM", "lower": float, "upper": float} or None
        - metrics: dict of walk-forward validation metrics
        - raw_arrays: {"history_arr": np.array, "forecast_arr": np.array}
    """

    def __init__(self, uid_default: str = UID_BASE, out_path: Path = OUT_PATH):
        """
        Initialize the forecast pipeline.

        Args:
            uid_default: Default user ID to use if none provided
            out_path: Path where to save CSV output
        """
        self.uid_default = uid_default
        self.out_path = out_path

    def _series_to_date_value_list(self, series: Optional[pd.Series]) -> List[Dict[str, Any]]:
        """Convert pandas Series to list of {"date": YYYY-MM, "value": float} dicts."""
        if series is None or len(series) == 0:
            return []

        out = []
        for ts, v in series.items():
            try:
                date_str = pd.to_datetime(ts).strftime("%Y-%m")
            except Exception:
                date_str = str(ts)

            val = float(v)
            if not np.isfinite(val):
                val = 0.0
            out.append({"date": date_str, "value": val})
        return out

    def _ci_to_list(self, ci_df: Optional[pd.DataFrame]) -> Optional[List[Dict[str, Any]]]:
        """Convert confidence interval DataFrame to list of dicts."""
        if ci_df is None or len(ci_df) == 0:
            return None

        out = []
        for idx, row in ci_df.iterrows():
            try:
                date_str = pd.to_datetime(idx).strftime("%Y-%m")
            except Exception:
                date_str = str(idx)

            # Extract lower and upper bounds
            try:
                lower = float(row.iloc[0])
                upper = float(row.iloc[1])
            except Exception:
                lower = float(row.get("lower", np.nan))
                upper = float(row.get("upper", np.nan))

            out.append({"date": date_str, "lower": lower, "upper": upper})
        return out

    def run(
        self,
        uid: Optional[str] = None,
        tx_list: Optional[List[Dict[str, Any]]] = None,
        plot: bool = False,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Run the complete forecasting pipeline.

        Args:
            uid: User ID (uses default if not provided)
            tx_list: Optional pre-loaded transaction list
            plot: Whether to generate plots
            verbose: Whether to print detailed logs

        Returns:
            Dictionary with forecasting results (see class docstring)
        """
        uid_local = uid if uid is not None else self.uid_default

        # Step 1: Prepare data
        monthly_series, exog, exog_forecast, used_status = prepare_transaction_data(
            uid=uid_local, tx_list=tx_list)

        # Step 2: Run forecasting pipeline
        if monthly_series is None or len(monthly_series) == 0:
            print("⚠️ Nincs elegendő adat az előrejelzéshez.")
            return {
                "status": "no_data",
                "data_source": "no_data",
                "history": [],
                "forecast": [],
                "ci": None,
                "metrics": {},
                "raw_arrays": {"history_arr": None, "forecast_arr": None},
            }

        print("\n▶️ Lefuttatom a rövid-sorozat pipeline-t...")
        fc_series, fc_ci, metrics = run_short_series_pipeline(
            monthly_series, exog=exog, exog_forecast=exog_forecast,
            plot=plot, verbose=verbose)

        # Step 3: Prepare output
        history_list = self._series_to_date_value_list(monthly_series)
        forecast_list = self._series_to_date_value_list(fc_series)
        ci_list = self._ci_to_list(fc_ci)

        history_arr = monthly_series.values.astype(float) if monthly_series is not None else None
        forecast_arr = fc_series.values.astype(float) if fc_series is not None else None

        # Step 4: Save CSV (optional)
        try:
            ci_out = None
            if fc_ci is not None:
                ci_df = fc_ci.copy()
                lower = ci_df.iloc[:, 0].values
                upper = ci_df.iloc[:, 1].values
                ci_out = pd.DataFrame({"lower": lower, "upper": upper}, index=fc_series.index)

            df_out = pd.DataFrame({
                "forecast": fc_series,
                "ci_lower": ci_out["lower"] if ci_out is not None else np.nan,
                "ci_upper": ci_out["upper"] if ci_out is not None else np.nan,
            })
            df_out.to_csv(self.out_path, index_label="date")
            print(f"\n💾 Elmentve: {self.out_path.resolve()}")
        except Exception as e:
            print(f"⚠️ Nem sikerült elmenteni a forecast-ot: {e}")

        # Step 5: Return results
        result = {
            "status": "success",
            "data_source": used_status,
            "history": history_list,
            "forecast": forecast_list,
            "ci": ci_list,
            "metrics": metrics or {},
            "raw_arrays": {
                "history_arr": history_arr,
                "forecast_arr": forecast_arr
            },
        }
        return result


def run_sarima_pipeline(uid: Optional[str] = None) -> tuple:
    """
    Backward-compatible wrapper that returns (history_arr, forecast_arr).

    Args:
        uid: User ID (uses default if not provided)

    Returns:
        Tuple of (history_array, forecast_array)
    """
    pipeline = ForecastPipeline()
    result = pipeline.run(uid=uid)
    raw = result.get("raw_arrays", {})
    history_arr = raw.get("history_arr")
    forecast_arr = raw.get("forecast_arr")
    return history_arr, forecast_arr


if __name__ == "__main__":
    # Example: run as script
    hist, fut = run_sarima_pipeline()
    print("\nPélda output shape-ek:")
    print(" - history shape:", getattr(hist, "shape", None))
    print(" - forecast shape:", getattr(fut, "shape", None))
    if hist is not None and fut is not None:
        print("History values:", hist[:5])
        print("Forecast values:", fut[:5])

