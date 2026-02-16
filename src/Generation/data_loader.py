# src/data_loader.py

import pandas as pd
from src.Generation.Feature_engineering import engineer_all_features
from typing import List, Dict, Any, Optional
import os
import time
import logging

# Use fallback dataset loader when DB isn't available. Import lazily to avoid initializing Firebase at import time.
from src.Generation import fallbacks

logger = logging.getLogger(__name__)


def _ensure_required_columns(df: pd.DataFrame) -> pd.DataFrame:
    required_defaults = {
        "amount": 0.0,
        "date": pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "user_id": "fallback-user",
        "internal_transfer": "none",
    }
    for col, default in required_defaults.items():
        if col not in df.columns:
            logger.warning("fallback dataframe missing column '%s'; filling default", col)
            df[col] = default
        df[col] = df[col].fillna(default)
    return df


def _load_fallback_frame(uid: str | None = None) -> pd.DataFrame:
    records = fallbacks.load_dataset_magyar(user_id=uid, user_email=uid)
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    df = _ensure_required_columns(df)
    return df


def is_firebase_quota_reached() -> bool:
    """
    Check if Firebase database quota is reached.
    Returns True if quota is reached, otherwise False.
    """
    try:
        from src.DAO.DAOimpl import FirebaseDAO
        dao = FirebaseDAO("quota_check")
        # Example: Check a lightweight endpoint or quota status
        quota_status = dao.check_quota_status()  # This method should be implemented in FirebaseDAO
        return quota_status.get("quota_reached", False)
    except Exception:
        return True  # Assume quota is reached if there's an error


# Globálisan elérhető DataFrame
def load_global_data(email: str) -> pd.DataFrame:
    """
    Betölti az összes tranzakciót és végrehajtja a feature-engineeringet.
    Ha a Firestore nem elérhető vagy nincs adat, visszatér a local fallback CSV-vel.
    """
    # Check if Firebase quota is reached
    if is_firebase_quota_reached():
        df = _load_fallback_frame(email)
        if df.empty:
            return df
        df['user_email'] = email
        try:
            df = engineer_all_features(df)
        except Exception:
            logger.exception("engineer_all_features failed on fallback records; returning raw dataframe")
            return df
        return df

    # If configured to prefer local fallback, do it immediately to avoid any remote waits
    if os.getenv("USE_LOCAL_FALLBACK", "").lower() in ("1", "true", "yes"):
        df = _load_fallback_frame(email)
        if df.empty:
            return df
        df['user_email'] = email
        try:
            df = engineer_all_features(df)
        except Exception:
            logger.exception("engineer_all_features failed on fallback records; returning raw dataframe")
            return df
        return df

    txs: Optional[List[Dict[str, Any]]] = None
    try:
        # lazy import to avoid Firebase initialization on module import
        from src.DAO.DAOimpl import FirebaseDAO
        dao = FirebaseDAO("user")
        # Set a timeout for Firebase calls
        start_time = time.time()
        txs = dao.read_user_transactions(email)
        if time.time() - start_time > 10:  # Timeout after 10 seconds
            raise TimeoutError("Firebase call exceeded timeout")
    except Exception:
        txs = None

    if not txs:
        # fallback to dataset CSV
        df = _load_fallback_frame(email)
        if df.empty:
            return df
        df['user_email'] = email
        try:
            df = engineer_all_features(df)
        except Exception:
            logger.exception("engineer_all_features failed on fallback records; returning raw dataframe")
            return df
        return df

    df = pd.DataFrame(txs)
    df['user_email'] = email  # Felhasználó azonosítása
    # 2. Feature‐engineering
    df = engineer_all_features(df)
    return df


def get_all_transactions(uid: str):
    """Return list of transactions for a user. Use fallback CSV when DB is unavailable or returns no data."""
    if not uid:
        return []

    # Check if Firebase quota is reached
    if is_firebase_quota_reached():
        df = _load_fallback_frame(uid)
        return df.to_dict(orient='records') if not df.empty else []

    # Respect explicit local-fallback flag
    if os.getenv("USE_LOCAL_FALLBACK", "").lower() in ("1", "true", "yes"):
        df = _load_fallback_frame(uid)
        return df.to_dict(orient='records') if not df.empty else []

    try:
        from src.DAO.DAOimpl import FirebaseDAO
        user_dao = FirebaseDAO("users")
        # Set a timeout for Firebase calls
        start_time = time.time()
        transactions = user_dao.read_user_transactions(uid)
        if time.time() - start_time > 10:  # Timeout after 10 seconds
            raise TimeoutError("Firebase call exceeded timeout")
        # If DAO returned None it means Firebase was unavailable/fast-failed -> use local fallback
        if transactions:
            return list(transactions)
    except Exception:
        # Firestore unavailable or error -> fall back to CSV
        pass

    df = _load_fallback_frame(uid)
    return df.to_dict(orient='records') if not df.empty else []
