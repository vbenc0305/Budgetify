import os
import sys
import time
from datetime import datetime

import bcrypt

from src.DAO.DAOimpl import FirebaseDAO
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QCheckBox, QFrame, QMessageBox
)

from src.views.main_view import MainView
from src.views.register_view import RegisterWindow
from src.views.usr_info_add import UsrInfoAddView


# ----------------------------------------------------------------
# 1) A folyamatos időfrissítést végző szál
# ----------------------------------------------------------------
class TimerThread(QThread):
    updated = pyqtSignal(str)  # Jel az idő frissítésére

    def run(self):
        while True:
            current_time = time.strftime('%Y-%m-%d %H:%M:%S')
            self.updated.emit(current_time)
            time.sleep(1)  # 1 másodperc késleltetés

# ----------------------------------------------------------------
# 2) A bal oldali rész: képváltós slider és óra
# ----------------------------------------------------------------
class LeftSide(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_index = 0
        self.images = []
        self.labels = []
        self.dots = []
        self.init_ui()

    def init_ui(self):
        # A bal oldali widget teljes felületére QVBoxLayout
        self.layout = QVBoxLayout(self)
        # Középre igazítjuk (vízszintesen és függőlegesen is)
        self.layout.setAlignment(Qt.AlignCenter)
        # Térköz és margók minimalizálása
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(10, 10, 10, 10)

        # -- Képek betöltése --
        self.images = [
            QPixmap(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "images", "image1.png"))),
            QPixmap(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "images", "image2.png"))),
            QPixmap(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "images", "image3.png"))),
            QPixmap(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "images", "image4.png"))),
        ]

        # -- Képek megjelenítése --
        self.image_layout = QVBoxLayout()
        self.image_layout.setSpacing(0)
        self.image_layout.setContentsMargins(0, 0, 0, 0)
        # A képeket is középre rakjuk
        self.image_layout.setAlignment(Qt.AlignCenter)

        for pixmap in self.images:
            label = QLabel(self)
            scaled_pixmap = pixmap.scaled(300, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            label.setPixmap(scaled_pixmap)
            label.setAlignment(Qt.AlignCenter)
            label.setVisible(False)
            self.labels.append(label)
            self.image_layout.addWidget(label)

        # Az első kép látható
        self.labels[self.current_index].setVisible(True)

        # -- Pontok (dots) létrehozása --
        self.dots_layout = QHBoxLayout()
        self.dots_layout.setSpacing(5)
        self.dots_layout.setContentsMargins(0, 0, 0, 0)
        self.dots_layout.setAlignment(Qt.AlignCenter)

        for i in range(len(self.images)):
            dot = QPushButton(self)
            dot.setFixedSize(10, 10)
            dot.setStyleSheet("border-radius: 5px; background-color: gray;")
            dot.setFlat(True)
            dot.setEnabled(False)
            self.dots.append(dot)
            self.dots_layout.addWidget(dot)

        # Az első pontot kiemeljük
        self.dots[0].setStyleSheet("border-radius: 5px; background-color: black;")

        # -- Automatikus kép csere Timer --
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.change_image)
        self.timer.start(10000)

        # -- Idő megjelenítése --
        self.time_label = QLabel(self)
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setVisible(False)

        # Külön szál az idő frissítéséhez
        self.timer_thread = TimerThread()
        self.timer_thread.updated.connect(self.update_time)
        self.timer_thread.start()

        # -- Layout összerakása --
        self.layout.addLayout(self.image_layout)
        self.layout.addLayout(self.dots_layout)
        self.layout.addWidget(self.time_label)

    def change_image(self):
        # Elrejtjük a korábbi képet
        self.labels[self.current_index].setVisible(False)
        self.dots[self.current_index].setStyleSheet("border-radius: 5px; background-color: gray;")

        # Következő index
        self.current_index = (self.current_index + 1) % len(self.images)
        # Láthatóvá tesszük az új képet
        self.labels[self.current_index].setVisible(True)
        self.dots[self.current_index].setStyleSheet("border-radius: 5px; background-color: black;")

    def update_time(self, current_time):
        self.time_label.setText(current_time)

# ----------------------------------------------------------------
# 3) A jobb oldali rész: bejelentkezési űrlap
# ----------------------------------------------------------------
class RightSide(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.usr_email=""
        self.firebase_dao_user = FirebaseDAO("user")
        self.firebase_dao_usr_info=FirebaseDAO("usr_info")
        self.init_ui()
        print("anyad")

    def on_login_click(self):
        email = self.email_field.text()
        password = self.password_field.text()
        self.check_user_password(email,password)  # Kiírjuk az üzenetet

    def on_register_click(self):
        print("Regisztrációs linkre kattintva!")
        self.register_window = RegisterWindow()
        self.register_window.show()

        # Bejelentkezéskor: jelszó ellenőrzése

    def check_user_password(self, email, input_password):
        """
        Ellenőrzi a felhasználó jelszavát a Firestore adatbázisból lekért hashelt jelszóval.

        :param email: A felhasználó email címe.
        :param input_password: A beírt jelszó.
        :return: True, ha helyes a jelszó, különben False.
        """
        # Lekérdezzük a tárolt hashelt jelszót az adatbázisból
        stored_hashed_password = self.firebase_dao_user.get_user_by_email(email).get("password")

        if stored_hashed_password is None:
            print("Hibás felhasználónév vagy jelszó!")  # Konzolra kiírjuk a hibát
            self.show_error_screen("Hibás felhasználónév vagy jelszó!")  # Error screen megjelenítése
            return False  # Sikertelen bejelentkezés

        # Ellenőrizzük, hogy a megadott jelszó megegyezik-e a hashelt jelszóval
        if bcrypt.checkpw(input_password.encode('utf-8'), stored_hashed_password.encode('utf-8')):
            print("Bejelentkeztél!")
            self.check_user_data_and_show_view(email)
            return True  # Jelszó helyes
        else:
            print("Hibás jelszó!")  # Konzolra kiírjuk
            self.show_error_screen("Hibás felhasználóvnév vagy jelszó!")  # Error screen megjelenítése
            return False  # Jelszó helytelen

    from datetime import datetime

    def check_user_data_and_show_view(self, email):
        """
        Ellenőrzi, hogy a felhasználó adatainak van-e "N/A" értéke.
        Ha az életkor "N/A", de a születési dátum megvan, kiszámolja az életkort és frissíti az adatbázisban.
        """
        # Lekérdezzük a felhasználó adatait
        user_info = self.firebase_dao_user.get_user_info_by_email(email)
        user = self.firebase_dao_user.get_user_by_email(email)

        if user_info.get("age") == "N/A":
            # Születési dátumból életkor számítása
            birthdate = datetime.strptime(user["birthdate"], "%Y-%m-%d")
            today = datetime.today()
            age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))

            # Életkor frissítése az adatbázisban az update() metódussal
            success = self.firebase_dao_usr_info.update(email, {"age": age})

            if success:
                print(f"Életkor frissítve az adatbázisban: {age}")
                user_info["age"] = age  # Frissítjük a lokális user_info dict-et is
            else:
                print("Hiba történt az életkor frissítése közben!")

        if "N/A" in user_info.values():
            self.usr_email=user["email"]
            self.show_usr_info_add_view(email)  # Adatkitöltő oldal megjelenítése
        else:
            self.show_main_window(email)  # Főoldal megjelenítése


    def show_main_window(self, email):
        # A felhasználó nevének lekérése a Firestore-ból
        user_name = self.firebase_dao_user.get_user_by_email(email).get("name")

        self.main_window= MainView(user_name)
        self.main_window.show()

    def show_error_screen(self, message):
        """
        Megjelenít egy hibaüzenetet egy felugró ablakban.

        :param message: A megjelenítendő hibaüzenet.
        """
        error_box = QMessageBox()
        error_box.setIcon(QMessageBox.Critical)
        error_box.setWindowTitle("Hiba")
        error_box.setText(message)
        error_box.setStandardButtons(QMessageBox.Ok)
        error_box.exec_()

    def init_ui(self):
        # A RightSide teljes felületét kitöltő layout
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)  # Minden középre kerüljön
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # -------------------------------
        # 1) Üdvözlő doboz
        # -------------------------------
        welcome_frame = QFrame()
        welcome_frame.setStyleSheet("""
            background-color: #3E88EF;
            border: 2px solid #cccccc;
            border-radius: 10px;
            padding: 15px;
            color: white;
        """)
        welcome_frame.setFrameShape(QFrame.Box)
        welcome_frame.setFrameShadow(QFrame.Raised)
        welcome_frame.setLineWidth(5)


        # A frame belső layoutja
        welcome_layout = QVBoxLayout(welcome_frame)
        welcome_layout.setAlignment(Qt.AlignCenter)


        # Üdvözlő szöveg
        welcome_label = QLabel("Üdvözlünk a belépési oldalon!\nKérjük add meg az adataidat.")
        welcome_label.setAlignment(Qt.AlignCenter)
        welcome_layout.addWidget(welcome_label)

        # -------------------------------
        # 2) Bejelentkezési mezők
        # -------------------------------
        fields_layout = QVBoxLayout()
        fields_layout.setAlignment(Qt.AlignCenter)
        fields_layout.setSpacing(10)
        fields_layout.setContentsMargins(0, 0, 0, 0)

        # E-mail cím
        email_label = QLabel("E-mail cím")
        email_label.setAlignment(Qt.AlignLeft)
        self.email_field = QLineEdit()
        self.email_field.setPlaceholderText("pl. valami@domain.com")

        # Jelszó
        password_label = QLabel("Jelszó")
        password_label.setAlignment(Qt.AlignLeft)
        self.password_field = QLineEdit()
        self.password_field.setPlaceholderText("Add meg a jelszót")
        self.password_field.setEchoMode(QLineEdit.Password)

        # Jegyezz meg
        self.remember_checkbox = QCheckBox("Jegyezz meg")

        # Hozzáadjuk a mezőket a fields_layout-hoz
        fields_layout.addWidget(email_label)
        fields_layout.addWidget(self.email_field)
        fields_layout.addWidget(password_label)
        fields_layout.addWidget(self.password_field)
        fields_layout.addWidget(self.remember_checkbox)

        # -------------------------------
        # 3) Bejelentkezés gomb
        # -------------------------------
        self.login_button = QPushButton("Bejelentkezés")
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)

        self.login_button.setCursor(Qt.PointingHandCursor)



        # Gomb kattintás eseményének kezelése
        self.login_button.clicked.connect(self.on_login_click)




        # Regisztrációs link
        self.register_button = QPushButton('Nincs fiókja? Hozzon létre egyet')
        self.register_button.setStyleSheet("color: white;")
        self.register_button.setCursor(Qt.PointingHandCursor)


        # MousePressEvent kezelés beállítása
        self.register_button.clicked.connect(self.on_register_click)

        # Gomb hozzáadása a layouthoz
        welcome_layout.addWidget(self.register_button)
        # -------------------------------
        # Layoutok összerakása
        # -------------------------------
        main_layout.addWidget(welcome_frame)       # Üdvözlő doboz
        main_layout.addLayout(fields_layout)       # Mezők
        main_layout.addWidget(self.login_button)   # Gomb

    def show_usr_info_add_view(self, email):
        self.register_window = UsrInfoAddView(email)
        self.register_window.show()


# ----------------------------------------------------------------
# 4) A főablak, ami összeilleszti a bal és jobb oldalt
# ----------------------------------------------------------------
class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Bejelentkezés")
        self.setWindowIcon(QIcon('assets/icons/app_icon.png'))

        # A Window ne legyen átméretezhető
        self.setFixedSize(800, 600)

        # Fő elrendezés: vízszintesen egymás mellé
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Bal oldal: képváltós slider
        self.left_side = LeftSide(self)
        # Jobb oldal: bejelentkezési űrlap
        self.right_side = RightSide(self)

        # Bal oldal és jobb oldal hozzáadása a fő layouthoz
        main_layout.addWidget(self.left_side, 1)
        main_layout.addWidget(self.right_side, 1)

# ----------------------------------------------------------------
# 5) Futtatás
# ----------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec_())
