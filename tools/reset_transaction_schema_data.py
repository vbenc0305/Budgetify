from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.firebase_client import FETCH_MARKER_SUFFIX, USER_TX_DIR, get_db_client


BATCH_SIZE = 400


def clear_firestore_transactions() -> int:
    db = get_db_client()
    deleted = 0

    for user_doc in db.collection("users").stream():
        tx_docs = user_doc.reference.collection("transactions").stream()
        batch = db.batch()
        batch_count = 0

        for tx_doc in tx_docs:
            batch.delete(tx_doc.reference)
            batch_count += 1
            if batch_count >= BATCH_SIZE:
                batch.commit()
                deleted += batch_count
                batch = db.batch()
                batch_count = 0

        if batch_count:
            batch.commit()
            deleted += batch_count

    return deleted



def clear_local_transaction_cache() -> int:
    deleted = 0
    for path in USER_TX_DIR.iterdir():
        if not path.is_file():
            continue
        if path.suffix == ".jsonl" or path.name.endswith(FETCH_MARKER_SUFFIX):
            path.unlink(missing_ok=True)
            deleted += 1
    return deleted



def main() -> None:
    parser = argparse.ArgumentParser(
        description="Delete all transaction subcollections and local transaction caches before rehydrating fresh data."
    )
    parser.add_argument("--local-only", action="store_true", help="Only clear local JSONL and fetch-marker files.")
    parser.add_argument("--yes", action="store_true", help="Execute the deletion.")
    args = parser.parse_args()

    if not args.yes:
        raise SystemExit("Refusing to delete data without --yes.")

    firestore_deleted = 0
    if not args.local_only:
        firestore_deleted = clear_firestore_transactions()

    local_deleted = clear_local_transaction_cache()

    print(
        f"Reset complete. Firestore transactions deleted: {firestore_deleted}. Local cache files deleted: {local_deleted}."
    )


if __name__ == "__main__":
    main()

