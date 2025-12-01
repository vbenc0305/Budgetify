import firebase_admin
from firebase_admin import credentials, firestore
from typing import Optional, Any
import threading
import logging
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger(__name__)
logger.debug("db.firebase_client module imported")

_cred_path = "conninfo.json"
_db_client_lock = threading.Lock()
_db_client: Optional[Any] = None
_db_init_error: Optional[str] = None

OFFLINE_DIR = Path("offline_backups")
OFFLINE_DIR.mkdir(parents=True, exist_ok=True)

# marker files for fetch_needed when Firestore cannot be updated immediately
FETCH_MARKER_SUFFIX = ".fetch"


class FirebaseUnavailable(Exception):
    """Raised when Firebase cannot be initialized (quota, auth, network, etc.)."""
    pass


def _init_firebase():
    """Internal: initialize firebase app and return a firestore client."""
    global _db_client, _db_init_error
    logger.debug("_init_firebase called")
    # double-checked locking
    if _db_client is not None:
        logger.debug("_db_client already initialized")
        return _db_client

    with _db_client_lock:
        if _db_client is not None:
            logger.debug("_db_client already initialized (inside lock)")
            return _db_client
        try:
            logger.info(f"Initializing Firebase with cred path: {_cred_path}")
            cred = credentials.Certificate(_cred_path)
            if not firebase_admin._apps:
                # initialize_app can perform network work; keep it inside try/except
                firebase_admin.initialize_app(cred)
            _db_client = firestore.client()
            logger.info("Firebase initialized successfully")
            _db_init_error = None
            return _db_client
        except Exception as e:
            _db_init_error = str(e)
            logger.exception("Failed to initialize Firebase client")
            _db_client = None
            # Raise a dedicated exception for upstream handlers
            raise FirebaseUnavailable(f"Failed to initialize Firebase client: {_db_init_error}") from e


def get_db_client() -> Any:
    logger.debug("get_db_client called")
    # If a previous init attempt failed, return a clear error immediately
    if _db_init_error is not None:
        logger.debug("get_db_client: previous init error detected")
        raise FirebaseUnavailable(f"Firebase unavailable: {_db_init_error}")
    if _db_client is not None:
        logger.debug("returning existing db client")
        return _db_client
    return _init_firebase()


# ----------------- Offline/age helpers -----------------

def _offline_file_path(uid: str) -> Path:
    return OFFLINE_DIR / f"{uid}.jsonl"


def is_offline_file_stale(uid: str, days: int = 7) -> bool:
    """Check whether the per-user offline file is older than `days` days using filesystem mtime.

    This is simple, robust, and does not depend on file content. Uses UTC to avoid timezone issues.
    """
    p = _offline_file_path(uid)
    if not p.exists():
        return False
    try:
        # use UTC to compare reliably with datetime.utcnow()
        mtime = datetime.utcfromtimestamp(p.stat().st_mtime)
        age = datetime.utcnow() - mtime
        logger.debug(f"Offline file for uid={uid} mtime={mtime.isoformat()} age_days={age.days}")
        return age > timedelta(days=days)
    except Exception:
        logger.exception("Failed to check offline file mtime")
        return False


def _fetch_marker_path(uid: str) -> Path:
    return OFFLINE_DIR / f"{uid}{FETCH_MARKER_SUFFIX}"


def _write_fetch_marker(uid: str) -> None:
    try:
        p = _fetch_marker_path(uid)
        p.write_text(datetime.utcnow().isoformat())
        logger.info(f"Wrote fetch marker for uid={uid} at {p}")
    except Exception:
        logger.exception("Failed to write fetch marker")


def _remove_fetch_marker(uid: str) -> None:
    try:
        p = _fetch_marker_path(uid)
        if p.exists():
            p.unlink()
            logger.info(f"Removed fetch marker for uid={uid}")
    except Exception:
        logger.exception("Failed to remove fetch marker")


def _flush_fetch_marker(uid: str) -> bool:
    """Attempt to set fetch_needed=True for user in Firestore and remove local marker on success.
    Returns True if write succeeded and marker removed.
    """
    try:
        db = get_db_client()
    except FirebaseUnavailable:
        logger.debug("_flush_fetch_marker: Firebase unavailable")
        return False

    try:
        db.collection("users").document(uid).set({"fetch_needed": True}, merge=True)
        _remove_fetch_marker(uid)
        logger.info(f"Set fetch_needed=True for uid={uid} in Firestore")
        return True
    except Exception:
        logger.exception("Failed to set fetch_needed in Firestore")
        return False


# ----------------- DB operations -----------------

def get_user_doc(uid: str):
    db = get_db_client()
    # Firestore usr_info
    usr_info_ref = db.collection("usr_info").document(uid)
    usr_info_snap = usr_info_ref.get()
    usr_info = usr_info_snap.to_dict() if usr_info_snap.exists else {}

    # Firestore users kollekció
    user_ref = db.collection("users").document(uid)
    user_snap = user_ref.get()
    user_data = user_snap.to_dict() if user_snap.exists else {}

    # Merge: user_data felülírja az usr_info-t ha ütköznek a kulcsok
    merged = {**usr_info, **user_data}

    return merged


def update_user_doc(uid: str, data: dict):
    db = get_db_client()
    users_data_to_save = {}
    usr_info_data_to_save = {}

    USERS_FIELDS = ["name", "phone", "birthdate"]
    USR_INFO_FIELDS = ["country", "education", "gender", "housing_status", "marital_status",
                       "occupation"]

    for key, value in data.items():
        if key == 'email':
            continue
        if key in USERS_FIELDS:
            users_data_to_save[key] = value
        elif key in USR_INFO_FIELDS:
            usr_info_data_to_save[key] = value

    if users_data_to_save:
        users_doc_ref = db.collection("users").document(uid)
        users_doc_ref.set(users_data_to_save, merge=True)

    if usr_info_data_to_save:
        usr_info_doc_ref = db.collection("usr_info").document(uid)
        usr_info_doc_ref.set(usr_info_data_to_save, merge=True)

    return get_user_doc(uid)


def get_all_occupations():
    db = get_db_client()
    try:
        docs = db.collection("occupations").stream()
        occupations = [doc.id for doc in docs]
        return sorted(occupations)
    except Exception as e:
        print(f"Hiba a foglalkozások lekérésekor: {e}")
        return []


def add_new_occupation(name: str):
    db = get_db_client()
    normalized_name = name.strip()
    if not normalized_name:
        return False
    try:
        doc_ref = db.collection("occupations").document(normalized_name)
        doc_ref.set({}, merge=True)
        return True
    except Exception as e:
        print(f"Hiba az új foglalkozás hozzáadásakor '{name}': {e}")
        return False


def get_user_transactions(uid: str):
    """Return user's transactions from Firestore. Also set `fetch_needed` when local offline stash is stale.

    Logic:
      - Always check offline file age first. If stale, attempt to set `fetch_needed=True` in Firestore.
        - If Firestore is available, write the flag immediately.
        - If Firestore is unavailable or the write fails, write a local fetch marker file for later flushing.
      - Then attempt to read transactions from Firestore as before. If Firestore is unavailable, return [] (existing behavior).
    """
    if not uid:
        return []

    # 1) Check offline file staleness and ensure fetch flag/marker is written (always attempted)
    try:
        if is_offline_file_stale(uid):
            try:
                # try to set fetch_needed in Firestore if available
                db = get_db_client()
                try:
                    db.collection("users").document(uid).set({"fetch_needed": True}, merge=True)
                    logger.info(f"Marked fetch_needed=True for uid={uid} because offline stash is stale")
                except Exception:
                    logger.exception("Failed to write fetch_needed directly; writing local marker instead")
                    _write_fetch_marker(uid)
            except FirebaseUnavailable:
                # Firestore isn't available right now; write a local marker so flush can handle it later
                logger.debug(f"Firestore unavailable when trying to set fetch_needed for uid={uid}; writing local marker")
                _write_fetch_marker(uid)
    except Exception:
        logger.exception("Error while evaluating/offline stash staleness and attempting to set fetch flag")

    # 2) Now attempt to read transactions from Firestore (unchanged behavior)
    try:
        db = get_db_client()
    except FirebaseUnavailable:
        logger.warning(f"get_user_transactions: FirebaseUnavailable for uid={uid}")
        return []

    try:
        user_ref = db.collection("users").document(uid)
        transactions_ref = user_ref.collection("transactions")
        docs = transactions_ref.stream()
        res = [doc.to_dict() for doc in docs]
    except Exception as e:
        logger.exception(f"Hiba a felhasználó tranzakcióinak lekérésekor for uid={uid}: {e}")
        return []


    return res


def get_usr_info_doc(id: str):
    db = get_db_client()
    doc_ref = db.collection("usr_info").document(id)
    doc = doc_ref.get()
    print(f"doc.exists={doc.exists}, id={id}")
    return doc.to_dict() if doc.exists else None


def update_usr_info_doc(id: str, data: dict):
    db = get_db_client()
    doc_ref = db.collection("usr_info").document(id)
    doc_ref.set(data, merge=True)
    return data


def save_user_transaction(uid: str, transaction_data: dict):
    db = get_db_client()
    doc_id = transaction_data.get("id")
    collection_ref = db.collection("users").document(uid).collection("transactions")
    if doc_id:
        doc_ref = collection_ref.document(doc_id)
    else:
        doc_ref = collection_ref.document()
    doc_ref.set(transaction_data)
    return doc_ref.id


def save_user_transactions(uid: str, transactions: list[dict]):
    if not transactions:
        return 0
    db = get_db_client()
    collection_ref = db.collection("users").document(uid).collection("transactions")
    batch = db.batch()
    for tx_data in transactions:
        doc_id = tx_data.get("id")
        doc_ref = collection_ref.document(doc_id) if doc_id else collection_ref.document()
        batch.set(doc_ref, tx_data)
    batch.commit()
    return len(transactions)