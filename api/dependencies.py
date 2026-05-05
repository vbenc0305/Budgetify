# app/api/dependencies.py
from fastapi import HTTPException, Header
import firebase_admin
from firebase_admin import auth
from firebase_admin import credentials
import threading
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
logger.debug("api.dependencies imported")

_cred_path = "conninfo.json"
_init_lock = threading.Lock()
_token_clock_skew_seconds = 60


def ensure_firebase_initialized():
    """Initialize firebase_admin once in a thread-safe manner. Raises RuntimeError on failure."""
    if firebase_admin._apps:
        logger.debug("firebase already initialized (api.dependencies)")
        return
    with _init_lock:
        if firebase_admin._apps:
            logger.debug("firebase already initialized (api.dependencies inside lock)")
            return
        try:
            logger.info(f"Initializing Firebase Admin SDK from api.dependencies with cred {_cred_path}")
            cred = credentials.Certificate(_cred_path)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin initialized (api.dependencies)")
        except Exception as e:
            logger.exception("Failed to initialize Firebase Admin SDK (api.dependencies)")
            raise RuntimeError(f"Failed to initialize Firebase Admin SDK: {e}") from e


async def get_current_user_uid(authorization: str = Header(...)):
    """
    Ellenőrzi a frontend által küldött Firebase ID tokent.
    Visszaadja a UID-t, ha érvényes.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    id_token = authorization.split("Bearer ")[1]

    try:
        # Ensure SDK initialized lazily (not on import)
        ensure_firebase_initialized()
        # Allow a small clock skew to avoid 1-2 second "token used too early" race conditions.
        decoded_token = auth.verify_id_token(
            id_token,
            clock_skew_seconds=_token_clock_skew_seconds,
        )
        uid = decoded_token.get("uid")
        if not uid:
            raise HTTPException(status_code=401, detail="UID not found in token")
        return uid
    except HTTPException:
        raise
    except Exception as e:
        if "Token used too early" in str(e):
            logger.warning(
                "Token rejected as too early even with clock skew tolerance. server_utc=%s, err=%s",
                datetime.now(timezone.utc).isoformat(),
                str(e),
            )
            raise HTTPException(
                status_code=401,
                detail="Token not yet valid. Please retry in a few seconds and verify your device clock.",
            )
        logger.exception("Token verification failed")
        raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")
