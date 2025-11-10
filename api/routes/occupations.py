from fastapi import APIRouter, Body
from db.firebase_client import get_all_occupations, add_new_occupation

router = APIRouter()

@router.get("/occupations")
async def get_occupations():
    """Visszaadja a Firebase-ben tárolt összes foglalkozást (munkahelyet)."""
    # A get_all_occupations függvényt még létre kell hozni a db/firebase_client.py-ban!
    return get_all_occupations()

# Ezt a végpontot használhatnánk a jövőben, ha külön API-t akarnánk az új elem hozzáadására
@router.post("/occupations")
async def add_occupation(name: str = Body(..., embed=True)):
     """Hozzáad egy új foglalkozást a listához."""
     return add_new_occupation(name)

