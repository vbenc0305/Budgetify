import firebase_admin
from firebase_admin import credentials, firestore
from typing import Optional, Any
import threading
import logging
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
import os
import socket
import csv
from concurrent.futures import ThreadPoolExecutor, Future, TimeoutError as FutureTimeout
import re

logger = logging.getLogger(__name__)
logger.debug("db.firebase_client module imported")

PROJECT_ROOT = Path(__file__).resolve().parent.parent

_cred_path = "conninfo.json"
_db_client_lock = threading.Lock()
_db_client: Optional[Any] = None
_db_init_error: Optional[str] = None

# Fast-fail/backoff controls to avoid repeated long waits when Google services are unreachable or quota is exceeded.
# Can be tweaked via environment variables.
INIT_CONNECT_HOST = os.getenv("FIREBASE_INIT_HOST", "oauth2.googleapis.com")
INIT_CONNECT_PORT = int(os.getenv("FIREBASE_INIT_PORT", "443"))
INIT_CONNECT_TIMEOUT = float(os.getenv("FIREBASE_INIT_TIMEOUT", "2"))  # seconds for TCP probe
INIT_BACKOFF_SECONDS = int(os.getenv("FIREBASE_RETRY_BACKOFF", "60"))  # wait between init attempts after failure
QUOTA_BACKOFF_SECONDS = int(os.getenv("FIREBASE_QUOTA_BACKOFF", "3600"))  # longer wait after quota errors
INIT_DEADLINE_SECONDS = float(os.getenv("FIREBASE_INIT_DEADLINE", "5"))  # fail-fast cutoff for firebase_admin (5s default to avoid 300s hangs)

_last_init_attempt: Optional[datetime] = None
_quota_exceeded_until: Optional[datetime] = None
_init_executor = ThreadPoolExecutor(max_workers=1)
_init_future: Optional[Future] = None

# Use a single directory for per-user transaction cache and offline stashes for readability.
# `OFFLINE_DIR` is kept as an alias for backward compatibility.
_default_user_tx_dir = PROJECT_ROOT / "userTransactions"
USER_TX_DIR = Path(os.getenv("BUDGETIFY_USER_TX_DIR", str(_default_user_tx_dir))).expanduser().resolve()
USER_TX_DIR.mkdir(parents=True, exist_ok=True)
OFFLINE_DIR = USER_TX_DIR

FALLBACK_DATASET_PATH = PROJECT_ROOT / "datasets" / "Dataset.csv"
_fallback_rows: list[dict] | None = None
_fallback_rows_mtime: float | None = None
_fallback_lock = threading.Lock()

# marker files for fetch_needed when Firestore cannot be updated immediately
FETCH_MARKER_SUFFIX = ".fetch"


class FirebaseUnavailable(Exception):
    """Raised when Firebase cannot be initialized (quota, auth, network, etc.)."""
    pass


def _looks_like_quota_error(exc: Exception | str) -> bool:
    text = str(exc).lower()
    return any(keyword in text for keyword in ("quota", "rate limit", "429"))


def _mark_quota_backoff(reason: str) -> None:
    global _quota_exceeded_until, _db_init_error
    _db_init_error = reason
    _quota_exceeded_until = datetime.now(timezone.utc) + timedelta(seconds=QUOTA_BACKOFF_SECONDS)


def _firebase_init_worker():
    """Worker that initializes Firebase in a separate thread with socket timeout."""
    import socket as sock_module
    # Set aggressive socket timeout to prevent 300s hangs
    old_timeout = sock_module.getdefaulttimeout()
    try:
        # Force all socket operations to timeout after 5 seconds
        sock_module.setdefaulttimeout(5.0)

        try:
            firebase_admin.get_app()
            logger.debug("Firebase default app already exists; worker will reuse instance")
        except ValueError:
            cred = credentials.Certificate(_cred_path)
            firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as exc:
        logger.exception("Firebase init worker failed")
        raise exc
    finally:
        # Restore original timeout
        sock_module.setdefaulttimeout(old_timeout)


def _init_firebase():
    """Internal: initialize firebase app and return a firestore client.

    This function now includes a short TCP connectivity probe and backoff logic so that
    when Google's token endpoints are unreachable (or quota-limited) the app fails fast
    and falls back to local caches instead of blocking for long network timeouts.
    """
    global _db_client, _db_init_error, _last_init_attempt, _quota_exceeded_until, _init_future
    logger.debug("_init_firebase called")

    now = datetime.now(timezone.utc)

    # CRITICAL: Check quota status FIRST before any network operations
    if _quota_exceeded_until is not None and now < _quota_exceeded_until:
        msg = f"Firebase quota backoff active until {_quota_exceeded_until.isoformat()}"
        logger.warning(msg)
        raise FirebaseUnavailable(msg)

    # double-checked locking
    if _db_client is not None:
        logger.debug("_db_client already initialized")
        return _db_client


    # Feature-flag to force immediate fail-fast (useful during testing or when you want local-only operation)
    if os.getenv("FIREBASE_FAILFAST", "").lower() in ("1", "true", "yes"):
        _db_init_error = "FIREBASE_FAILFAST enabled"
        logger.warning("FIREBASE_FAILFAST enabled - skipping Firebase initialization")
        raise FirebaseUnavailable(_db_init_error)


    # If there was a recent init attempt that failed, avoid hammering and fail fast until backoff expires
    if _last_init_attempt is not None and (now - _last_init_attempt) < timedelta(seconds=INIT_BACKOFF_SECONDS):
        msg = f"Recent Firebase init failed at {_last_init_attempt.isoformat()}; backing off ({INIT_BACKOFF_SECONDS}s)"
        logger.debug(msg)
        _db_init_error = msg
        raise FirebaseUnavailable(msg)

    with _db_client_lock:
        if _db_client is not None:
            logger.debug("_db_client already initialized (inside lock)")
            return _db_client
    # perform a quick TCP probe to the oauth2 host so we can fail fast if network is down or blocked
    try:
        logger.debug(f"Probing connectivity to {INIT_CONNECT_HOST}:{INIT_CONNECT_PORT} with timeout {INIT_CONNECT_TIMEOUT}s")
        sock = socket.create_connection((INIT_CONNECT_HOST, INIT_CONNECT_PORT), timeout=INIT_CONNECT_TIMEOUT)
        sock.close()
    except Exception as probe_exc:
        _last_init_attempt = datetime.now(timezone.utc)
        _db_init_error = f"Network probe failed: {probe_exc}"
        logger.warning(f"Firebase init probe failed: {probe_exc}")
        raise FirebaseUnavailable(_db_init_error) from probe_exc

    # Add a timeout for Firebase initialization
    try:
        with socket.create_connection((INIT_CONNECT_HOST, INIT_CONNECT_PORT), timeout=INIT_CONNECT_TIMEOUT):
            logger.debug(f"Connectivity probe to {INIT_CONNECT_HOST}:{INIT_CONNECT_PORT} succeeded")
    except socket.timeout:
        msg = f"Connectivity probe to {INIT_CONNECT_HOST}:{INIT_CONNECT_PORT} timed out after {INIT_CONNECT_TIMEOUT}s"
        logger.error(msg)
        _db_init_error = msg
        raise FirebaseUnavailable(msg)
    except Exception as e:
        msg = f"Connectivity probe to {INIT_CONNECT_HOST}:{INIT_CONNECT_PORT} failed: {e}"
        logger.error(msg)
        _db_init_error = msg
        raise FirebaseUnavailable(msg)

    future: Optional[Future] = None
    with _db_client_lock:
        if _db_client is not None:
            return _db_client
        if _init_future and _init_future.done():
            try:
                client = _init_future.result()
                _db_client = client
                _init_future = None
                _db_init_error = None
                return _db_client
            except Exception as exc:
                _init_future = None
                msg = f"Firebase initialization failed: {exc}"
                logger.error(msg)
                _db_init_error = msg
                if _looks_like_quota_error(exc):
                    _mark_quota_backoff(msg)
                raise FirebaseUnavailable(msg)
        if _init_future is None:
            _last_init_attempt = datetime.now(timezone.utc)
            logger.debug("Spawning Firebase init worker")
            _init_future = _init_executor.submit(_firebase_init_worker)
        future = _init_future

    try:
        client = future.result(timeout=INIT_DEADLINE_SECONDS)
    except FutureTimeout:
        msg = f"Firebase initialization timed out after {INIT_DEADLINE_SECONDS}s - likely quota exceeded"
        logger.error(msg)
        # Cancel the future (though worker thread will continue until Python GC)
        with _db_client_lock:
            _init_future = None
        _mark_quota_backoff(msg)
        logger.warning(f"Quota backoff activated until {_quota_exceeded_until.isoformat() if _quota_exceeded_until else 'unknown'}")
        raise FirebaseUnavailable(msg)
    except Exception as exc:
        msg = f"Firebase initialization failed: {exc}"
        logger.error(msg)
        with _db_client_lock:
            _init_future = None
        if _looks_like_quota_error(exc):
            _mark_quota_backoff(msg)
        else:
            _db_init_error = msg
        raise FirebaseUnavailable(msg)
    else:
        with _db_client_lock:
            _db_client = client
            _init_future = None
            _db_init_error = None
        logger.info("Firebase initialized successfully")
        return client


def get_db_client() -> Any:
    logger.debug("get_db_client called")
    # If a previous init attempt failed, return a clear error immediately
    if _db_init_error is not None:
        logger.debug("get_db_client: previous init error detected")
        # If the error is old and backoff expired, attempt to re-init; otherwise raise quickly
        now = datetime.now(timezone.utc)
        if _quota_exceeded_until is not None and now < _quota_exceeded_until:
            raise FirebaseUnavailable(f"Firebase unavailable: {_db_init_error}")
        if _last_init_attempt is not None and (now - _last_init_attempt) < timedelta(seconds=INIT_BACKOFF_SECONDS):
            raise FirebaseUnavailable(f"Firebase unavailable: {_db_init_error}")
    if _db_client is not None:
        logger.debug("returning existing db client")
        return _db_client
    return _init_firebase()


# --- quota helpers -------------------------------------------------

def is_quota_exceeded() -> bool:
    """Return True if we've recently detected a quota/rate-limit condition and are currently backing off."""
    if _quota_exceeded_until is None:
        return False
    try:
        return datetime.now(timezone.utc) < _quota_exceeded_until
    except Exception:
        return False


def get_quota_status() -> dict:
    """Return a small status dict describing quota/backoff state for logging or health checks.

    Keys:
      - quota_exceeded: bool
      - quota_exceeded_until: ISO timestamp or None
      - last_init_attempt: ISO timestamp or None
      - init_error: str or None
    """
    return {
        "quota_exceeded": is_quota_exceeded(),
        "quota_exceeded_until": _quota_exceeded_until.isoformat() if _quota_exceeded_until else None,
        "last_init_attempt": _last_init_attempt.isoformat() if _last_init_attempt else None,
        "init_error": _db_init_error,
    }


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
        # use timezone-aware UTC datetimes
        mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
        age = datetime.now(timezone.utc) - mtime
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
        p.write_text(datetime.now(timezone.utc).isoformat())
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


# ----------------- Local user transactions helpers -----------------

def _local_tx_path(uid: str) -> Path:
    """Per-user JSONL file path for locally saved transactions."""
    return USER_TX_DIR / f"{uid}.jsonl"


def _append_local_tx(uid: str, tx_data: dict) -> None:
    """Append a single transaction as JSON line to the per-user file."""
    try:
        p = _local_tx_path(uid)
        with p.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(tx_data, ensure_ascii=False) + "\n")
        logger.info(f"Appended local tx for uid={uid} to {p}")
    except Exception:
        logger.exception(f"Failed to append local tx for uid={uid}")


def _append_local_txs(uid: str, tx_list: list[dict]) -> int:
    """Append multiple transactions; returns number written."""
    count = 0
    try:
        p = _local_tx_path(uid)
        with p.open("a", encoding="utf-8") as fh:
            for tx in tx_list:
                fh.write(json.dumps(tx, ensure_ascii=False) + "\n")
                count += 1
        logger.info(f"Appended {count} local txs for uid={uid} to {p}")
    except Exception:
        logger.exception(f"Failed to append local txs for uid={uid}")
    return count


def _read_local_txs(uid: str) -> list:
    """Read locally saved transactions for a user; returns list of dicts.
    If file missing, returns empty list.
    """
    p = _local_tx_path(uid)
    if not p.exists():
        return []
    out = []
    try:
        with p.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except Exception:
                    logger.exception(f"Skipping invalid JSON line in {p}")
        logger.debug(f"Read {len(out)} local txs for uid={uid} from {p}")
    except Exception:
        logger.exception(f"Failed to read local txs for uid={uid}")
    return out


def _write_local_txs_overwrite(uid: str, tx_list: list[dict]) -> None:
    """Atomically overwrite the per-user local JSONL file with tx_list (list of dicts)."""
    try:
        p = _local_tx_path(uid)
        tmp = p.with_suffix('.tmp')
        with tmp.open('w', encoding='utf-8') as fh:
            for tx in tx_list:
                fh.write(json.dumps(tx, ensure_ascii=False) + '\n')
        # atomic replace
        tmp.replace(p)
        logger.info(f"Wrote {len(tx_list)} txs to local stash for uid={uid} at {p}")
    except Exception:
        logger.exception(f"Failed to write local txs for uid={uid}")


def _upsert_local_txs(uid: str, tx_list: list[dict]) -> None:
    """Update existing local txs by `id` and append new ones to keep cache aligned with writes."""
    if not tx_list:
        return

    local = _read_local_txs(uid)
    index_by_id: dict[str, int] = {}
    for idx, tx in enumerate(local):
        if isinstance(tx, dict) and tx.get("id") and tx.get("id") not in index_by_id:
            index_by_id[str(tx.get("id"))] = idx

    for tx in tx_list:
        if not isinstance(tx, dict):
            continue
        tx_copy = dict(tx)
        tx_id = tx_copy.get("id")
        if tx_id:
            tx_key = str(tx_id)
            if tx_key in index_by_id:
                local[index_by_id[tx_key]] = tx_copy
            else:
                index_by_id[tx_key] = len(local)
                local.append(tx_copy)
        else:
            local.append(tx_copy)

    _write_local_txs_overwrite(uid, local)


def _remove_local_txs_by_ids(uid: str, transaction_ids: list[str]) -> None:
    """Remove deleted transaction IDs from local cache to avoid stale cache-first reads."""
    if not transaction_ids:
        return
    id_set = {str(tx_id) for tx_id in transaction_ids if tx_id is not None}
    if not id_set:
        return

    local = _read_local_txs(uid)
    if not local:
        return

    filtered = []
    for tx in local:
        if not isinstance(tx, dict):
            filtered.append(tx)
            continue
        tx_id = tx.get("id")
        tx_doc_id = tx.get("transaction_id")
        if str(tx_id) in id_set or str(tx_doc_id) in id_set:
            continue
        filtered.append(tx)

    if len(filtered) != len(local):
        _write_local_txs_overwrite(uid, filtered)


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
    merged.setdefault("anonymous_stats_consent", False)

    return merged


def update_user_doc(uid: str, data: dict):
    db = get_db_client()
    users_data_to_save = {}
    usr_info_data_to_save = {}

    USERS_FIELDS = ["name", "phone", "birthdate", "anonymous_stats_consent"]
    USR_INFO_FIELDS = ["country", "education", "gender", "housing_status", "marital_status",
                       "occupation"]

    if "anonymous_stats_consent" in data and not isinstance(data.get("anonymous_stats_consent"), bool):
        raise ValueError("anonymous_stats_consent must be a boolean")

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


def _parse_amount(value: str) -> float:
    cleaned = (value or "").replace("\xa0", "").replace(" ", "")
    cleaned = cleaned.replace(",", "")
    if not cleaned:
        raise ValueError("empty amount value in fallback dataset")
    return float(cleaned)


def _normalize_date_value(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y.%m.%d %H:%M:%S", "%Y.%m.%d"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return text


def _normalize_dataset_row(row: dict, idx: int) -> dict:
    date_value = row.get("Tranzakció dátuma") or row.get("Könyvelés dátuma")
    amount_value = _parse_amount(str(row.get("Összeg", "")))
    return {
        "id": row.get("id") or f"fallback-{idx}",
        "amount": amount_value,
        "category": row.get("Költési kategória") or "Ismeretlen",
        "date": _normalize_date_value(date_value),
        "description": row.get("Közlemény") or row.get("Partner neve") or "",
        "for_who": row.get("Partner neve") or "",
        "tran_type": row.get("Típus") or row.get("Bejövő/Kimenő") or "Ismeretlen",
        "internal_transfer": "none",
        "data_source": "dataset",
    }


def _load_dataset_fallback() -> list[dict]:
    global _fallback_rows, _fallback_rows_mtime
    path = FALLBACK_DATASET_PATH
    if not path.exists():
        logger.warning("Fallback dataset missing at %s", path)
        return []

    mtime = path.stat().st_mtime
    with _fallback_lock:
        if _fallback_rows is not None and _fallback_rows_mtime == mtime:
            return _fallback_rows

        rows: list[dict] = []
        try:
            with path.open("r", encoding="utf-8-sig") as csv_file:
                reader = csv.DictReader(csv_file)
                for idx, raw in enumerate(reader):
                    try:
                        rows.append(_normalize_dataset_row(raw, idx))
                    except Exception:
                        logger.exception("Failed to normalize fallback dataset row %s", idx)
        except Exception:
            logger.exception("Failed to load fallback dataset from %s", path)
            rows = []

        _fallback_rows = rows
        _fallback_rows_mtime = mtime if rows else None
        return rows


def get_fallback_transactions(uid: str) -> list[dict]:
    base_rows = _load_dataset_fallback()
    if not base_rows:
        return []
    output = []
    for idx, row in enumerate(base_rows):
        tx = dict(row)
        tx["user_id"] = uid
        tx.setdefault("id", f"fallback-{uid}-{idx}")
        output.append(tx)
    return output


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

    # Short-circuit: if we have a fresh local stash for this user, prefer it and skip Firestore.
    try:
        local_path = _local_tx_path(uid)
        if local_path.exists():
            mtime = datetime.fromtimestamp(local_path.stat().st_mtime, tz=timezone.utc)
            age = datetime.now(timezone.utc) - mtime
            if age <= timedelta(days=7):
                logger.info(f"Using fresh local stash for uid={uid} (age_days={age.days}) - skipping Firestore")
                return _read_local_txs(uid)
    except Exception:
        # If anything goes wrong when inspecting the local file, continue with normal logic
        logger.exception("Error while checking local userTransactions stash; falling back to normal fetch logic")

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
        logger.warning(f"get_user_transactions: FirebaseUnavailable for uid={uid} — returning local stash if present")
        # Fallback: return locally saved transactions if any
        local = _read_local_txs(uid)
        if local:
            return local
        fallback = get_fallback_transactions(uid)
        if fallback:
            logger.info("Serving fallback dataset transactions for uid=%s", uid)
            return fallback
        return []

    try:
        user_ref = db.collection("users").document(uid)
        transactions_ref = user_ref.collection("transactions")
        docs = transactions_ref.stream()
        res = [doc.to_dict() | {"transaction_id": doc.id} for doc in docs]
    except Exception as e:
        logger.exception(f"Hiba a felhasználó tranzakcióinak lekérésekor for uid={uid}: {e} — falling back to local stash")
        local = _read_local_txs(uid)
        if local:
            return local
        fallback = get_fallback_transactions(uid)
        if fallback:
            logger.info("Serving fallback dataset transactions for uid=%s due to read failure", uid)
            return fallback
        return []

    # Merge remote + local stash: local stash may contain transactions not yet pushed; include them but avoid duplicates by id
    local = _read_local_txs(uid)
    if not local:
        # write remote result to local cache for future fast reads
        try:
            _write_local_txs_overwrite(uid, res)
        except Exception:
            logger.exception("Failed to update local cache with remote transactions")
        return res

    # Build fingerprint sets for deduplication
    remote_by_fp = {}
    remote_by_id = {}
    for tx in res:
        if not isinstance(tx, dict):
            continue
        try:
            fp = _tx_fingerprint_for_dedup(tx)
            remote_by_fp[fp] = tx
        except Exception:
            logger.exception("Failed to create fingerprint for remote transaction")
        tx_id = tx.get('id')
        if tx_id:
            remote_by_id[tx_id] = tx

    # Start with all remote transactions
    merged = list(res)

    # Add local transactions that are not duplicates
    for ltx in local:
        if not isinstance(ltx, dict):
            continue

        # Check if already in remote by ID
        lid = ltx.get('id')
        if lid and lid in remote_by_id:
            logger.debug(f"Skipping local tx with id={lid} - already in remote by ID")
            continue

        # Check if already in remote by fingerprint
        try:
            lfp = _tx_fingerprint_for_dedup(ltx)
            if lfp in remote_by_fp:
                logger.debug(f"Skipping local tx with fingerprint={lfp[:50]}... - already in remote")
                continue
        except Exception:
            logger.exception("Failed to create fingerprint for local transaction - including it anyway")

        # Not a duplicate - add to merged list
        merged.append(ltx)

    logger.info(f"Merged {len(res)} remote + {len(local)} local = {len(merged)} total txs for uid={uid} (removed {len(res) + len(local) - len(merged)} duplicates)")

    # Attempt to update local cache with merged view so future reads use the cache
    try:
        _write_local_txs_overwrite(uid, merged)
    except Exception:
        logger.exception("Failed to update local cache with merged transactions")
    return merged


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


def save_user_transaction(uid: str, transaction_data: dict, allow_local_fallback: bool = True):
    """Save a single transaction.

    By default, falls back to local JSONL when Firestore is unavailable.
    If `allow_local_fallback` is False, Firebase errors are raised to caller.
    Returns the document id (str) on success or the locally generated id when falling back.
    """
    # ensure we have an id for local fallback
    import uuid
    doc_id = transaction_data.get("id") or str(uuid.uuid4())
    transaction_data = dict(transaction_data)
    transaction_data["id"] = doc_id

    try:
        db = get_db_client()
    except FirebaseUnavailable:
        if not allow_local_fallback:
            raise
        logger.warning(f"save_user_transaction: Firebase unavailable for uid={uid}; saving locally")
        _append_local_tx(uid, transaction_data)
        return doc_id

    try:
        collection_ref = db.collection("users").document(uid).collection("transactions")
        doc_ref = collection_ref.document(doc_id)
        doc_ref.set(transaction_data)
        try:
            _upsert_local_txs(uid, [transaction_data])
        except Exception:
            logger.exception("Failed to sync local cache after save_user_transaction")
        return doc_ref.id
    except Exception:
        if not allow_local_fallback:
            raise
        logger.exception(f"Failed to save transaction to Firestore for uid={uid}; saving locally")
        _append_local_tx(uid, transaction_data)
        return doc_id


def save_user_transactions(uid: str, transactions: list[dict], allow_local_fallback: bool = True):
    """Save multiple transactions.

    By default, falls back to local JSONL when Firestore is unavailable.
    If `allow_local_fallback` is False, Firebase errors are raised to caller.
    Returns number of written transactions.
    """
    if not transactions:
        return 0

    # ensure ids exist for local fallback
    import uuid
    txs = []
    for tx in transactions:
        tx_copy = dict(tx)
        if not tx_copy.get("id"):
            tx_copy["id"] = str(uuid.uuid4())
        txs.append(tx_copy)

    try:
        db = get_db_client()
    except FirebaseUnavailable:
        if not allow_local_fallback:
            raise
        logger.warning(f"save_user_transactions: Firebase unavailable for uid={uid}; saving {len(txs)} locally")
        return _append_local_txs(uid, txs)

    try:
        collection_ref = db.collection("users").document(uid).collection("transactions")
        batch = db.batch()
        for tx_data in txs:
            doc_id = tx_data.get("id")
            doc_ref = collection_ref.document(doc_id) if doc_id else collection_ref.document()
            batch.set(doc_ref, tx_data)
        batch.commit()
        try:
            _upsert_local_txs(uid, txs)
        except Exception:
            logger.exception("Failed to sync local cache after save_user_transactions")
        return len(txs)
    except Exception:
        if not allow_local_fallback:
            raise
        logger.exception(f"Failed to batch save transactions to Firestore for uid={uid}; saving locally")
        return _append_local_txs(uid, txs)


def flush_local_transactions(uid: str) -> int:
    """Attempt to push locally-stashed transactions for `uid` to Firestore.

    Returns number of transactions successfully pushed. On success the local file is removed.
    If Firebase is unavailable or push fails, returns 0 and keeps the local file.
    """
    txs = _read_local_txs(uid)
    if not txs:
        return 0
    try:
        db = get_db_client()
    except FirebaseUnavailable:
        logger.debug(f"flush_local_transactions: Firebase unavailable for uid={uid}")
        return 0

    try:
        collection_ref = db.collection("users").document(uid).collection("transactions")
        batch = db.batch()
        for tx in txs:
            doc_id = tx.get('id')
            doc_ref = collection_ref.document(doc_id) if doc_id else collection_ref.document()
            batch.set(doc_ref, tx)
        batch.commit()
        # If commit succeeded, remove local stash
        try:
            p = _local_tx_path(uid)
            if p.exists():
                p.unlink()
                logger.info(f"Flushed and removed local tx stash for uid={uid}")
        except Exception:
            logger.exception(f"Failed to remove local tx stash for uid={uid} after flushing")
        return len(txs)
    except Exception:
        logger.exception(f"Failed to flush local transactions to Firestore for uid={uid}")
        return 0


def flush_all_local_transactions() -> int:
    """Find all files in USER_TX_DIR and attempt to flush each one. Returns total pushed count."""
    total = 0
    try:
        for p in USER_TX_DIR.iterdir():
            if not p.is_file() or not p.name.endswith('.jsonl'):
                continue
            uid = p.stem
            pushed = flush_local_transactions(uid)
            total += pushed
    except Exception:
        logger.exception("Failed during flush_all_local_transactions")
    return total

# Helper function for duplicate detection using fingerprints
def _tx_fingerprint_for_dedup(tx: dict) -> str:
    """
    Create a fingerprint for transaction deduplication using full timestamp, amount, and key fields.
    This matches the logic in api.routes.transactions._tx_fingerprint_for_matching
    """
    def _normalize_text(s: Any) -> str:
        if not s:
            return ""
        t = str(s).lower()
        # normalize diacritics
        t = t.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ö", "o").replace("ő", "o").replace("ú", "u").replace("ü", "u").replace("ű", "u")
        t = re.sub(r"\s+", " ", t)
        return t

    # Full timestamp (not just date)
    date_raw = str(tx.get("date", "")).strip()
    date_full = date_raw if date_raw else ""

    # Amount with 2 decimal places
    try:
        amount_val = float(tx.get("amount", 0.0) or 0.0)
    except Exception:
        amount_val = 0.0
    amount_s = f"{amount_val:.2f}"

    # Normalized text fields
    desc = _normalize_text(tx.get("description", ""))[:200]
    cat = _normalize_text(tx.get("category", ""))
    ttype = _normalize_text(tx.get("tran_type", ""))
    internal = _normalize_text(tx.get("internal_transfer", ""))

    return "|".join([date_full, amount_s, desc, cat, ttype, internal])


def delete_user_transactions_batched(uid: str, transaction_ids: list[str], batch_size: int = 500) -> int:
    """Delete multiple user transactions using Firestore batch writes.

    Returns the number of transaction IDs processed (requested for deletion).

    This helper assumes that deleting a non-existent document is a no-op.
    Raises FirebaseUnavailable if Firestore cannot be initialized, and lets
    other exceptions propagate to the caller.
    """
    if not transaction_ids:
        return 0

    try:
        db = get_db_client()
    except FirebaseUnavailable as exc:
        # surface as-is so API layer can convert to 503
        logger.warning(f"delete_user_transactions_batched: Firebase unavailable for uid={uid}: {exc}")
        raise

    collection_ref = db.collection("users").document(uid).collection("transactions")

    total_processed = 0
    # Chunk IDs into batches of at most batch_size (Firestore limit is 500 ops per batch)
    for i in range(0, len(transaction_ids), batch_size):
        chunk = transaction_ids[i : i + batch_size]
        if not chunk:
            continue
        batch = db.batch()
        for tx_id in chunk:
            doc_ref = collection_ref.document(str(tx_id))
            batch.delete(doc_ref)
        # Commit this batch; any exception should bubble up to caller
        batch.commit()
        total_processed += len(chunk)

    try:
        _remove_local_txs_by_ids(uid, transaction_ids)
    except Exception:
        logger.exception("Failed to sync local cache after delete_user_transactions_batched")

    return total_processed

