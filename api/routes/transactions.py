from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from starlette.responses import JSONResponse

from api.dependencies import get_current_user_uid
from api.helpers.transaction_helpers import (
    _tx_fingerprint_for_matching,
    classify_internal_transfer,
    transform_excel_row,
)
from api.services.transactions_service import (
    _get_pipeline,
    delete_transactions_for_user,
    mass_import_transactions_for_user,
    predict_future_transactions_for_user,
    put_transaction_for_user,
)
from api.transaction_payloads import serialize_transactions_for_api
from db.firebase_client import (
    FirebaseUnavailable,
    delete_user_transactions_batched,
    get_user_transactions,
    save_user_transaction,
)

logger = logging.getLogger(__name__)
logger.debug("api.routes.transactions imported")

router = APIRouter()

# Compatibility exports used by existing tests and callers.
__all__ = [
    "router",
    "_get_pipeline",
    "classify_internal_transfer",
    "transform_excel_row",
    "_tx_fingerprint_for_matching",
]


@router.get("/transactions")
async def get_transactions(uid: str = Depends(get_current_user_uid)):
    try:
        return serialize_transactions_for_api(get_user_transactions(uid))
    except FirebaseUnavailable as exc:
        logger.error("Firebase unavailable in get_transactions: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc))


@router.delete("/transactions/mass_delete")
async def mass_delete_transactions(
    request_body: dict = Body(...),
    uid: str = Depends(get_current_user_uid),
):
    return delete_transactions_for_user(
        uid=uid,
        request_body=request_body,
        delete_transactions=delete_user_transactions_batched,
    )


@router.put("/transactions")
async def put_transaction(
    transaction_data: dict = Body(...),
    uid: str = Depends(get_current_user_uid),
):
    return put_transaction_for_user(
        uid=uid,
        transaction_data=transaction_data,
        load_transactions=get_user_transactions,
        save_transaction=save_user_transaction,
    )


@router.post("/transactions/mass_import")
async def mass_import_transactions(
    transactions_data: Any = Body(...),
    uid: str = Depends(get_current_user_uid),
):
    return mass_import_transactions_for_user(uid=uid, transactions_data=transactions_data)


@router.get("/predict/transactions", response_class=JSONResponse)
async def predict_future_transactions(uid: str = Depends(get_current_user_uid)):
    payload = await predict_future_transactions_for_user(
        uid=uid,
        load_transactions=get_user_transactions,
    )
    return JSONResponse(content=payload)
