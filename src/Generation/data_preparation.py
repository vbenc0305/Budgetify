#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data loading and preparation for forecasting pipeline.
"""

import logging
import re
from typing import Any, Dict, List, Optional, cast

import pandas as pd

from src.Generation.data_loader import get_all_transactions
from src.Generation.Feature_engineering import engineer_all_features, build_monthly_panel_from_tx, \
    make_monthly_exog_no_leakage, make_exog_forecast_from_last_known

from src.Generation.config import TARGET, FORECAST_STEPS


logger = logging.getLogger(__name__)


def _log_amount_stats(df: pd.DataFrame, label: str) -> None:
    if df is None or df.empty:
        logger.info("%s: empty", label)
        return
    if 'amount' not in df.columns:
        logger.info("%s: no amount column", label)
        return
    amounts = pd.to_numeric(df['amount'], errors='coerce')
    total = amounts.sum(skipna=True)
    logger.info("%s: count=%s amount_sum=%.2f", label, len(df), total)


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ö": "o",
        "ő": "o",
        "ú": "u",
        "ü": "u",
        "ű": "u",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return re.sub(r"\s+", "", text)


def _has_internal_transfer_hint(*values: Any) -> bool:
    joined = _normalize_text(" ".join(str(v or "") for v in values))
    if not joined:
        return False
    return any(keyword in joined for keyword in ("persely", "kerek", "felkerek", "rounding"))


def prepare_transaction_data(
    uid: str,
    tx_list: Optional[List[Dict[str, Any]]] = None,
    export_filtered_csv_path: Optional[str] = None,
    export_monthly_csv_path: Optional[str] = None,
    sum_from_filtered_csv: bool = False
) -> tuple:
    """
    Load and prepare transaction data for forecasting.

    If tx_list is provided, use that; otherwise load from database.

    Args:
        uid: User ID
        tx_list: Optional pre-loaded transaction list

    Returns:
        Tuple of (monthly_series, exog, exog_forecast, used_status)
    """
    monthly_series = None
    exog = None
    exog_forecast = None
    used_status = "no_data"

    # 1) Load transactions
    if tx_list is None:
        try:
            tx_list = get_all_transactions(uid)
        except Exception as e:
            logger.error("Hiba a tranzakciók lekérésekor: %s", e)
            tx_list = []

    # Ensure we always have a list
    tx_list = tx_list or []

    # 2) Process transactions if available
    if len(tx_list) > 0:
        df_tx = pd.DataFrame(tx_list)
        logger.info("prepare_transaction_data: loaded %s transactions", len(df_tx))
        _log_amount_stats(df_tx, "loaded")


        # Ensure required columns exist and fill nulls
        if 'user_id' not in df_tx.columns:
            df_tx['user_id'] = uid
            logger.info("user_id missing; filled from uid")
        df_tx['user_id'] = df_tx['user_id'].fillna(uid)

        if 'description' in df_tx.columns:
            df_tx['description'] = df_tx['description'].fillna('')

        if 'direction' in df_tx.columns:
            df_tx['direction'] = df_tx['direction'].fillna('')
        if 'transaction_direction' in df_tx.columns:
            df_tx['transaction_direction'] = df_tx['transaction_direction'].fillna('')
        if 'for_who' in df_tx.columns:
            df_tx['for_who'] = df_tx['for_who'].fillna('')

        if 'date' not in df_tx.columns:
            df_tx['date'] = pd.NaT
            logger.info("date missing; filled with NaT")
        df_tx['date'] = pd.to_datetime(df_tx['date'], errors='coerce')
        before_dates = len(df_tx)
        df_tx = df_tx[df_tx['date'].notna()].copy()
        if len(df_tx) != before_dates:
            logger.info("date filter (valid only): %s -> %s", before_dates, len(df_tx))
        if df_tx.empty:
            logger.info("prepare_transaction_data: no valid dates after date filter")
            return monthly_series, exog, exog_forecast, used_status

        # Remove duplicates based on exact date match (yyyy-mm-dd hh:mm:ss)
        before_dupes = len(df_tx)
        df_tx = df_tx.drop_duplicates(subset=['date'], keep='first').copy()
        if len(df_tx) != before_dupes:
            logger.info(
                "date dedupe: %s -> %s (removed %s duplicates)",
                before_dupes,
                len(df_tx),
                before_dupes - len(df_tx),
            )
        _log_amount_stats(df_tx, "after deduplication")

        if 'amount' not in df_tx.columns:
            df_tx['amount'] = 0.0
            logger.info("amount missing; filled with 0.0")
        df_tx['amount'] = pd.to_numeric(df_tx['amount'], errors='coerce').fillna(0.0)

        if 'category' not in df_tx.columns:
            df_tx['category'] = 'unknown'
            logger.info("category missing; filled with 'unknown'")
        df_tx['category'] = df_tx['category'].fillna('unknown')

        if 'tran_type' not in df_tx.columns:
            df_tx['tran_type'] = ''
            logger.info("tran_type missing; filled with empty string")
        df_tx['tran_type'] = df_tx['tran_type'].fillna('')

        if 'internal_transfer' not in df_tx.columns:
            df_tx['internal_transfer'] = 'none'
        df_tx['internal_transfer'] = (
            df_tx['internal_transfer']
            .fillna('none')
            .astype(str)
            .str.strip()
            .str.lower()
            .replace({'': 'none', 'nan': 'none', 'null': 'none', 'none': 'none'})
        )

        valid_internal_transfer_values = {'none', 'jar_in', 'jar_out', 'rounding'}
        invalid_internal = ~df_tx['internal_transfer'].isin(valid_internal_transfer_values)
        if invalid_internal.any():
            df_tx.loc[invalid_internal, 'internal_transfer'] = 'none'
            logger.info(
                "internal_transfer normalize: reset %s invalid values to 'none'",
                int(invalid_internal.sum()),
            )

        hint_mask = df_tx.apply(
            lambda row: _has_internal_transfer_hint(
                row.get('description', ''),
                row.get('tran_type', ''),
                row.get('for_who', ''),
            ),
            axis=1,
        )
        stale_internal_mask = (
            df_tx['internal_transfer'].isin({'jar_in', 'jar_out', 'rounding'})
            & ~hint_mask
        )
        if stale_internal_mask.any():
            df_tx.loc[stale_internal_mask, 'internal_transfer'] = 'none'
            logger.info(
                "internal_transfer repair: reset %s stale labels to 'none'",
                int(stale_internal_mask.sum()),
            )

        # Apply feature engineering
        try:
            df_tx = engineer_all_features(df_tx)
        except Exception as e:
            logger.warning("engineer_all_features hibát dobott: %s (folytatom a nyers df-fel)", e)
        _log_amount_stats(df_tx, "after feature engineering")

        # Normalize and filter transaction direction
        if 'transaction_direction' in df_tx.columns:
            df_tx['direction_norm'] = df_tx['transaction_direction'].apply(_normalize_text)
        elif 'direction' in df_tx.columns:
            df_tx['direction_norm'] = df_tx['direction'].apply(_normalize_text)
        else:
            df_tx['direction_norm'] = ''

        outgoing_mask = df_tx['direction_norm'].str.contains('kimen', na=False)
        before_direction = len(df_tx)
        df_tx = df_tx[outgoing_mask].copy()
        logger.info("direction filter (Kimenő): %s -> %s", before_direction, len(df_tx))
        _log_amount_stats(df_tx, "after direction filter")

        # Filter internal transfers
        if 'internal_transfer' in df_tx.columns:
            before_internal = len(df_tx)
            df_tx = df_tx[df_tx['internal_transfer'].fillna('none') == 'none'].copy()
            logger.info("internal_transfer filter: %s -> %s", before_internal, len(df_tx))
        _log_amount_stats(df_tx, "after internal_transfer filter")

        if export_filtered_csv_path:
            df_tx.to_csv(export_filtered_csv_path, index=False)
            logger.info("filtered CSV exported: %s", export_filtered_csv_path)

        if TARGET not in df_tx.columns:
            logger.error("Figyelem: a pipeline elvárja a '%s' oszlopot az engineer_all_features kimenetében.", TARGET)
            return monthly_series, exog, exog_forecast, used_status

        # Build monthly panel
        try:
            panel = build_monthly_panel_from_tx(df_tx, uid_local=uid, date_col="date",
                                               uid_col='user_id', amount_col=TARGET)
            if panel is None:
                panel = pd.DataFrame()
        except Exception as e:
            logger.warning("build_monthly_panel_from_tx hibát dobott: %s", e)
            panel = pd.DataFrame()

        # Filter for current user
        if not panel.empty and 'user_id' in panel.columns:
            try:
                panel_uid = panel[panel['user_id'] == uid].copy()
            except Exception:
                panel_uid = panel.copy()
        else:
            panel_uid = panel.copy()

        # Create monthly series
        if panel_uid is None or panel_uid.empty:
            monthly_series = None
        else:
            panel_uid['date'] = pd.to_datetime(panel_uid['date'])
            panel_uid = panel_uid.sort_values('date').reset_index(drop=True)

            # Determine value column name
            value_col = 'y_sum' if 'y_sum' in panel_uid.columns else (
                TARGET if TARGET in panel_uid.columns else None)

            if value_col is None:
                logger.error("Nem található aggregált érték ('y_sum' / TARGET) a panel-ben.")
            else:
                try:
                    monthly_series = pd.Series(panel_uid[value_col].values,
                                              index=pd.to_datetime(panel_uid['date']))
                    monthly_series = monthly_series.asfreq('ME', fill_value=0.0)
                    used_status = "from_db"
                    logger.info("monthly_series sum=%.2f months=%s", monthly_series.sum(), len(monthly_series))

                    if export_monthly_csv_path:
                        if sum_from_filtered_csv and export_filtered_csv_path:
                            filtered_csv = pd.read_csv(cast(str, export_filtered_csv_path))
                            filtered_df = filtered_csv if isinstance(filtered_csv, pd.DataFrame) else pd.DataFrame()
                            if 'date' in filtered_df.columns:
                                filtered_df['date'] = pd.to_datetime(filtered_df['date'], errors='coerce')
                            # Remove duplicates by date before aggregation
                            before_csv_dupes = len(filtered_df)
                            filtered_df = filtered_df.drop_duplicates(subset=['date'], keep='first')
                            if len(filtered_df) != before_csv_dupes:
                                logger.info(
                                    "CSV dedupe before monthly sum: %s -> %s (removed %s duplicates)",
                                    before_csv_dupes,
                                    len(filtered_df),
                                    before_csv_dupes - len(filtered_df),
                                )
                            filtered_df['amount'] = pd.to_numeric(filtered_df['amount'], errors='coerce').fillna(0.0)
                            monthly_df = (
                                filtered_df.set_index('date')['amount']
                                .resample('ME')
                                .sum()
                                .rename("amount_sum")
                                .reset_index()
                            )
                        else:
                            monthly_df = monthly_series.rename("amount_sum").reset_index()
                            monthly_df = monthly_df.rename(columns={"index": "date"})
                        monthly_df.to_csv(export_monthly_csv_path, index=False)
                        logger.info("monthly CSV exported: %s", export_monthly_csv_path)
                except Exception as e:
                    logger.warning("Nem sikerült monthly_series-t előállítani: %s", e)

        # Prepare exogenous variables
        try:
            panel_uid_for_exog = panel_uid if isinstance(panel_uid, pd.DataFrame) else pd.DataFrame()
            exog = make_monthly_exog_no_leakage(panel_uid_for_exog, uid_col='user_id', date_col='date',
                                               shift_periods=1)
            if isinstance(exog, pd.DataFrame) and 'date' in exog.columns:
                exog = exog.set_index(pd.to_datetime(exog['date'])).drop(columns=['date'],
                                                                         errors='ignore')
            if isinstance(exog, pd.DataFrame):
                exog = exog.sort_index().asfreq('ME')
                exog = exog.apply(pd.to_numeric, errors='coerce').ffill().fillna(0.0)
        except Exception as e:
            logger.warning("make_monthly_exog_no_leakage hibát dobott: %s", e)
            exog = None

        # Prepare exogenous forecast
        try:
            if exog is not None and isinstance(exog, pd.DataFrame) and not exog.empty:
                exog_forecast = make_exog_forecast_from_last_known(exog, steps=FORECAST_STEPS)
                if isinstance(exog_forecast, pd.DataFrame):
                    exog_forecast.index = pd.date_range(
                        start=pd.to_datetime(exog.index[-1]) + pd.offsets.MonthEnd(1),
                        periods=FORECAST_STEPS, freq='ME')
                    exog_forecast = exog_forecast.asfreq('ME')
                    exog_forecast = exog_forecast.apply(pd.to_numeric, errors='coerce').ffill().fillna(0.0)
            else:
                exog_forecast = None
        except Exception as e:
            logger.warning("make_exog_forecast_from_last_known hibát dobott: %s", e)
            # Fallback exog_forecast preparation
            try:
                if exog is not None and isinstance(exog, pd.DataFrame) and not exog.empty:
                    idx_future = pd.date_range(
                        start=pd.to_datetime(exog.index[-1]) + pd.offsets.MonthEnd(1),
                        periods=FORECAST_STEPS, freq='ME')
                    exog_forecast = exog.tail(1).reindex(idx_future)
                    exog_forecast = exog_forecast.apply(pd.to_numeric, errors='coerce').ffill().fillna(0.0)
                else:
                    exog_forecast = None
            except Exception:
                exog_forecast = None

    return monthly_series, exog, exog_forecast, used_status

