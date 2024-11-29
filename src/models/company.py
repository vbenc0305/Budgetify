"""company.py"""
class Company:


    """
    Company osztály, amely egy céget reprezentál az adatbázisból.
    Az osztály a következő attribútumokat kezeli:
    - Cég adatai (name, address, company_id)
    - Kapcsolattartási adatok (con_email, con_person, con_phone)
    """

    def __init__(self, name: str, address: str, company_id: str,
                 con_email: str, con_person: str, con_phone: str):
        """
        Inicializálja az osztály attribútumait.

        Args:
            name (str): A cég neve.
            address (str): A cég címe.
            company_id (str): A cég egyedi azonosítója.
            con_email (str): Kapcsolattartó e-mail címe.
            con_person (str): Kapcsolattartó neve.
            con_phone (str): Kapcsolattartó telefonszáma.
        """
        self._name = name
        self._address = address
        self._company_id = company_id
        self._con_email = con_email
        self._con_person = con_person
        self._con_phone = con_phone

    # name
    @property
    def name(self):
        """Visszaadja a cég nevét."""
        return self._name

    @name.setter
    def name(self, value: str):
        """
        Beállítja a cég nevét.

        Args:
            value (str): A név, amit be akarunk állítani.

        Raises:
            ValueError: Ha a név üres.
        """
        if not value:
            raise ValueError("A cég neve nem lehet üres.")
        self._name = value

    # address
    @property
    def address(self):
        """Visszaadja a cég címét."""
        return self._address

    @address.setter
    def address(self, value: str):
        """
        Beállítja a cég címét.

        Args:
            value (str): A cím, amit be akarunk állítani.
        """
        self._address = value

    # company_id
    @property
    def company_id(self):
        """Visszaadja a cég egyedi azonosítóját."""
        return self._company_id

    @company_id.setter
    def company_id(self, value: str):
        """
        Beállítja a cég egyedi azonosítóját.

        Args:
            value (str): Az azonosító, amit be akarunk állítani.

        Raises:
            ValueError: Ha az azonosító üres.
        """
        if not value:
            raise ValueError("A cég azonosítója nem lehet üres.")
        self._company_id = value

    # con_email
    @property
    def con_email(self):
        """Visszaadja a kapcsolattartó e-mail címét."""
        return self._con_email

    @con_email.setter
    def con_email(self, value: str):
        """
        Beállítja a kapcsolattartó e-mail címét.

        Args:
            value (str): Az e-mail cím, amit be akarunk állítani.

        Raises:
            ValueError: Ha az e-mail cím érvénytelen.
        """
        if "@" not in value:
            raise ValueError("Érvénytelen e-mail cím.")
        self._con_email = value

    # con_person
    @property
    def con_person(self):
        """Visszaadja a kapcsolattartó nevét."""
        return self._con_person

    @con_person.setter
    def con_person(self, value: str):
        """
        Beállítja a kapcsolattartó nevét.

        Args:
            value (str): A kapcsolattartó neve.
        """
        self._con_person = value

    # con_phone
    @property
    def con_phone(self):
        """Visszaadja a kapcsolattartó telefonszámát."""
        return self._con_phone

    @con_phone.setter
    def con_phone(self, value: str):
        """
        Beállítja a kapcsolattartó telefonszámát.

        Args:
            value (str): A telefonszám, amit be akarunk állítani.

        Raises:
            ValueError: Ha a telefonszám nem '+' jellel kezdődik.
        """
        if not value.startswith("+"):
            raise ValueError("A telefonszámnak '+' jellel kell kezdődnie.")
        self._con_phone = value
