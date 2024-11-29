class NotificationSettings:
    """
    Az NotificationSettings osztály a felhasználói értesítési beállításokat reprezentálja,
    például a havi és heti értesítések engedélyezését.
    """

    def __init__(self, notif_monthly: bool, notif_weekly: bool):
        """
        Inicializálja az értesítési beállításokat.

        Args:
            notif_monthly (bool): Havi értesítések engedélyezése.
            notif_weekly (bool): Heti értesítések engedélyezése.
        """
        self._notif_monthly = notif_monthly
        self._notif_weekly = notif_weekly

    # Getterek és setterek
    @property
    def notif_monthly(self):
        """Visszaadja a havi értesítések állapotát."""
        return self._notif_monthly

    @notif_monthly.setter
    def notif_monthly(self, value: bool):
        """Beállítja a havi értesítések állapotát."""
        if not isinstance(value, bool):
            raise ValueError("A havi értesítések beállítása boolean értéknek kell lennie.")
        self._notif_monthly = value

    @property
    def notif_weekly(self):
        """Visszaadja a heti értesítések állapotát."""
        return self._notif_weekly

    @notif_weekly.setter
    def notif_weekly(self, value: bool):
        """Beállítja a heti értesítések állapotát."""
        if not isinstance(value, bool):
            raise ValueError("A heti értesítések beállítása boolean értéknek kell lennie.")
        self._notif_weekly = value

    def to_dict(self) -> dict:
        """Visszaadja az értesítési beállításokat szótár formájában."""
        return {
            'notif_monthly': self._notif_monthly,
            'notif_weekly': self._notif_weekly
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Létrehoz egy NotificationSettings objektumot a szótár adatokból."""
        return cls(
            notif_monthly=data['notif_monthly'],
            notif_weekly=data['notif_weekly']
        )


class UserSettings:
    """
    Az UserSettings osztály a felhasználói beállításokat reprezentálja, beleértve az értesítéseket,
    a pénznemet, a grafikon színét, a nyelvet, az adatvédelmi beállítást és a témát.
    """

    def __init__(self, currency: str, graph_color: str, lang: str, priv_data: bool, theme: str,
                 user_id: str, notif: NotificationSettings):
        """
        Inicializálja a felhasználói beállításokat, beleértve az értesítési beállításokat.

        Args:
            currency (str): Az alapértelmezett pénznem.
            graph_color (str): A grafikon színkódja.
            lang (str): A felhasználó által preferált nyelv (pl. 'hu').
            priv_data (bool): Az adatvédelmi beállítás állapota.
            theme (str): Az alkalmazás témája (pl. 'dark' vagy 'light').
            user_id (str): A felhasználó azonosítója.
            notif (NotificationSettings): Az értesítési beállítások.
        """
        self._currency = currency
        self._graph_color = graph_color
        self._lang = lang
        self._priv_data = priv_data
        self._theme = theme
        self._user_id = user_id
        self._notif = notif  # Hozzáadjuk az értesítési beállításokat

    # Getterek és setterek
    @property
    def currency(self):
        """Visszaadja az alapértelmezett pénznemet."""
        return self._currency

    @currency.setter
    def currency(self, value: str):
        """Beállítja az alapértelmezett pénznemet."""
        if not value:
            raise ValueError("A pénznem nem lehet üres.")
        self._currency = value

    @property
    def graph_color(self):
        """Visszaadja a grafikon színét."""
        return self._graph_color

    @graph_color.setter
    def graph_color(self, value: str):
        """Beállítja a grafikon színét."""
        if not value:
            raise ValueError("A grafikon színe nem lehet üres.")
        self._graph_color = value

    @property
    def lang(self):
        """Visszaadja a felhasználó által preferált nyelvet."""
        return self._lang

    @lang.setter
    def lang(self, value: str):
        """Beállítja a felhasználó által preferált nyelvet."""
        if not value:
            raise ValueError("A nyelv nem lehet üres.")
        self._lang = value

    @property
    def priv_data(self):
        """Visszaadja az adatvédelem állapotát."""
        return self._priv_data

    @priv_data.setter
    def priv_data(self, value: bool):
        """Beállítja az adatvédelem állapotát."""
        if not isinstance(value, bool):
            raise ValueError("Az adatvédelem állapotának boolean értéknek kell lennie.")
        self._priv_data = value

    @property
    def theme(self):
        """Visszaadja az alkalmazás témáját."""
        return self._theme

    @theme.setter
    def theme(self, value: str):
        """Beállítja az alkalmazás témáját."""
        if value not in ["dark", "light"]:
            raise ValueError("A téma csak 'dark' vagy 'light' lehet.")
        self._theme = value

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

    @property
    def notif(self):
        """Visszaadja az értesítési beállításokat."""
        return self._notif

    @notif.setter
    def notif(self, value: NotificationSettings):
        """Beállítja az értesítési beállításokat."""
        if not isinstance(value, NotificationSettings):
            raise ValueError("Az értesítési beállításoknak NotificationSettings típusúnak kell lenniük.")
        self._notif = value

    def to_dict(self) -> dict:
        """Visszaadja a felhasználói beállításokat szótár formájában."""
        return {
            'currency': self._currency,
            'graph_color': self._graph_color,
            'lang': self._lang,
            'priv_data': self._priv_data,
            'theme': self._theme,
            'user_id': self._user_id,
            'notif': self._notif.to_dict()  # Az értesítési beállítások szótárként
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Létrehoz egy UserSettings objektumot a szótár adatokból."""
        notif_settings = NotificationSettings.from_dict(data['notif'])
        return cls(
            currency=data['currency'],
            graph_color=data['graph_color'],
            lang=data['lang'],
            priv_data=data['priv_data'],
            theme=data['theme'],
            user_id=data['user_id'],
            notif=notif_settings  # Átadjuk az értesítési beállításokat
        )
