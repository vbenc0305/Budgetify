import pandas as pd
from pathlib import Path
from typing import Any, Optional
import threading

_DATASET_CACHE: list[dict[str, Any]] | None = None
_DATASET_MTIME: float | None = None
_CACHE_LOCK = threading.Lock()


def _dataset_path() -> Path:
    # repo root is two levels up from this file (src/Generation)
    return Path(__file__).resolve().parents[2] / "datasets" / "Dataset.csv"


def _parse_amount(value: Any) -> float:
    if value is None:
        return 0.0
    text = str(value).strip()
    if not text:
        return 0.0
    cleaned = text.replace("\xa0", "").replace(" ", "").replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _parse_date(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    dt = pd.to_datetime(text, errors='coerce')
    if pd.isna(dt):
        return text
    # Always return ISO-like string to keep downstream expectations simple
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _normalize_row(raw: dict[str, Any], idx: int) -> dict[str, Any]:
    date_value = raw.get("Tranzakció dátuma") or raw.get("Könyvelés dátuma")
    normalized = {
        "id": f"dataset-{idx}",
        "amount": _parse_amount(raw.get("Összeg")),
        "category": raw.get("Költési kategória") or "Ismeretlen",
        "date": _parse_date(date_value),
        "description": raw.get("Közlemény") or raw.get("Partner neve") or "",
        "for_who": raw.get("Partner neve") or "",
        "tran_type": raw.get("Típus") or raw.get("Bejövő/Kimenő") or "Ismeretlen",
        "internal_transfer": "none",
        "data_source": "dataset",
    }
    return normalized


def _load_base_rows() -> list[dict[str, Any]]:
    global _DATASET_CACHE, _DATASET_MTIME
    path = _dataset_path()
    if not path.exists():
        return []
    mtime = path.stat().st_mtime
    with _CACHE_LOCK:
        if _DATASET_CACHE is not None and _DATASET_MTIME == mtime:
            return _DATASET_CACHE
        try:
            df = pd.read_csv(path, encoding='utf-8-sig')
        except Exception:
            _DATASET_CACHE = []
            _DATASET_MTIME = None
            return []
        rows: list[dict[str, Any]] = []
        for idx, raw in enumerate(df.to_dict(orient='records')):
            try:
                rows.append(_normalize_row(raw, idx))
            except Exception:
                continue
        _DATASET_CACHE = rows
        _DATASET_MTIME = mtime if rows else None
        return rows


def load_dataset_magyar(user_id: Optional[str] = None, user_email: Optional[str] = None) -> list[dict[str, Any]]:
    """Return normalized fallback transactions ready for downstream ML/DB flows."""
    base_rows = _load_base_rows()
    if not base_rows:
        return []
    resolved_user = user_id or "fallback-user"
    resolved_email = user_email or resolved_user
    rows: list[dict[str, Any]] = []
    for idx, row in enumerate(base_rows):
        tx = dict(row)
        tx["user_id"] = resolved_user
        tx["user_email"] = resolved_email
        tx["id"] = row.get("id", f"dataset-{idx}")
        rows.append(tx)
    return rows
