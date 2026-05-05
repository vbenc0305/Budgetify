from fastapi import APIRouter, Depends, HTTPException
import logging

from api.dependencies import get_current_user_uid
from db.firebase_client import FirebaseUnavailable, get_county_transactions as load_county_transactions

logger = logging.getLogger(__name__)
logger.debug("api.routes.stats imported")

router = APIRouter()


@router.get("/stats/counties/{county}/categories")
async def get_county_transactions(
    county: str,
    uid: str = Depends(get_current_user_uid),
):
    """Return transactions for all users whose county matches the path parameter."""
    if not (county or "").strip():
        raise HTTPException(status_code=400, detail="county path parameter is required")

    try:
        county_data = load_county_transactions(county)
        transactions = county_data.get("transactions", [])
        return {
            "county": county,
            "matched_users": county_data.get("matched_users", 0),
            "transaction_count": len(transactions),
            "transactions": transactions,
            "data_source": county_data.get("data_source", "firestore"),
        }
    except FirebaseUnavailable as e:
        logger.error(f"Firebase unavailable in get_county_transactions: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in get_county_transactions")
        raise HTTPException(status_code=500, detail=f"Failed to fetch county transactions: {e}")
