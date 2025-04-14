"""dao.py"""

from typing import Protocol, Any, List, Dict


class DAO(Protocol):
    """
    Az adatbázis műveletek végzésére szolgáló DAO interfész.
    Ez az interfész meghatározza az alapvető CRUD műveleteket,
    amelyeket minden adatkezelő osztálynak implementálnia kell.

    A CRUD műveletek a következők:
    - Create (létrehozás)
    - Read (lekérdezés)
    - Update (frissítés)
    - Delete (törlés)
    """

    def get_user_info_by_email(self, email):
        """
        Lekérdezi a felhasználó információit az e-mail cím alapján.

        Paraméterek:
            email (str): A felhasználó e-mail címe.

        Visszatérési érték:
            dict[str, Any]: A felhasználó információi egy szótárban.
        """
        ...

    def get_user_by_email(self, email):
        """
        Lekérdezi a felhasználó adatait az e-mail cím alapján.

        Paraméterek:
            email (str): A felhasználó e-mail címe.

        Visszatérési érték:
            dict[str, Any]: A felhasználó adatai egy szótárban.
        """
        ...

    def user_exists(self, email: str) -> bool:
        """
        Ellenőrzi, hogy a felhasználó létezik-e az adatbázisban.

        Paraméterek:
            email (str): A felhasználó e-mail címe.

        Visszatérési érték:
            bool: True, ha a felhasználó létezik, egyébként False.
        """
        ...

    def read_user_transactions(self, identifier=None) -> List[Dict[str, Any]]:
        """
        Felhasználói tranzakciók lekérdezése.

        Paraméterek:
            identifier (str, opcional): Az azonosító (pl. felhasználó ID), amely alapján lekérdezzük a tranzakciókat.
                                        Ha None, akkor az összes tranzakciót visszaadja.

        Visszatérési érték:
            list[dict[str, Any]]: A lekérdezett tranzakciók adatai egy listában, ahol minden tranzakció egy szótár.
        """
        ...

    def create(self, data: dict[str, Any]) -> bool:
        """
        Új rekord létrehozása az adatbázisban.

        Paraméterek:
            data (dict[str, Any]): A rekordot tartalmazó adatokat, amelyek tárolásra kerülnek.

        Visszatérési érték:
            bool: Ha a rekord sikeresen létrejött, akkor True, egyébként False.
        """
        ...

    def read(self, identifier: str) -> dict[str, Any]:
        """
        Egy rekord lekérdezése az adatbázisból az azonosító alapján.

        Paraméterek:
            identifier (str): Az azonosító (pl. rekord ID), amely alapján lekérdezzük az adatot.

        Visszatérési érték:
            dict[str, Any]: A lekérdezett rekord adatai egy szótár formájában.
        """
        ...

    def update(self, identifier: str, data: dict[str, Any]) -> bool:
        """
        Egy rekord frissítése az adatbázisban.

        Paraméterek:
            identifier (str): Az azonosító (pl. rekord ID), amely alapján frissíteni kell a rekordot.
            data (dict[str, Any]): Az új adatokat, amelyekkel frissíteni kell a rekordot.

        Visszatérési érték:
            bool: Ha a rekord sikeresen frissült, akkor True, egyébként False.
        """
        ...

    def delete(self, identifier: str) -> bool:
        """
        Egy rekord törlése az adatbázisból az azonosító alapján.

        Paraméterek:
            identifier (str): Az azonosító (pl. rekord ID), amely alapján töröljük a rekordot.

        Visszatérési érték:
            bool: Ha a rekord sikeresen törlődött, akkor True, egyébként False.
        """
        ...

    def find_all(self) -> list[dict[str, Any]]:
        """
        Az összes rekord lekérdezése az adatbázisból.

        Visszatérési érték:
            list[dict[str, Any]]: Az összes rekord adatai egy listában, ahol minden rekord egy szótár.
        """
        ...

    def count(self) -> int:
        """
        Az összes rekord számának lekérdezése az adatbázisból.

        Visszatérési érték:
            int: A rekordok száma.
        """
        ...
