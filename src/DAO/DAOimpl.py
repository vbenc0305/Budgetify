"""DAOImpl.py"""
import os

import firebase_admin
from firebase_admin import credentials, firestore
from typing import List, Dict, Any
from abc import ABC

from src.DAO.DAO import DAO

# Firebase inicializálása
cred = credentials.Certificate(os.path.join(os.path.dirname(__file__), '..', 'conn', 'conninfo.json'))
firebase_admin.initialize_app(cred)

# Firestore referencia
db = firestore.client()

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
        self.collection = db.collection(collection_name)

    def create(self, data: Dict[str, Any]) -> bool:
        """
        Új rekord létrehozása az adatbázisban.

        Paraméterek:
            data (Dict[str, Any]): A rekordot tartalmazó adatokat, amelyek tárolásra kerülnek.

        Visszatérési érték:
            bool: Ha a rekord sikeresen létrejött, akkor True, egyébként False.
        """
        try:
            # Először próbáljuk meg a company_id-t, ha nem létezik, akkor egy másik egyedi azonosítót használunk
            identifier = data.get("company_id") or data.get("email") or data.get("uid")

            if not identifier:
                raise ValueError(
                    "A rekordnak tartalmaznia kell egy egyedi azonosítót (pl. company_id, email vagy uid)!")

            # A dokumentum azonosítója az azonosító, legyen az company_id, email vagy uid
            doc_ref = self.collection.document(identifier).set(data)
            return True
        except Exception as e:
            print(f"Error creating record: {e}")
            return False

    def read(self, identifier: str) -> Dict[str, Any]:
        """
        Egy rekord lekérdezése az adatbázisból.

        Paraméterek:
            identifier (str): Az azonosító (pl. rekord ID), amely alapján lekérdezzük az adatot.

        Visszatérési érték:
            Dict[str, Any]: A lekérdezett rekord adatai egy szótár formájában.
        """
        try:
            doc_ref = self.collection.document(identifier)
            doc = doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            else:
                return {}
        except Exception as e:
            print(f"Error reading record: {e}")
            return {}

    def update(self, identifier: str, data: Dict[str, Any]) -> bool:
        """
        Egy rekord frissítése az adatbázisban.

        Paraméterek:
            identifier (str): Az azonosító (pl. rekord ID), amely alapján frissíteni kell a rekordot.
            data (Dict[str, Any]): Az új adatokat, amelyekkel frissíteni kell a rekordot.

        Visszatérési érték:
            bool: Ha a rekord sikeresen frissült, akkor True, egyébként False.
        """
        try:
            doc_ref = self.collection.document(identifier)
            doc_ref.update(data)
            return True
        except Exception as e:
            print(f"Error updating record: {e}")
            return False

    def delete(self, identifier: str) -> bool:
        """
        Egy rekord törlése az adatbázisból.

        Paraméterek:
            identifier (str): Az azonosító (pl. rekord ID), amely alapján töröljük a rekordot.

        Visszatérési érték:
            bool: Ha a rekord sikeresen törlődött, akkor True, egyébként False.
        """
        try:
            doc_ref = self.collection.document(identifier)
            doc_ref.delete()
            return True
        except Exception as e:
            print(f"Error deleting record: {e}")
            return False

    def find_all(self) -> List[Dict[str, Any]]:
        """
        Az összes rekord lekérdezése az adatbázisból.

        Visszatérési érték:
            List[Dict[str, Any]]: Az összes rekord adatai egy listában, ahol minden rekord egy szótár.
        """
        try:
            docs = self.collection.stream()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            print(f"Error fetching all records: {e}")
            return []

    def count(self) -> int:
        """
        Az összes rekord számának lekérdezése az adatbázisból.

        Visszatérési érték:
            int: A rekordok száma.
        """
        try:
            docs = self.collection.stream()
            return len(list(docs))
        except Exception as e:
            print(f"Error counting records: {e}")
            return 0

    def user_exists(self, email: str) -> bool:
        """Ellenőrzi, hogy a felhasználó létezik-e az email alapján"""
        try:
            # A 'users' gyűjteményből lekérjük az adott emaillel rendelkező dokumentumot
            user_ref = self.collection.document(email)  # Itt már nem db-t használunk, hanem a self.collection-t
            doc = user_ref.get()

            # Ha a dokumentum létezik, visszatérünk True-val, különben False
            return doc.exists
        except Exception as e:
            print(f"Hiba történt a felhasználó ellenőrzése során: {e}")
            return False

    def get_user_password(self, email):
        """Lekérdezi a felhasználó jelszavának hashelt változatát az email alapján"""
        try:
            # Lekérdezzük a felhasználót az email alapján
            user_query = self.collection.where("email", "==", email).limit(1).stream()

            for user in user_query:
                return user.to_dict().get("password")  # Visszaadjuk a hashelt jelszót

            return None  # Ha nincs ilyen email cím, None-t adunk vissza

        except Exception as e:
            print(f"Hiba történt a jelszó lekérdezése közben: {e}")
            return None

