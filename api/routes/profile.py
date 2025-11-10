from fastapi import APIRouter, Depends, Body, HTTPException
from api.dependencies import get_current_user_uid
from db.firebase_client import get_user_doc, update_user_doc, get_usr_info_doc, update_usr_info_doc

router = APIRouter()

@router.get("/profile")
async def get_profile(uid: str = Depends(get_current_user_uid)):
    user_doc = get_user_doc(uid)
    return user_doc or {}

@router.post("/profile")
async def update_profile(update_data: dict = Body(...), uid: str = Depends(get_current_user_uid)):
    updated_doc = update_user_doc(uid, update_data)
    return updated_doc


@router.put("/usr_info/{id}")
async def update_usr_info(id: str, update_data: dict = Body(...), uid: str = Depends(get_current_user_uid)):
    # Ellenőrizzük, hogy létezik-e a dokumentum
    existing_doc = get_usr_info_doc(id)
    if not existing_doc:
        raise HTTPException(status_code=404, detail="usr_info not found")

    # Frissítés Firebase-ben
    updated_doc = update_usr_info_doc(id, update_data)
    return {"status": "success", "data": updated_doc}