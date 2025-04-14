"""DAOImpl.py"""
import os
import uuid

import firebase_admin
from firebase_admin import credentials, firestore
from typing import List, Dict, Any
from abc import ABC

from src.DAO.DAO import DAO
from src.models.usr_info import UsrInfo

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
            if self.collection.id=="user":
                # Az email cím a rekord azonosítója
                identifier = data.get("email")

                if not identifier:
                    raise ValueError("A rekordnak tartalmaznia kell egy email című azonosítót!")

                # A dokumentum azonosítója az email cím lesz
                doc_ref = self.collection.document(identifier).set(data)

                # Alapértelmezett UsrInfo létrehozása az új felhasználóhoz
                usr_info = UsrInfo(user_id=identifier)  # Alap adatokat hozunk létre
                self.collection=db.collection("usr_info")
                usr_info_ref = self.collection.document(identifier).set(usr_info.to_dict())
                self.collection=db.collection("user")
                return True



            elif self.collection.id == "transactions":

                # Ellenőrizzük, hogy az 'email' mező jelen van-e az adatokban

                user_email = data.get("email")

                if not user_email:
                    raise ValueError(
                        "A tranzakciónak tartalmaznia kell egy 'email' mezőt, amely a felhasználóra mutat!")

                # Létrehozzuk a felhasználóra mutató hivatkozást

                user_ref = db.collection("user").document(user_email)

                # Generálunk egy egyedi azonosítót a tranzakcióhoz

                transaction_id = str(uuid.uuid4())

                # Létrehozzuk a tranzakciót a felhasználó 'transactions' alkollekciójában

                user_ref.collection("transactions").document(transaction_id).set(data)

                return True
            elif self.collection.id == "usr_info":
                # Az email cím a rekord azonosítója
                identifier = data.get("email")

                user_ref = db.collection("usr_info").document(identifier)

                user_ref.collection("usr_info").document(identifier).set(data)
                return True

            else:
                raise ValueError(f"Ismeretlen gyűjtemény: {self.collection.id}")
        except Exception as e:
            print(f"Error creating record: {e}")
            return False

    def read_user_transactions(self, identifier=None) -> List[Dict[str, Any]]:
        # Ha identifier (pl. email) van, akkor csak azokat a tranzakciókat kérjük le
        if identifier:
            # Az email alapján lekérjük az alkollekciót
            transactions_ref = self.collection.document(identifier).collection("transactions")
            docs = transactions_ref.stream()
            return [doc.to_dict() for doc in docs]
        else:
            # Ha nincs identifier, akkor az összes tranzakciót visszaadjuk
            docs = self.collection.stream()
            return [doc.to_dict() for doc in docs]

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

    def get_user_info_by_email(self, email):
        """
        Lekérdezi a felhasználó adatokat az email alapján.

        :param email: A felhasználó email címe.
        :return: Dict[str, Any] - A felhasználó adatait tartalmazó szótár.
        """
        try:
            self.collection=db.collection('usr_info')
            user_ref = self.collection.document(email)  # Az email azonosítja a felhasználót
            user_doc = user_ref.get()  # Lekérdezzük a dokumentumot

            if user_doc.exists:
                # Ha létezik a dokumentum, visszaadjuk az adatokat
                return user_doc.to_dict()  # A dokumentumból szótárt adunk vissza
            else:
                print("A felhasználó nem található.")
                return {}  # Ha a felhasználó nem található, üres szótárat adunk vissza
        except Exception as e:
            print(f"Hiba történt a felhasználó adatainak lekérésekor: {e}")
            return {} #

    def get_user_by_email(self,email):
        try:
            self.collection=db.collection('user')
            user_ref = self.collection.document(email)
            user_doc = user_ref.get()
            if user_doc.exists:
                # Ha létezik a dokumentum, visszaadjuk az adatokat
                return user_doc.to_dict()  # A dokumentumból szótárt adunk vissza
            else:
                print("A felhasználó nem található.")
                return {}  # Ha a felhasználó nem található, üres szótárat adunk vissza
        except Exception as e:
            print(f"Hiba történt a felhasználó adatainak lekérésekor: {e}")
            return {}  #