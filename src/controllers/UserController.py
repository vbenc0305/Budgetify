"""UserController.py"""
from src.models.user import User


class UserController:
    """
        Usereket kezel
    """
    def __init__(self, user_dao):
        """
        Konstruktor a UserController osztályhoz.
        Inicializálja a DAO objektumot, amely az adatbázis-interakciókat kezeli.

        :param user_dao: A User DAO implementációja.
        """
        self.user_dao = user_dao

    def create_user(self, name, email, phone, pwd, role,birthdate,last_login):
        """
        Létrehoz egy új felhasználót, és elmenti az adatbázisba.

        :param last_login: legutóbbi login
        :param birthdate: A felhasználó szültési dátuma
        :param name: A felhasználó neve.
        :param email: A felhasználó e-mail címe.
        :param phone: A felhasználó telefonszáma.
        :param pwd: A felhasználó jelszava.
        :param role: A felhasználó szerepe.
        :return: A sikeresen létrehozott felhasználó objektuma.
        """
        user = User(name=name, email=email, phone=phone, pwd=pwd, role=role,birthdate=birthdate,last_login=last_login)
        return self.user_dao.save(user)

    def get_user(self, user_id):
        """
        Lekéri a felhasználót az adatbázisból a felhasználó ID-ja alapján.

        :param user_id: A keresett felhasználó ID-ja.
        :return: A felhasználó objektuma, ha megtalálható.
        """
        return self.user_dao.get_by_id(user_id)

    def update_user(self, user_id, name=None, email=None, phone=None, pwd=None, role=None):
        """
        Frissíti egy meglévő felhasználó adatait.

        :param user_id: A frissítendő felhasználó ID-ja.
        :param name: A frissített név (ha van).
        :param email: A frissített e-mail cím (ha van).
        :param phone: A frissített telefonszám (ha van).
        :param pwd: A frissített jelszó (ha van).
        :param role: A frissített szerep (ha van).
        :return: A frissített felhasználó objektuma.
        """
        user = self.user_dao.get_by_id(user_id)
        if user:
            if name:
                user.set_name(name)
            if email:
                user.set_email(email)
            if phone:
                user.set_phone(phone)
            if pwd:
                user.set_pwd(pwd)
            if role:
                user.set_role(role)
            return self.user_dao.save(user)
        return None

    def delete_user(self, user_id):
        """
        Törli a felhasználót az adatbázisból.

        :param user_id: A törlendő felhasználó ID-ja.
        :return: True, ha sikerült törölni, különben False.
        """
        user = self.user_dao.get_by_id(user_id)
        if user:
            self.user_dao.delete(user_id)
            return True
        return False
