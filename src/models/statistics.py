"""statistics.py"""
from income import Income
from spending import Spending

class Statistics:
    """
    A Statistics osztály a felhasználó kiadási és bevételi statisztikáit reprezentálja.
    """

    def __init__(self, stat_id: str, income: Income, spending: Spending, user_id: str):
        """
        Inicializálja a statisztikai adatokat.

        Args:
            stat_id (str): A statisztikai rekord azonosítója.
            income (Income): Az Income objektum.
            spending (Spending): A Spending objektum.
            user_id (str): A felhasználó egyedi azonosítója.
        """
        self._stat_id = stat_id
        self._income = income
        self._spending = spending
        self._user_id = user_id

    @property
    def stat_id(self):
        """Visszaadja a statisztikai rekord azonosítóját."""
        return self._stat_id

    @stat_id.setter
    def stat_id(self, value: str):
        """Beállítja a statisztikai rekord azonosítóját."""
        if not value:
            raise ValueError("Az azonosító nem lehet üres.")
        self._stat_id = value

    @property
    def income(self):
        """Visszaadja az Income objektumot."""
        return self._income

    @income.setter
    def income(self, value: Income):
        """Beállítja az Income objektumot."""
        if not isinstance(value, Income):
            raise TypeError("Az income attribútum csak Income típusú lehet.")
        self._income = value

    @property
    def spending(self):
        """Visszaadja a Spending objektumot."""
        return self._spending

    @spending.setter
    def spending(self, value: Spending):
        """Beállítja a Spending objektumot."""
        if not isinstance(value, Spending):
            raise TypeError("A spending attribútum csak Spending típusú lehet.")
        self._spending = value

    @property
    def user_id(self):
        """Visszaadja a felhasználó azonosítóját."""
        return self._user_id

    @user_id.setter
    def user_id(self, value: str):
        """Beállítja a felhasználó azonosítóját."""
        if not value:
            raise ValueError("A felhasználó azonosítója nem lehet üres.")
        self._user_id = value
