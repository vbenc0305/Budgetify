"""StatisticsController.py"""

from src.models.statistics import Statistics
from src.DAO.DAOimpl import FirebaseDAO
from src.models.income import Income
from src.models.spending import Spending


class StatisticsController:
    """
    A StatisticsController osztály felelős a statisztikai műveletek kezeléséért.
    Itt történnek a statisztikák lekérdezései, frissítései és létrehozása.
    """

    def __init__(self, dao: FirebaseDAO):
        """
        Inicializálja a StatisticsController osztályt.

        Args:
            dao (FirebaseDAO): A DAO osztály példánya, amely az adatbázissal kommunikál.
        """
        self.dao = dao

    def get_statistics(self, user_id: str) -> Statistics:
        """
        Lekérdezi a statisztikákat a megadott felhasználó azonosítója alapján.

        Args:
            user_id (str): A felhasználó egyedi azonosítója.

        Return:
            Statistics: A felhasználó statisztikai adatainak objektuma.

        Raise:
            ValueError: Ha nem található statisztika a megadott felhasználóhoz.
        """
        stats_data = self.dao.read(user_id)
        if not stats_data:
            raise ValueError(f"Statisztikai adat nem található a felhasználóhoz: {user_id}")

        income_data = Income(**stats_data['income'])  # Feltételezzük, hogy az Income is egy osztály
        spending_data = Spending(**stats_data['spending'])  # Ugyanez a Spending-re
        return Statistics(stats_data['stat_id'], income_data, spending_data, stats_data['user_id'])

    def create_statistics(self, user_id: str, income: Income, spending: Spending) -> bool:
        """
        Létrehoz egy új statisztikai rekordot a megadott felhasználó számára.

        Args:
            user_id (str): A felhasználó egyedi azonosítója.
            income (Income): Az Income objektum, amely tartalmazza a bevételi adatokat.
            spending (Spending): A Spending objektum, amely tartalmazza a kiadási adatokat.

        Return:
            bool: Ha sikerült létrehozni a statisztikát, True, egyébként False.
        """
        stat_id = f"stat_{user_id}"  # Példa statisztikai azonosító generálása
        data = {
            'stat_id': stat_id,
            'user_id': user_id,
            'income': income.to_dict(),  # Feltételezve, hogy az Income és Spending rendelkeznek to_dict metódussal
            'spending': spending.to_dict()
        }
        return self.dao.create(data)

    def update_statistics(self, stat_id: str, income: Income = None, spending: Spending = None) -> bool:
        """
        Frissíti a meglévő statisztikai rekordot a megadott statisztikai azonosító alapján.

        Args:
            stat_id (str): A statisztikai rekord azonosítója.
            income (Income): Az új bevételi adatok, ha vannak.
            spending (Spending): Az új kiadási adatok, ha vannak.

        Return:
            bool: Ha sikerült frissíteni a statisztikát, True, egyébként False.
        """
        data = {}
        if income:
            data['income'] = income.to_dict()
        if spending:
            data['spending'] = spending.to_dict()

        return self.dao.update(stat_id, data)

    def delete_statistics(self, stat_id: str) -> bool:
        """
        Törli a statisztikai rekordot a megadott statisztikai azonosító alapján.

        Args:
            stat_id (str): A statisztikai rekord azonosítója.

        Return:
            bool: Ha sikerült törölni a statisztikát, True, egyébként False.
        """
        return self.dao.delete(stat_id)
