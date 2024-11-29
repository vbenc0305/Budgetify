"""Transactions.py"""

class Transaction:
    """
    A Transaction osztály egy pénzügyi tranzakció adatait reprezentálja.
    """

    def __init__(self,
                 amount: float,
                 category: str,
                 date: str,
                 description: str,
                 for_who: str,
                 tran_type: str,
                 user_id: str):
        """
        Inicializálja a tranzakció attribútumait.

        Args:
            amount (float): A tranzakció összege.
            category (str): A tranzakció kategóriája (pl. 'food').
            date (str): A tranzakció dátuma (ISO 8601 formátumban).
            description (str): A tranzakció leírása.
            for_who (str): Kinek vagy mire vonatkozik a tranzakció.
            tran_type (str): A tranzakció típusa ('incoming' vagy 'outgoing').
            user_id (str): A tranzakcióhoz tartozó felhasználó azonosítója.
        """
        self._amount = amount
        self._category = category
        self._date = date
        self._description = description
        self._for_who = for_who
        self._tran_type = tran_type
        self._user_id = user_id

    # Getterek és setterek az egyes attribútumokhoz
    @property
    def amount(self):
        """Visszaadja a tranzakció összegét."""
        return self._amount

    @amount.setter
    def amount(self, value: float):
        """Beállítja a tranzakció összegét."""
        if value < 0:
            raise ValueError("A tranzakció összege nem lehet negatív.")
        self._amount = value

    @property
    def category(self):
        """Visszaadja a tranzakció kategóriáját."""
        return self._category

    @category.setter
    def category(self, value: str):
        """Beállítja a tranzakció kategóriáját."""
        if not value:
            raise ValueError("A kategória nem lehet üres.")
        self._category = value

    @property
    def date(self):
        """Visszaadja a tranzakció dátumát."""
        return self._date

    @date.setter
    def date(self, value: str):
        """Beállítja a tranzakció dátumát."""
        if not value:
            raise ValueError("A dátum nem lehet üres.")
        self._date = value

    @property
    def description(self):
        """Visszaadja a tranzakció leírását."""
        return self._description

    @description.setter
    def description(self, value: str):
        """Beállítja a tranzakció leírását."""
        self._description = value

    @property
    def for_who(self):
        """Visszaadja, hogy a tranzakció kinek vagy mire vonatkozik."""
        return self._for_who

    @for_who.setter
    def for_who(self, value: str):
        """Beállítja, hogy a tranzakció kinek vagy mire vonatkozik."""
        self._for_who = value

    @property
    def tran_type(self):
        """Visszaadja a tranzakció típusát."""
        return self._tran_type

    @tran_type.setter
    def tran_type(self, value: str):
        """Beállítja a tranzakció típusát."""
        if value not in ["incoming", "outgoing"]:
            raise ValueError("A tranzakció típusa 'incoming' vagy 'outgoing' lehet.")
        self._tran_type = value

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


    def to_dict(self) -> dict:
        """
        Visszaadja a tranzakció adatainak szótár formátumát.

        Return:
            dict: A tranzakció adatait tartalmazó szótár.
        """
        return {
            'amount': self._amount,
            'category': self._category,
            'date': self._date,
            'description': self._description,
            'for_who': self._for_who,
            'tran_type': self._tran_type,
            'user_id': self._user_id
        }