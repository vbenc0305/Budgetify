"""Transactions.py"""

from typing import Optional


class Transaction:
    """
    A Transaction osztály egy pénzügyi tranzakció adatait reprezentálja.
    """

    ALLOWED_INTERNAL_TRANSFER_VALUES = {None, "none", "jar_in", "jar_out", "rounding"}

    def __init__(self,
                 amount: float,
                 category: str,
                 date: str,
                 description: str,
                 for_who: str,
                 transaction_direction: str,
                 tran_type: str,
                 user_id: str,
                 transaction_id: Optional[str] = None,
                 internal_transfer: Optional[str] = None):
        """
        Inicializálja a tranzakció attribútumait.

        Args:
            amount (float): A tranzakció összege (negatív vagy pozitív is lehet, a banki export szerint).
            category (str): A tranzakció kategóriája (pl. 'food').
            date (str): A tranzakció dátuma (ISO 8601 formátumban, pl. "2025-06-02 01:48:16").
            description (str): A tranzakció leírása.
            for_who (str): A partner neve.
            transaction_direction (str): A tranzakció iránya a banki exportból ('Bejövő'/'Kimenő').
            tran_type (str): A tranzakció típusa (banki leírás/pl. 'VÁSÁRLÁS KÁRTYÁVAL').
            user_id (str): A tranzakcióhoz tartozó felhasználó azonosítója.
            transaction_id (Optional[str]): A tranzakció Firebase dokumentum azonosítója.
            internal_transfer (Optional[str]): Belső átvezetés jelölése: None/'none'/'jar_in'/'jar_out'/'rounding'
        """
        self._amount = amount
        self._category = category
        self._date = date
        self._description = description
        self._for_who = for_who
        self._transaction_direction = transaction_direction
        self._tran_type = tran_type
        self._user_id = user_id
        self._transaction_id = transaction_id
        self._internal_transfer = internal_transfer if internal_transfer in self.ALLOWED_INTERNAL_TRANSFER_VALUES else None

    # Getterek és setterek az egyes attribútumokhoz
    @property
    def amount(self) -> float:
        """Visszaadja a tranzakció összegét (negatív vagy pozitív)."""
        return self._amount

    @amount.setter
    def amount(self, value: float):
        """Beállítja a tranzakció összegét. Negatív érték engedélyezett (banki kiadások)."""
        try:
            self._amount = float(value)
        except (TypeError, ValueError):
            raise ValueError("Az összegnek számnak kell lennie.")

    @property
    def category(self) -> str:
        """Visszaadja a tranzakció kategóriáját."""
        return self._category

    @category.setter
    def category(self, value: str):
        """Beállítja a tranzakció kategóriáját."""
        if not value:
            raise ValueError("A kategória nem lehet üres.")
        self._category = value

    @property
    def date(self) -> str:
        """Visszaadja a tranzakció dátumát."""
        return self._date

    @date.setter
    def date(self, value: str):
        """Beállítja a tranzakció dátumát."""
        if not value:
            raise ValueError("A dátum nem lehet üres.")
        self._date = value

    @property
    def description(self) -> str:
        """Visszaadja a tranzakció leírását."""
        return self._description

    @description.setter
    def description(self, value: str):
        """Beállítja a tranzakció leírását."""
        self._description = value

    @property
    def for_who(self) -> str:
        """Visszaadja a partner nevét."""
        return self._for_who

    @for_who.setter
    def for_who(self, value: str):
        """Beállítja a partner nevét."""
        self._for_who = value

    @property
    def transaction_direction(self) -> str:
        """Visszaadja a tranzakció irányát (pl. 'Bejövő' vagy 'Kimenő')."""
        return self._transaction_direction

    @transaction_direction.setter
    def transaction_direction(self, value: str):
        """Beállítja a tranzakció irányát."""
        if value is None or str(value).strip() == "":
            raise ValueError("A transaction_direction nem lehet üres.")
        self._transaction_direction = value

    @property
    def tran_type(self) -> str:
        """Visszaadja a tranzakció típusát (banki leírás)."""
        return self._tran_type

    @tran_type.setter
    def tran_type(self, value: str):
        """Beállítja a tranzakció típusát. Elfogadunk tetszőleges nem üres stringet (banki Típus mező)."""
        if value is None or str(value).strip() == "":
            raise ValueError("A tranzakció típusa nem lehet üres.")
        self._tran_type = value

    @property
    def user_id(self) -> str:
        """Visszaadja a felhasználó azonosítóját."""
        return self._user_id

    @user_id.setter
    def user_id(self, value: str):
        """Beállítja a felhasználó azonosítóját."""
        if not value:
            raise ValueError("A felhasználó azonosítója nem lehet üres.")
        self._user_id = value

    @property
    def internal_transfer(self) -> Optional[str]:
        """
        Visszaadja az internal transfer jelölést:
        None / 'none' / 'jar_in' / 'jar_out' / 'rounding'
        """
        return self._internal_transfer

    @internal_transfer.setter
    def internal_transfer(self, value: Optional[str]):
        """Beállítja az internal_transfer mezőt, validálva az értéket."""
        if value not in self.ALLOWED_INTERNAL_TRANSFER_VALUES:
            raise ValueError(f"internal_transfer értéke csak a következők lehetnek: {self.ALLOWED_INTERNAL_TRANSFER_VALUES}")
        self._internal_transfer = value

    @property
    def transaction_id(self) -> Optional[str]:
        """Visszaadja a tranzakció Firebase dokumentum azonosítóját."""
        return self._transaction_id

    @transaction_id.setter
    def transaction_id(self, value: Optional[str]):
        """Beállítja a tranzakció Firebase dokumentum azonosítóját."""
        self._transaction_id = value

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
            'transaction_direction': self._transaction_direction,
            'tran_type': self._tran_type,
            'user_id': self._user_id,
            'internal_transfer': self._internal_transfer,
            'transaction_id': self._transaction_id
        }
