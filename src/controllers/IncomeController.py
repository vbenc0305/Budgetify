from src.DAO.DAOimpl import FirebaseDAO
from src.models.income import Income
from typing import List, Dict, Any


class IncomeController:
    """
    A IncomeController osztály kezeli a bevételi adatokat,
    beleértve a CRUD műveleteket, valamint az üzleti logikát.
    """

    def __init__(self, collection_name: str = "incomes"):
        """
        Inicializálja az IncomeController-t.

        Paraméterek:
            collection_name (str): Az adatbázis gyűjteményének neve (alapértelmezett "incomes").
        """
        self.dao = FirebaseDAO(collection_name)

    def create_income(self, income_data: Dict[str, float]) -> bool:
        """
        Új Income rekordot hoz létre az adatbázisban.

        Paraméterek:
            income_data (Dict[str, float]): A bevételi adatokat tartalmazó szótár.

        Visszatérési érték:
            bool: True, ha sikeresen létrejött a rekord, False egyébként.
        """
        income = Income(**income_data)  # Bevétel objektum létrehozása
        income_dict = income.to_dict()  # Átalakítjuk szótárrá
        return self.dao.create(income_dict)

    def read_income(self, income_id: str) -> Dict[str, Any]:
        """
        Lekérdez egy bevételt az adatbázisból az azonosító alapján.

        Paraméterek:
            income_id (str): Azonosító, amivel lekérdezzük a bevételt.

        Visszatérési érték:
            dict: A bevétel adatai szótár formájában.
        """
        return self.dao.read(income_id)

    def update_income(self, income_id: str, updated_data: Dict[str, float]) -> bool:
        """
        Frissít egy meglévő bevételt az adatbázisban.

        Paraméterek:
            income_id (str): Az azonosító, amely alapján frissíteni kell a rekordot.
            updated_data (Dict[str, float]): A frissítendő adatok.

        Visszatérési érték:
            bool: True, ha sikeres a frissítés, False egyébként.
        """
        return self.dao.update(income_id, updated_data)

    def delete_income(self, income_id: str) -> bool:
        """
        Töröl egy bevételt az adatbázisból az azonosító alapján.

        Paraméterek:
            income_id (str): Az azonosító, amely alapján törölni kell a rekordot.

        Visszatérési érték:
            bool: True, ha sikeresen törölve lett a rekord, False egyébként.
        """
        return self.dao.delete(income_id)

    def get_all_incomes(self) -> List[Dict[str, Any]]:
        """
        Lekérdezi az összes bevételt az adatbázisból.

        Visszatérési érték:
            List[Dict[str, Any]]: A bevételek listája szótáraként.
        """
        return self.dao.find_all()

    def count_incomes(self) -> int:
        """
        Lekérdezi az összes bevétel számát.

        Visszatérési érték:
            int: A bevételek száma.
        """
        return self.dao.count()
