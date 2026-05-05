from fastapi import APIRouter, Depends, Body, HTTPException
from pydantic import BaseModel, ConfigDict, StrictBool, model_validator
from api.dependencies import get_current_user_uid
from db.firebase_client import get_user_doc, update_user_doc, get_usr_info_doc, update_usr_info_doc, delete_user_account, FirebaseUnavailable
import logging

logger = logging.getLogger(__name__)
logger.debug("api.routes.profile imported")

router = APIRouter()


class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    anonymous_stats_consent: StrictBool | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_consent(cls, data):
        if isinstance(data, dict) and "anonymous_stats_consent" in data and data.get("anonymous_stats_consent") is None:
            raise ValueError("anonymous_stats_consent cannot be null")
        return data


class ProfileResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    anonymous_stats_consent: bool = False

@router.get("/profile")
async def get_profile(uid: str = Depends(get_current_user_uid)):
    try:
        user_doc = get_user_doc(uid)
        if not user_doc:
            return ProfileResponse().model_dump()
        user_doc.setdefault("anonymous_stats_consent", False)
        return ProfileResponse(**user_doc).model_dump()
    except FirebaseUnavailable as e:
        logger.error(f"Firebase unavailable in get_profile: {e}")
        raise HTTPException(status_code=503, detail=str(e))

@router.post("/profile")
async def update_profile(update_data: ProfileUpdateRequest = Body(...), uid: str = Depends(get_current_user_uid)):
    try:
        payload = update_data.model_dump(exclude_none=True)
        updated_doc = update_user_doc(uid, payload)
        if not updated_doc:
            return ProfileResponse().model_dump()
        updated_doc.setdefault("anonymous_stats_consent", False)
        return ProfileResponse(**updated_doc).model_dump()
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except FirebaseUnavailable as e:
        logger.error(f"Firebase unavailable in update_profile: {e}")
        raise HTTPException(status_code=503, detail=str(e))


@router.put("/usr_info/{id}")
async def update_usr_info(id: str, update_data: dict = Body(...), uid: str = Depends(get_current_user_uid)):
    try:
        # Ellenőrizzük, hogy létezik-e a dokumentum
        existing_doc = get_usr_info_doc(id)
        if not existing_doc:
            raise HTTPException(status_code=404, detail="usr_info not found")

        # Frissítés Firebase-ben
        updated_doc = update_usr_info_doc(id, update_data)
        return {"status": "success", "data": updated_doc}
    except FirebaseUnavailable as e:
        logger.error(f"Firebase unavailable in update_usr_info: {e}")
        raise HTTPException(status_code=503, detail=str(e))


@router.delete("/usr_info/{id}")
async def delete_usr_info(id: str, uid: str = Depends(get_current_user_uid)):
    try:
        requested_uid = (id or "").strip()
        if not requested_uid:
            raise HTTPException(status_code=400, detail="uid is required")

        if requested_uid != uid:
            raise HTTPException(status_code=403, detail="You can only delete your own user account")

        result = delete_user_account(requested_uid)
        return {"status": "success", "data": result}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FirebaseUnavailable as e:
        logger.error(f"Firebase unavailable in delete_usr_info: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in delete_usr_info")
        raise HTTPException(status_code=500, detail=f"Failed to delete user account: {e}")

