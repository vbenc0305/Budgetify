from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any



def serialize_transaction_for_api(transaction: Mapping[str, Any]) -> dict[str, Any]:
    serialized = dict(transaction)
    serialized.pop("Transfer type", None)
    serialized.pop("transfer_type", None)
    serialized.setdefault("for_who", "")
    serialized.setdefault("transaction_direction", "")
    return serialized



def serialize_transactions_for_api(transactions: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    if not transactions:
        return []
    return [serialize_transaction_for_api(tx) for tx in transactions]

