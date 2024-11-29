"""SpendingController.py"""

from src.DAO.DAOimpl import FirebaseDAO
from src.models.spending import Spending
from typing import List, Dict, Any


class SpendingController:
    """
    A SpendingController osztály kezeli a kiadási adatokat,
    beleértve a CRUD műveleteket, valamint az üzleti logikát.
    """

    def __init__(self, collection_name: str = "spendings"):
        """
        Inicializálja a SpendingController-t.

        Paraméterek:
            collection_name (str): Az adatbázis gyűjteményének neve (alapértelmezett "spendings").
        """
        self.dao = FirebaseDAO(collection_name)

    def create_spending(self, spending_data: Dict[str, float]) -> bool:
        """
        Új Spending rekordot hoz létre az adatbázisban.

        Paraméterek:
            spending_data (Dict[str, float]): A kiadás adatokat tartalmazó szótár.

        Visszatérési érték:
            bool: True, ha sikeresen létrejött a rekord, False egyébként.
        """
        spending = Spending(**spending_data)  # Kiadás objektum létrehozása
        spending_dict = spending.to_dict()  # Átalakítjuk szótárrá
        return self.dao.create(spending_dict)

    def read_spending(self, spending_id: str) -> Dict[str, Any]:
        """
        Lekérdez egy kiadást az adatbázisból az azonosító alapján.

        Paraméterek:
            spending_id (str): Azonosító, amivel lekérdezzük a kiadást.

        Visszatérési érték:
            dict: A kiadás adatai szótár formájában.
        """
        return self.dao.read(spending_id)

    def update_spending(self, spending_id: str, updated_data: Dict[str, float]) -> bool:
        """
        Frissít egy meglévő kiadást az adatbázisban.

        Paraméterek:
            spending_id (str): Az azonosító, amely alapján frissíteni kell a rekordot.
            updated_data (Dict[str, float]): A frissítendő adatok.

        Visszatérési érték:
            bool: True, ha sikeres a frissítés, False egyébként.
        """
        return self.dao.update(spending_id, updated_data)

    def delete_spending(self, spending_id: str) -> bool:
        """
        Töröl egy kiadást az adatbázisból az azonosító alapján.

        Paraméterek:
            spending_id (str): Az azonosító, amely alapján törölni kell a rekordot.

        Visszatérési érték:
            bool: True, ha sikeresen törölve lett a rekord, False egyébként.
        """
        return self.dao.delete(spending_id)

    def get_all_spendings(self) -> List[Dict[str, Any]]:
        """
        Lekérdezi az összes kiadást az adatbázisból.

        Visszatérési érték:
            List[Dict[str, Any]]: A kiadások listája szótáraként.
        """
        return self.dao.find_all()

    def count_spendings(self) -> int:
        """
        Lekérdezi az összes kiadás számát.

        Visszatérési érték:
            int: A kiadások száma.
        """
        return self.dao.count()
