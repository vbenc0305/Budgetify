import sys
from datetime import datetime

import bcrypt
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QLabel, QDateEdit, \
    QDialog, QCalendarWidget, QMessageBox
from PyQt5.QtCore import QDate, QRegExp
import re

from src.DAO.DAOimpl import FirebaseDAO
from src.models import user


class RegisterWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Regisztráció")
        self.setGeometry(300, 100, 400, 500)

        self.layout = QVBoxLayout(self)
        self.firebase_dao = FirebaseDAO("user")

        # Apply styles to the whole window
        self.setStyleSheet("""
                  
                  QPushButton {
                      background-color: #5c8dff;
                      color: white;
                      border-radius: 8px;
                      font-size: 14px;
                      padding: 10px;
                      border: none;
                      margin: 10px 0;
                  }
                  QPushButton:hover {
                      background-color: #3a6ccf;
                  }
                  QLineEdit {
                      background-color: white;
                      border: 1px solid #ddd;
                      border-radius: 5px;
                      padding: 10px;
                      font-size: 14px;
                  }
                  QLineEdit:focus {
                      border-color: #5c8dff;
                  }
                  QLabel {
                      font-size: 16px;
                  }
                  QFormLayout {
                      margin: 20px;
                  }
              """)

        # Állapotok kezelésére szolgáló változó
        self.state = 2  # 1 = Alapadatok, 2 = További adatok, 3 = Sikeres/Sikertelen

        self.init_basic_data_form()

    def init_basic_data_form(self):
        """Alapadatok űrlap megjelenítése"""
        self.basic_form = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Név")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Jelszó")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_confirm_input = QLineEdit()
        self.password_confirm_input.setPlaceholderText("Jelszó megerősítése")
        self.password_confirm_input.setEchoMode(QLineEdit.Password)

        self.next_button = QPushButton("Tovább")
        self.next_button.clicked.connect(self.go_to_additional_data)

        self.basic_form.addRow("Név:", self.name_input)
        self.basic_form.addRow("Email:", self.email_input)
        self.basic_form.addRow("Jelszó:", self.password_input)
        self.basic_form.addRow("Jelszó megerősítése:", self.password_confirm_input)
        self.basic_form.addWidget(self.next_button)

        self.layout.addLayout(self.basic_form)

    def go_to_additional_data(self):
        """Átváltás a további adatok oldalra"""
        if self.is_basic_data_valid():
            self.state = 2
            self.clear_layout()
            self.init_additional_data_form()
        else:
            self.show_error("Kérlek töltsd ki az összes mezőt!")

    def init_additional_data_form(self):
        """További adatok űrlap megjelenítése"""
        self.additional_form = QFormLayout()

        self.calendar_input = QCalendarWidget()  # QCalendarWidget hozzáadása
        self.calendar_input.setGridVisible(True)
        self.calendar_input.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)

        self.phone_input = QLineEdit(self)
        self.phone_input.setPlaceholderText("+36 70 171 5932")

        # Telefonszám validátor
        phone_regex = QRegExp(r"^\+?(\d{1,3})?(\s?(\(?\d{2,3}\)?\s?))?(\d{2,3}(\s?\d{2,3}){2})$")
        phone_validator = QRegExpValidator(phone_regex, self.phone_input)

        # A validator hozzárendelése
        self.phone_input.setValidator(phone_validator)

        self.register_button = QPushButton("Regisztrálás")
        self.register_button.clicked.connect(self.register_user)

        self.back_button = QPushButton("Vissza")
        self.back_button.clicked.connect(self.go_back_to_basic_data)

        self.additional_form.addRow("Születési dátum:", self.calendar_input)
        self.additional_form.addRow("Telefonszám:", self.phone_input)
        self.additional_form.addWidget(self.register_button)
        self.additional_form.addWidget(self.back_button)



        self.layout.addLayout(self.additional_form)

    def go_back_to_basic_data(self):
        """Vissza az alapadatok oldalra"""
        self.state = 1
        self.clear_layout()
        self.init_basic_data_form()

    from datetime import datetime

    def register_user(self):
        """A regisztráció elküldése"""
        if self.is_additional_data_valid():
            # Felhasználói adatokat kinyerjük a formból
            name = self.name_input.text()
            email = self.email_input.text()
            password = self.password_input.text()
            birthdate = self.calendar_input.selectedDate().toString("yyyy-MM-dd")
            phone = self.phone_input.text()

            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

            # Ellenőrizzük, hogy már létezik-e ilyen email cím
            if self.firebase_dao.user_exists(email):
                self.show_error("Ez az email cím már regisztrálva van!")
                return

            # Jelenlegi dátumot beállítjuk 'last_login' értéknek
            last_login = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Felhasználói adatokat szótárban tároljuk
            user_data = {
                "name": name,
                "email": email,
                "password": hashed_password.decode(),  # A hashelt jelszó stringként kerül tárolásra
                "birthdate": birthdate,
                "phone": phone,
                "role": "user",  # alapértelmezett érték
                "last_login": last_login  # aktuális dátum
            }

            # Felhasználó regisztrálása az adatbázisban
            if self.firebase_dao.create(user_data):
                self.show_success("Regisztráció sikeres!")
            else:
                self.show_error("Hiba történt a regisztráció során. Kérlek próbáld újra!")

    def is_basic_data_valid(self):
        """Alapadatok validálása"""
        if self.name_input.text() == "" or self.email_input.text() == "" or self.password_input.text() == "" or self.password_confirm_input.text() == "":
            return False

        # Email validálás
        email_pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(email_pattern, self.email_input.text()):
            self.show_error("Hibás email cím!")
            return False

        # Jelszó hossz validálása
        if len(self.password_input.text()) < 8:
            self.show_error("A jelszónak legalább 8 karakter hosszúnak kell lennie!")
            return False

        # Jelszó megerősítése
        if self.password_input.text() != self.password_confirm_input.text():
            self.show_error("A jelszavak nem egyeznek!")
            return False

        return True

    def is_additional_data_valid(self):
        """További adatok validálása"""
        phone_pattern = r"^\+36\s?\d{2}\s?\d{3}\s?\d{4}$"
        if not re.match(phone_pattern, self.phone_input.text()):
            self.show_error("Hibás telefonszám! Kérlek használd a következő formátumot: +36 70 171 5932")
            return False

        return self.calendar_input != QDate.currentDate() and self.phone_input.text() != ""

    def clear_layout(self):
        """Törli a meglévő formot a layoutból"""
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

    def show_success(self, message):
        """Siker üzenet popup"""
        QMessageBox.information(self,"Siker",message, QMessageBox.Ok)
        self.close()

    def show_error(self, message):
        """Hiba üzenet popup"""
        QMessageBox.critical(self, "Hiba", message, QMessageBox.Ok)


