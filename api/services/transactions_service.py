from __future__ import annotations

import asyncio
import importlib
import logging
import math
import threading
from typing import Any, Callable, Dict, List, Mapping, Optional, Protocol, Set, cast

from fastapi import HTTPException

from api.helpers.transaction_helpers import (
    _normalize_input_to_dicts,
    _serialize_mass_import_response_for_api,
    _tx_fingerprint_for_matching,
    transform_excel_row,
)
from api.transaction_payloads import serialize_transaction_for_api
from db import firebase_client
from db.firebase_client import (
    FirebaseUnavailable,
    delete_user_transactions_batched,
    get_db_client,
    get_user_transactions,
    save_user_transaction,
    save_user_transactions,
)
from src.models.transactions import Transaction

logger = logging.getLogger(__name__)

TransactionDict = Dict[str, Any]
ForecastResult = Dict[str, Any]
TransactionLoader = Callable[[str], Any]
TransactionSaver = Callable[..., str]
TransactionBatchDeleter = Callable[[str, List[str]], int]

PIPELINE_MODULE_PATH = "src.Generation.Case_one_has_enough_Transact_arima_refactored"


class ForecastPipelineProtocol(Protocol):
    def run(self, uid: str, plot: bool = False, verbose: bool = False) -> Any:
        ...


_pipeline_lock = threading.Lock()
_pipeline: Optional[ForecastPipelineProtocol] = None


async def _get_pipeline() -> ForecastPipelineProtocol:
    """Return a lazily created, cached forecast pipeline instance."""
    global _pipeline
    if _pipeline is not None:
        return _pipeline

    def _create_pipeline() -> ForecastPipelineProtocol:
        global _pipeline
        with _pipeline_lock:
            if _pipeline is None:
                try:
                    module = importlib.import_module(PIPELINE_MODULE_PATH)
                    pipeline_class = getattr(module, "ForecastPipeline")
                    _pipeline = cast(ForecastPipelineProtocol, pipeline_class())
                except Exception:
                    logger.exception("Failed to initialize ForecastPipeline")
                    raise

            assert _pipeline is not None
            return _pipeline

    try:
        return await asyncio.to_thread(_create_pipeline)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to initialize ForecastPipeline: {exc}")


def _sanitize_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sanitize_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize_json_value(item) for item in value]

    try:
        numeric = float(value)
    except Exception:
        return value

    if math.isfinite(numeric):
        return numeric
    return None


def _build_transaction(transaction_data: Mapping[str, Any], uid: str) -> Transaction:
    return Transaction(
        amount=transaction_data["amount"],
        category=transaction_data["category"],
        date=transaction_data["date"],
        description=transaction_data.get("description", ""),
        for_who=transaction_data.get("for_who", ""),
        transaction_direction=transaction_data["transaction_direction"],
        tran_type=transaction_data["tran_type"],
        user_id=uid,
        transaction_id=transaction_data.get("transaction_id"),
        internal_transfer=transaction_data.get("internal_transfer"),
    )


def _find_duplicate_transaction(
    uid: str,
    transaction: Mapping[str, Any],
    load_transactions: TransactionLoader,
) -> bool:
    fingerprint = _tx_fingerprint_for_matching(transaction)

    try:
        for existing_transaction in load_transactions(uid) or []:
            try:
                if _tx_fingerprint_for_matching(existing_transaction) == fingerprint:
                    logger.warning("Duplicate transaction detected for uid=%s, fp=%s", uid, fingerprint)
                    return True
            except Exception:
                continue
    except Exception as exc:
        logger.warning("Could not check for duplicates in put_transaction: %s", exc)

    return False


def _normalize_transaction_ids(request_body: Mapping[str, Any]) -> List[str]:
    transaction_ids = request_body.get("transaction_ids")
    if not transaction_ids:
        raise HTTPException(status_code=400, detail="transaction_ids is required and must be a non-empty array")
    if not isinstance(transaction_ids, list):
        raise HTTPException(status_code=400, detail="transaction_ids must be an array")
    if len(transaction_ids) == 0:
        raise HTTPException(status_code=400, detail="transaction_ids array cannot be empty")

    normalized_ids: List[str] = []
    for transaction_id in transaction_ids:
        if not transaction_id:
            continue

        if isinstance(transaction_id, str) and "/" in transaction_id:
            normalized_id = transaction_id.split("/")[-1]
        else:
            normalized_id = transaction_id

        if normalized_id:
            normalized_ids.append(str(normalized_id))

    return normalized_ids


def _fetch_existing_firestore_transactions(uid: str) -> List[TransactionDict]:
    try:
        db = get_db_client()
    except FirebaseUnavailable as exc:
        logger.error("Firebase unavailable in mass_import_transactions for uid=%s: %s", uid, exc)
        raise HTTPException(status_code=503, detail=f"Firebase unavailable, mass import aborted: {exc}")

    try:
        docs = db.collection("users").document(uid).collection("transactions").stream()
        return [
            transaction
            for transaction in (doc.to_dict() | {"transaction_id": doc.id} for doc in docs)
            if firebase_client.is_current_transaction_schema(transaction)
        ]
    except Exception as exc:
        logger.exception("Failed to fetch existing Firestore transactions for uid=%s", uid)
        raise HTTPException(status_code=500, detail=f"Could not read existing transactions from Firestore: {exc}")


def _collect_fingerprints(transactions: List[Mapping[str, Any]]) -> Set[str]:
    fingerprints: Set[str] = set()
    for transaction in transactions:
        try:
            fingerprints.add(_tx_fingerprint_for_matching(transaction))
        except Exception:
            continue
    return fingerprints


def _determine_mass_import_status(imported_count: int, skipped_count: int, error_count: int) -> str:
    if not skipped_count and not error_count:
        return "success"
    if imported_count:
        return "partial_success"
    return "failed"


def delete_transactions_for_user(
    uid: str,
    request_body: Mapping[str, Any],
    delete_transactions: TransactionBatchDeleter = delete_user_transactions_batched,
) -> TransactionDict:
    normalized_ids = _normalize_transaction_ids(request_body)

    try:
        deleted_count = delete_transactions(uid, normalized_ids)
    except FirebaseUnavailable as exc:
        logger.error("Firebase unavailable in mass_delete_transactions for uid=%s: %s", uid, exc)
        raise HTTPException(status_code=503, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected error in mass_delete_transactions for uid=%s", uid)
        raise HTTPException(status_code=500, detail=f"Internal server error during deletion: {exc}")

    if deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No transactions found to delete. Attempted to delete {len(normalized_ids)} IDs.",
        )

    return {
        "success": True,
        "message": f"{deleted_count} transaction(s) deleted successfully",
        "deleted_count": deleted_count,
        "errors": None,
    }


def put_transaction_for_user(
    uid: str,
    transaction_data: Mapping[str, Any],
    load_transactions: TransactionLoader = get_user_transactions,
    save_transaction: TransactionSaver = save_user_transaction,
) -> TransactionDict:
    try:
        transaction = _build_transaction(transaction_data, uid)
        tx_dict = transaction.to_dict()

        if _find_duplicate_transaction(uid, tx_dict, load_transactions=load_transactions):
            return {
                "status": "warning",
                "message": "This transaction appears to be a duplicate of an existing transaction.",
                "duplicate_warning": True,
                "transaction": serialize_transaction_for_api(tx_dict),
            }

        doc_id = save_transaction(uid, tx_dict)
        tx_dict["transaction_id"] = doc_id
        return {"status": "success", "transaction": serialize_transaction_for_api(tx_dict)}
    except FirebaseUnavailable as exc:
        logger.error("Firebase unavailable in put_transaction: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


def mass_import_transactions_for_user(uid: str, transactions_data: Any) -> TransactionDict:
    rows = _normalize_input_to_dicts(transactions_data)
    transformed_rows = [transform_excel_row(row) for row in rows]

    imported_transactions: List[TransactionDict] = []
    errors: List[TransactionDict] = []
    skipped_duplicates: List[TransactionDict] = []
    existing_fingerprints = _collect_fingerprints(_fetch_existing_firestore_transactions(uid))
    new_fingerprints: Set[str] = set()

    for index, tx_data in enumerate(transformed_rows):
        try:
            fingerprint = _tx_fingerprint_for_matching(tx_data)

            if fingerprint in existing_fingerprints:
                skipped_duplicates.append(
                    {
                        "index": index,
                        "reason": "already_in_db",
                        "fingerprint": fingerprint,
                        "row": tx_data,
                    }
                )
                continue

            if fingerprint in new_fingerprints:
                skipped_duplicates.append(
                    {
                        "index": index,
                        "reason": "duplicate_in_upload",
                        "fingerprint": fingerprint,
                        "row": tx_data,
                    }
                )
                continue

            imported_transactions.append(_build_transaction(tx_data, uid).to_dict())
            new_fingerprints.add(fingerprint)
        except Exception as exc:
            errors.append({"index": index, "error": str(exc), "row": tx_data})

    if imported_transactions:
        try:
            save_user_transactions(uid, imported_transactions, allow_local_fallback=False)
        except FirebaseUnavailable as exc:
            logger.error("Firebase unavailable while saving mass import for uid=%s: %s", uid, exc)
            raise HTTPException(status_code=503, detail=f"Firebase unavailable while saving import: {exc}")
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Mentés sikertelen: {exc}")

    return _serialize_mass_import_response_for_api(
        {
            "status": _determine_mass_import_status(
                imported_count=len(imported_transactions),
                skipped_count=len(skipped_duplicates),
                error_count=len(errors),
            ),
            "imported_count": len(imported_transactions),
            "skipped_duplicates_count": len(skipped_duplicates),
            "skipped_duplicates": skipped_duplicates[:50],
            "failed_count": len(errors),
            "errors": errors,
        }
    )


async def predict_future_transactions_for_user(
    uid: str,
    load_transactions: TransactionLoader = get_user_transactions,
) -> ForecastResult:
    try:
        load_transactions(uid)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error fetching transactions: {exc}")

    try:
        pipeline = await _get_pipeline()
        result = cast(ForecastResult, await asyncio.to_thread(pipeline.run, uid=uid, plot=False, verbose=True))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Forecast pipeline error: {exc}")

    public_result: ForecastResult = {
        "status": result.get("status"),
        "data_source": result.get("data_source"),
        "history": result.get("history"),
        "forecast": result.get("forecast"),
        "ci": result.get("ci"),
        "metrics": result.get("metrics", {}),
    }
    return cast(ForecastResult, _sanitize_json_value(public_result))

