"""Lightweight data access helpers for the forecasting pipeline."""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from db.firebase_client import get_user_transactions


def get_all_transactions(uid: str) -> List[Dict[str, Any]]:
    """Return all transactions for a user id.

    Falls back to local cache or bundled dataset via firebase_client logic.
    """
    if not uid:
        return []
    return get_user_transactions(uid) or []


def load_global_data(uid_or_email: str) -> pd.DataFrame:
    """Return a DataFrame for smoke tests or ad-hoc data inspection.

    The argument is treated as a uid (email is accepted for backward usage).
    """
    rows = get_all_transactions(uid_or_email)
    return pd.DataFrame(rows)

