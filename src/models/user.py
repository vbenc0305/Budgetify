"""User osztály"""

from datetime import datetime
class User:
    """
       User osztály, amely a felhasználók adatait reprezentálja.
       Az osztály getter és setter metódusokkal rendelkezik az adattagokhoz.
       """

    def __init__(self, name: str, email: str, phone: str, pwd: str, role: str,
                 birthdate: datetime, last_login: datetime):
        """
        Inicializálja az osztály attribútumait.

        Args:
            name (str): A felhasználó neve.
            email (str): A felhasználó e-mail címe.
            phone (str): A felhasználó telefonszáma.
            pwd (str): A felhasználó jelszava.
            role (str): A felhasználó szerepköre.
            birthdate (datetime): A felhasználó születési dátuma.
            last_login (datetime): A felhasználó utolsó bejelentkezési ideje.
        """
        self._name = name
        self._email = email
        self._phone = phone
        self._pwd = pwd
        self._role = role
        self._birthdate = birthdate
        self._last_login = last_login

    # name
    @property
    def name(self):
        """Visszaadja a felhasználó nevét."""
        return self._name

    @name.setter
    def name(self, value: str):
        """
        Beállítja a felhasználó nevét.

        Args:
            value (str): A név, amit be akarunk állítani.

        Raises:
            ValueError: Ha a név üres.
        """
        if not value:
            raise ValueError("A név nem lehet üres.")
        self._name = value

    # email
    @property
    def email(self):
        """Visszaadja a felhasználó e-mail címét."""
        return self._email

    @email.setter
    def email(self, value: str):
        """
        Beállítja a felhasználó e-mail címét.

        Args:
            value (str): Az e-mail cím, amit be akarunk állítani.

        Raises:
            ValueError: Ha az e-mail cím érvénytelen.
        """
        if "@" not in value:
            raise ValueError("Érvénytelen e-mail cím.")
        self._email = value

    # phone
    @property
    def phone(self):
        """Visszaadja a felhasználó telefonszámát."""
        return self._phone

    @phone.setter
    def phone(self, value: str):
        """
        Beállítja a felhasználó telefonszámát.

        Args:
            value (str): A telefonszám, amit be akarunk állítani.

        Raises:
            ValueError: Ha a telefonszám nem '+' jellel kezdődik.
        """
        if not value.startswith("+"):
            raise ValueError("A telefonszámnak '+' jellel kell kezdődnie.")
        self._phone = value

    # pwd
    @property
    def pwd(self):
        """Visszaadja a felhasználó jelszavát."""
        return self._pwd

    @pwd.setter
    def pwd(self, value: str):
        """
        Beállítja a felhasználó jelszavát.

        Args:
            value (str): A jelszó, amit be akarunk állítani.

        Raises:
            ValueError: Ha a jelszó rövidebb, mint 6 karakter.
        """
        if len(value) < 6:
            raise ValueError("A jelszónak legalább 6 karakter hosszúnak kell lennie.")
        self._pwd = value

    # role
    @property
    def role(self):
        """Visszaadja a felhasználó szerepkörét."""
        return self._role

    @role.setter
    def role(self, value: str):
        """
        Beállítja a felhasználó szerepkörét.

        Args:
            value (str): A szerepkör, amit be akarunk állítani.

        Raises:
            ValueError: Ha a szerepkör üres.
        """
        if not value:
            raise ValueError("A szerepkör nem lehet üres.")
        self._role = value

    # birthdate
    @property
    def birthdate(self):
        """Visszaadja a felhasználó születési dátumát."""
        return self._birthdate

    @birthdate.setter
    def birthdate(self, value: datetime):
        """
        Beállítja a felhasználó születési dátumát.

        Args:
            value (datetime): A születési dátum, amit be akarunk állítani.

        Raises:
            ValueError: Ha az érték nem datetime típusú.
        """
        if not isinstance(value, datetime):
            raise ValueError("A születési dátumnak datetime típusúnak kell lennie.")
        self._birthdate = value

    # last_login
    @property
    def last_login(self):
        """Visszaadja a felhasználó utolsó bejelentkezési idejét."""
        return self._last_login

    @last_login.setter
    def last_login(self, value: datetime):
        """
        Beállítja a felhasználó utolsó bejelentkezési idejét.

        Args:
            value (datetime): Az utolsó bejelentkezési idő, amit be akarunk állítani.

        Raises:
            ValueError: Ha az érték nem datetime típusú.
        """
        if not isinstance(value, datetime):
            raise ValueError("Az utolsó bejelentkezési dátumnak datetime típusúnak kell lennie.")
        self._last_login = value
