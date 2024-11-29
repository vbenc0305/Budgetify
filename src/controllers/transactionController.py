"""transcationController.py"""
from src.models.transactions import Transaction
from src.DAO.DAOimpl import FirebaseDAO

class TransactionController:
    """
    A TransactionController kezeli a tranzakciókat.
    CRUD műveleteket biztosít tranzakciók létrehozására, lekérdezésére, frissítésére és törlésére.
    """

    def __init__(self, user_id: str):
        """
        Inicializálja a TransactionController osztályt a megadott felhasználó számára.

        Args:
            user_id (str): A felhasználó azonosítója.
        """
        self.user_id = user_id
        self.dao = FirebaseDAO("transactions")

    def create_transaction(self, amount: float, category: str, date: str, description: str,tran_type:str,userid:str,for_who:str) -> bool:
        """
        Létrehoz egy új tranzakciót.

        Args:
            amount (float): A tranzakció összege.
            category (str): A tranzakció kategóriája (pl. étkezés, szórakozás).
            date (str): A tranzakció dátuma.
            description (str): Rövid leírás a tranzakcióról.

        Return:
            bool: True, ha a tranzakció sikeresen létrejött, False, ha hiba történt.
            :param date: Tranzakcio datuma
            :param category: Tranzakcio kategoriaja
            :param amount: Tranzakcio mennyisége
            :param description: a tranzakcio leirasa
            :param for_who: Kinek szol a tranzakcio
            :param userid: melyik felh-hoz tartozik a tranzakcio
            :param tran_type: Milyen tipusu a tranzakcio
        """
        transaction = Transaction( amount, category, date, description,tran_type, for_who, userid)
        success = self.dao.create(transaction.to_dict())
        return success

    def get_transactions(self) -> list:
        """
        Visszaadja az összes tranzakciót a felhasználó számára.

        Return:
            list: A felhasználó tranzakciói.
        """
        data = self.dao.read(self.user_id)
        if isinstance(data, dict):
            # Ha a data egy szótár, akkor konvertáljuk listává
            return [Transaction(**item) for item in data.values()]
        return []

    def get_transaction_by_id(self, transaction_id: str) -> Transaction:
        """
        Lekérdezi a tranzakciót a megadott azonosító alapján.

        Args:
            transaction_id (str): A tranzakció azonosítója.

        Return:
            Transaction: A lekérdezett tranzakció.

        Raise:
            ValueError: Ha nem található a tranzakció az adott azonosítóval.
        """
        transaction_data = self.dao.read(transaction_id)
        if transaction_data:
            return Transaction(**transaction_data)
        else:
            raise ValueError(f"A tranzakció nem található a következő azonosítóval: {transaction_id}")

    def update_transaction(self, transaction_id: str, amount: float = None, category: str = None,
                           date: str = None, description: str = None) -> bool:
        """
        Frissíti a tranzakciót a megadott paraméterek alapján.

        Args:
            transaction_id (str): A tranzakció azonosítója.
            amount (float, optional): A frissített tranzakció összege.
            category (str, optional): A frissített tranzakció kategóriája.
            date (str, optional): A frissített tranzakció dátuma.
            description (str, optional): A frissített tranzakció leírása.

        Return:
            bool: True, ha a tranzakció sikeresen frissült, False, ha hiba történt.
        """
        transaction_data = self.dao.read(transaction_id)
        if transaction_data:
            if amount:
                transaction_data['amount'] = amount
            if category:
                transaction_data['category'] = category
            if date:
                transaction_data['date'] = date
            if description:
                transaction_data['description'] = description
            success = self.dao.update(transaction_id, transaction_data)
            return success
        return False

    def delete_transaction(self, transaction_id: str) -> bool:
        """
        Törli a tranzakciót a megadott azonosító alapján.

        Args:
            transaction_id (str): A törlendő tranzakció azonosítója.

        Return:
            bool: True, ha a tranzakció sikeresen törlésre került, False, ha hiba történt.
        """
        success = self.dao.delete(transaction_id)
        return success
