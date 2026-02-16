"""DAOImpl.py"""
import uuid
import logging

logger = logging.getLogger(__name__)
logger.debug("src.DAO.DAOimpl module imported")

# Defer Firebase initialization to db.firebase_client to allow fast-fail and backoff behavior
from db import firebase_client
from db.firebase_client import FirebaseUnavailable

from typing import List, Dict, Any
from abc import ABC

from src.DAO.DAO import DAO
from src.models.usr_info import UsrInfo


# Avoid initializing firebase_admin at import time; use get_db_client() lazily instead

class FirebaseDAO(DAO, ABC):
    """
    Implementálja a DAO protokollt Firebase Firestore használatával.
    Ez az osztály biztosítja az adatbázis műveletek végrehajtását a Firestore adatbázison,
    beleértve az új rekordok létrehozását, lekérdezését, frissítését, törlését és összes rekord lekérését.
    """

    def __init__(self, collection_name: str):
        """
        Inicializálja a FirebaseDAO osztályt.

        Paraméterek:
            collection_name (str): Az adatbázis gyűjteménye, amelyben a rekordok tárolódnak.
        """
        self.collection_name = collection_name
        # self.collection will be resolved lazily via get_db_client when needed

    def _get_collection(self):
        try:
            db = firebase_client.get_db_client()
        except FirebaseUnavailable:
            logger.warning("_get_collection: Firebase unavailable; operations will fall back where supported")
            return None
        return db.collection(self.collection_name)

    def create(self, data: Dict[str, Any]) -> bool:
        try:
            collection = self._get_collection()
            if collection is None:
                # When Firebase is unavailable, perform the best-effort local fallback if possible
                logger.warning("create: Firebase unavailable - cannot create remote document")
                return False

            if collection.id=="user":
                # Az email cím a rekord azonosítója
                identifier = data.get("email")

                if not identifier:
                    raise ValueError("A rekordnak tartalmaznia kell egy email című azonosítót!")

                # A dokumentum azonosítója az email cím lesz
                doc_ref = collection.document(identifier).set(data)

                # Alapértelmezett UsrInfo létrehozása az új felhasználóhoz
                usr_info = UsrInfo(user_id=identifier)  # Alap adatokat hozunk létre
                users_coll = firebase_client.get_db_client().collection("usr_info")
                usr_info_ref = users_coll.document(identifier).set(usr_info.to_dict())
                return True



            elif collection.id == "transactions":

                # Ellenőrizzük, hogy az 'email' mező jelen van-e az adatokban

                user_id = data.get("user_id")

                if not user_id:
                    raise ValueError(
                        "A tranzakciónak tartalmaznia kell egy 'user_id' mezőt, amely a felhasználóra mutat!")

                # Létrehozzuk a felhasználóra mutató hivatkozást

                user_ref = firebase_client.get_db_client().collection("users").document(user_id)

                # Generálunk egy egyedi azonosítót a tranzakcióhoz

                transaction_id = str(uuid.uuid4())

                # Létrehozzuk a tranzakciót a felhasználó 'transactions' alkollekciójában

                user_ref.collection("transactions").document(transaction_id).set(data)

                return True
            elif collection.id == "usr_info":
                # Az email cím a rekord azonosítója
                identifier = data.get("email")

                user_ref = firebase_client.get_db_client().collection("usr_info").document(identifier)

                user_ref.collection("usr_info").document(identifier).set(data)
                return True

            else:
                raise ValueError(f"Ismeretlen gyűjtemény: {collection.id}")
        except FirebaseUnavailable:
            logger.warning("create: FirebaseUnavailable - falling back or returning failure quickly")
            return False
        except Exception as e:
            print(f"Error creating record: {e}")
            return False

    def read_user_transactions(self, uid:str | None=None) -> list[dict[str, Any] | None] | None:
        # If uid provided, attempt to read from Firestore; on FirebaseUnavailable return local stash if present
        if uid:
            try:
                collection = self._get_collection()
                if collection is None:
                    return None
                transactions_ref = collection.document(uid).collection("transactions")
                docs = transactions_ref.stream()
                return [doc.to_dict() for doc in docs]
            except FirebaseUnavailable:
                logger.warning("read_user_transactions: FirebaseUnavailable - returning None so caller can fallback")
                return None
            except Exception as e:
                logger.exception(f"read_user_transactions failed: {e}")
                return None
        else:
           return None

    def read(self, identifier: str) -> Dict[str, Any]:
        try:
            collection = self._get_collection()
            if collection is None:
                return {}
            doc_ref = collection.document(identifier)
            doc = doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            else:
                return {}
        except FirebaseUnavailable:
            logger.warning("read: FirebaseUnavailable - returning empty dict")
            return {}
        except Exception as e:
            print(f"Error reading record: {e}")
            return {}

    def update(self, identifier: str, data: Dict[str, Any]) -> bool:
        try:
            collection = self._get_collection()
            if collection is None:
                return False
            doc_ref = collection.document(identifier)
            doc_ref.update(data)
            return True
        except FirebaseUnavailable:
            logger.warning("update: FirebaseUnavailable - returning False")
            return False
        except Exception as e:
            print(f"Error updating record: {e}")
            return False

    def delete(self, identifier: str) -> bool:
        try:
            collection = self._get_collection()
            if collection is None:
                return False
            doc_ref = collection.document(identifier)
            doc_ref.delete()
            return True
        except FirebaseUnavailable:
            logger.warning("delete: FirebaseUnavailable - returning False")
            return False
        except Exception as e:
            print(f"Error deleting record: {e}")
            return False

    def find_all(self) -> List[Dict[str, Any]]:
        try:
            collection = self._get_collection()
            if collection is None:
                return []
            docs = collection.stream()
            return [doc.to_dict() for doc in docs]
        except FirebaseUnavailable:
            logger.warning("find_all: FirebaseUnavailable - returning empty list")
            return []
        except Exception as e:
            print(f"Error fetching all records: {e}")
            return []

    def count(self) -> int:
        try:
            collection = self._get_collection()
            if collection is None:
                return 0
            docs = collection.stream()
            return len(list(docs))
        except FirebaseUnavailable:
            logger.warning("count: FirebaseUnavailable - returning 0")
            return 0
        except Exception as e:
            print(f"Error counting records: {e}")
            return 0

    def user_exists(self, email: str) -> bool:
        """Ellenőrzi, hogy a felhasználó létezik-e az email alapján"""
        try:
            collection = self._get_collection()
            if collection is None:
                return False
            user_ref = collection.document(email)  # Itt már nem db-t használunk, hanem a self.collection-t
            doc = user_ref.get()

            # Ha a dokumentum létezik, visszatérünk True-val, különben False
            return doc.exists
        except FirebaseUnavailable:
            logger.warning("user_exists: FirebaseUnavailable - returning False")
            return False
        except Exception as e:
            print(f"Hiba történt a felhasználó ellenőrzése során: {e}")
            return False

    def get_user_info_by_email(self, email):
        try:
            users_coll = firebase_client.get_db_client().collection('usr_info')
            user_ref = users_coll.document(email)  # Az email azonosítja a felhasználót
            user_doc = user_ref.get()  # Lekérdezzük a dokumentumot

            if user_doc.exists:
                # Ha létezik a dokumentum, visszaadjuk az adatokat
                return user_doc.to_dict()  # A dokumentumból szótárt adunk vissza
            else:
                print("A felhasználó nem található.")
                return {}  # Ha a felhasználó nem található, üres szótárat adunk vissza
        except FirebaseUnavailable:
            logger.warning("get_user_info_by_email: FirebaseUnavailable - returning empty dict")
            return {}
        except Exception as e:
            print(f"Hiba történt a felhasználó adatainak lekérésekor: {e}")
            return {} #

    def get_user_by_email(self,email):
        try:
            users_coll = firebase_client.get_db_client().collection('user')
            user_ref = users_coll.document(email)
            user_doc = user_ref.get()
            if user_doc.exists:
                # Ha létezik a dokumentum, visszaadjuk az adatokat
                return user_doc.to_dict()  # A dokumentumból szótárt adunk vissza
            else:
                print("A felhasználó nem található.")
                return {}  # Ha a felhasználó nem található, üres szótárat adunk vissza
        except FirebaseUnavailable:
            logger.warning("get_user_by_email: FirebaseUnavailable - returning empty dict")
            return {}
        except Exception as e:
            print(f"Hiba történt a felhasználó adatainak lekérésekor: {e}")
            return {}

    def upload_transactions(self,
                            transactions: List[Dict[str, Any]],
                            user_id: str = None) -> int:
        if self.collection_name != "transactions":
            print("Hiba: Az upload_transactions metódus csak a 'transactions' kollekcióval működik.")
            return 0

        uploaded_count = 0
        for data in transactions:
            if user_id:
                data['user_id'] = user_id

            if 'user_id' not in data:
                print("FIGYELEM: Egy tranzakció kihagyva, mert hiányzik a user_id.")
                continue

            if self.create(data):
                uploaded_count += 1

        return uploaded_count

    def delete_all_user_transactions(self, user_id: str) -> int:
        if self.collection_name != "transactions":
            print("Hiba: A delete_all_user_transactions metódus csak a 'transactions' kollekcióval működik.")
            return 0

        try:
            docs = firebase_client.get_db_client().collection("users").document(user_id).collection("transactions").stream()
            deleted_count = 0
            for doc in docs:
                doc.reference.delete()
                deleted_count += 1

            return deleted_count

        except FirebaseUnavailable:
            logger.warning("delete_all_user_transactions: FirebaseUnavailable - returning 0")
            return 0
        except Exception as e:
            print(f"Hiba történt a törlés során a(z) {user_id} felhasználónál: {e}")
            return 0

    def check_quota_status(self) -> dict:
        """
        Check the quota status of the Firebase database.
        Returns a dictionary with the quota status, e.g., {"quota_reached": True/False}.
        """
        try:
            db = firebase_client.get_db_client()
            # Example: Check a lightweight document for quota status
            quota_doc = db.collection("quota_status").document("status").get()
            if quota_doc.exists:
                return quota_doc.to_dict()
            else:
                return {"quota_reached": False}  # Default to False if no status document exists
        except FirebaseUnavailable:
            logger.warning("check_quota_status: Firebase unavailable; assuming quota reached")
            return {"quota_reached": True}  # Assume quota is reached if Firebase is unavailable
        except Exception as e:
            logger.error(f"check_quota_status: Unexpected error: {e}")
            return {"quota_reached": True}  # Assume quota is reached on unexpected errors

