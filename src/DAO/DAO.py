"""dao.py"""

from typing import Protocol, Any


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
