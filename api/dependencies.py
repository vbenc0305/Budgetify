# app/api/dependencies.py
from fastapi import Depends, HTTPException, Header
import firebase_admin
from firebase_admin import auth

# Ellenőrizzük, hogy az admin SDK inicializálva legyen
if not firebase_admin._apps:
    from firebase_admin import credentials
    cred = credentials.Certificate("conninfo.json")
    firebase_admin.initialize_app(cred)

async def get_current_user_uid(authorization: str = Header(...)):
    """
    Ellenőrzi a frontend által küldött Firebase ID tokent.
    Visszaadja a UID-t, ha érvényes.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    id_token = authorization.split("Bearer ")[1]

    try:
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token.get("uid")
        if not uid:
            raise HTTPException(status_code=401, detail="UID not found in token")
        return uid
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")
