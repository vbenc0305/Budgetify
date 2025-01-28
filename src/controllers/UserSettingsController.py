"""userSettingsController.py"""

from src.DAO.DAOimpl import FirebaseDAO
from src.models.user_settings import UserSettings, NotificationSettings


class UserSettingsController:
    """
    Controller class for handling the User Settings functionality.

    This class provides methods to interact with the UserSettings model, including
    retrieving, creating, updating, and deleting user settings from the Firebase database.
    """

    def __init__(self, user_id: str):
        """
        Initializes the UserSettingsController with the given user_id.

        :param user_id: The unique identifier for the user whose settings are being managed.
        """
        self.user_id = user_id
        self.dao = FirebaseDAO('user_settings')  # Az 'user_settings' collection-t fogjuk használni

    def get_user_settings(self) -> UserSettings:
        """
        Retrieves the user settings for the given user_id from the database.

        :return: The UserSettings object containing all settings for the user.
        :raises: ValueError if the user settings are not found.
        """
        data = self.dao.read(self.user_id)
        if data:
            return UserSettings(**data)
        raise ValueError(f"User settings not found for user_id: {self.user_id}")  # Hibát dobunk, ha nem találunk adatot

    def create_user_settings(self, currency: str, graph_color: str, lang: str, priv_data: bool, theme: str, user_id:str, notif:NotificationSettings) -> bool:
        """
        Creates a new set of user settings for the given user_id.

        :param user_id: userhez tartozó settingek
        :param notif: notifikációk beállításai
        :param currency: The user's preferred currency.
        :param graph_color: The user's preferred color scheme for graphs.
        :param lang: The user's preferred language.
        :param priv_data: Flag indicating whether the user wants private data handling.
        :param theme: The user's preferred UI theme (e.g., light, dark).
        :return: True if the user settings were successfully created, False otherwise.
        """
        user_settings = UserSettings(currency, graph_color, lang, priv_data, theme, user_id, notif)

        # Rekord hozzáadása az adatbázishoz
        success = self.dao.create(user_settings.to_dict())  # Visszatérési érték: True vagy False

        return success