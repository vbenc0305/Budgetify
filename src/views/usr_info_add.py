from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QStackedWidget, QHBoxLayout, \
    QCompleter, QComboBox
from PyQt5.QtCore import Qt
import requests

from src.DAO.DAOimpl import FirebaseDAO


def get_countries():
    url = "https://restcountries.com/v3.1/all"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        countries = response.json()

        country_names = []
        for country in countries:
            if "nativeName" in country["name"] and "hun" in country["name"]["nativeName"]:
                country_names.append(country["name"]["nativeName"]["hun"]["common"])
            else:
                country_names.append(country["name"]["common"])  # Ha nincs magyar név, marad angol

        return sorted(country_names)
    except requests.exceptions.RequestException as e:
        print(f"Hiba történt az API-lekérdezés során: {e}")
        return []


class UsrInfoAddView(QWidget):
    def __init__(self, usr_email,parent=None):
        super().__init__(parent)
        self.usr_email = usr_email
        self.occupation_input = None
        self.marital_status_input = None
        self.housing_status_input = None
        self.gender_input = None
        self.education_input = None
        self.setWindowTitle("Felhasználói adatok kitöltése")
        self.setGeometry(100, 100, 600, 400)
        self.firebase_dao_user_info = FirebaseDAO("usr_info")
        self.stacked_widget = QStackedWidget(self)

        self.page3 = self.create_address_page()
        self.page4 = self.create_input_page("Oktatás", "education")
        self.page5 = self.create_input_page("Nem", "gender")
        self.page6 = self.create_input_page("Lakhatási helyzet", "housing_status")
        self.page8 = self.create_input_page("Családi állapot", "marital_status")
        self.page9 = self.create_input_page("Foglalkozás", "occupation")

        for page in [self.page3, self.page4, self.page5, self.page6, self.page8, self.page9]:
            self.stacked_widget.addWidget(page)

        self.next_button = QPushButton("Tovább", self)
        self.prev_button = QPushButton("Vissza", self)
        self.save_button = QPushButton("Mentés", self)
        self.save_button.setVisible(False)

        self.next_button.clicked.connect(self.next_page)
        self.prev_button.clicked.connect(self.prev_page)
        self.save_button.clicked.connect(self.save_data)

        self.stacked_widget.setCurrentIndex(0)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.stacked_widget)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.prev_button)
        button_layout.addWidget(self.next_button)
        button_layout.addWidget(self.save_button)
        self.layout.addLayout(button_layout)

        self.setLayout(self.layout)
        self.user_data = {}

    def create_address_page(self):
        page = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Kérjük, adja meg az országát:"))

        self.country_input = QLineEdit()
        self.country_input.setPlaceholderText("Ország")
        layout.addWidget(self.country_input)

        self.setup_completers()

        page.setLayout(layout)
        return page

    def setup_completers(self):
        country_list = get_countries()

        country_completer = QCompleter(country_list)

        country_completer.setCaseSensitivity(Qt.CaseInsensitive)

        self.country_input.setCompleter(country_completer)

    def create_input_page(self, label_text, key):
        page = QWidget()
        layout = QVBoxLayout()

        label = QLabel(f"Kérjük, adja meg: {label_text}")
        layout.addWidget(label)

        if key == "education":
            input_field = QComboBox(self)
            education_levels = [
                "Általános iskola", "Középiskola", "Szakiskola", "OKJ képzés",
                "Felsőfokú szakképzés", "Alapképzés (BSc, BA)", "Mesterképzés (MSc, MA)",
                "Doktori képzés (PhD, DLA)", "Posztgraduális képzés", "Egyéb"
            ]
            input_field.addItems(education_levels)

        elif key == "gender":
            input_field = QComboBox(self)
            gender_options = ["Férfi", "Nő", "Egyéb"]
            input_field.addItems(gender_options)

        elif key == "housing_status":
            input_field = QComboBox(self)
            housing_options = [
                "Saját tulajdonú lakás",  # Ha saját tulajdonban van az ingatlan
                "Bérlakás",  # Klasszikus bérlemény
                "Albérlet",  # Rövidebb távú bérlés
                "Kollégiumi szoba",  # Egyetemi kollégium által biztosított szoba
                "Családi ház",  # Különálló családi otthon
                "Panel lakás",  # Többlakásos, általában több emeletes épület
                "Lakópark",  # Közösségi lakónegyed, ahol több ingatlan található
                "Újépítésű ingatlan",  # Frissen épült, modern kialakítású
                "Felújított lakás",  # Régebbi ingatlan, de korszerűsítve
                "Loft (ipari stílusú)",  # Tágas, nyitott elrendezés, ipari hangulattal
                "Vendégház / Nyaraló",  # Különleges, szüneti időre szánt ingatlan
                "Lakásmegosztás",  # Több ember által közösen bérelt vagy használt ingatlan
                "Ideiglenes szállás",  # Rövid távú, átmeneti megoldás
                "Vidéki ház",  # Csendes, természeti környezetben elhelyezkedő
                "Városi lakás",  # Központi, urbanizált környezetben
                "Duplex lakás",  # Két szintes lakás, egyedi elrendezéssel
                "Penthouse",  # Felső emeleti, exkluzív lakás
                "Ökopanellák",  # Környezetbarát, energiatakarékos megoldás
                "Közös ház",  # Több család vagy bérlő által megosztott ingatlan
                "Egyéb"  # Ha egyik opció sem felel meg
            ]
            input_field.addItems(housing_options)

        elif key == "marital_status":
            input_field = QComboBox(self)
            marital_status_options = [
                "Egyedülálló",  # Független, saját útját járó
                "Házasságban",  # Hagyományos, elkötelezett kapcsolat
                "Élettársi kapcsolatban",  # Közös életet építők
                "Elvált",  # Múlt lezárult, jövő felé tekint
                "Özvegy/Özvegyasszony",  # Egy szeretett személy elvesztése után
            ]
            input_field.addItems(marital_status_options)

        elif key == "occupation":
            input_field = QComboBox(self)
            occupation_options = [
                "8 órás (Teljes munkaidő)",  # Hagyományos, napi 8 órás munkarend
                "12 órás (Műszakos)",  # Hosszabb, műszakos beosztás
                "Vállalkozó / Szabadúszó",  # Saját vállalkozás vagy projektalapú munkavégzés
                "Részmunkaidős",  # Csak bizonyos órákban dolgozom
                "Rugalmas időbeosztás",  # Dinamikus, az aktuális feladatoktól függő munkarend
                "Távmunkában dolgozom",  # Otthonról vagy egyéb helyről végzem a munkámat
                "Egyéb"  # Ha egyik opció sem illik, válassz ide
            ]
            input_field.addItems(occupation_options)


        else:
            input_field = QLineEdit(self)

        layout.addWidget(input_field)
        page.setLayout(layout)

        setattr(self, f"{key}_input", input_field)
        return page

    def next_page(self):
        current_index = self.stacked_widget.currentIndex()
        if current_index < self.stacked_widget.count() - 1:
            self.stacked_widget.setCurrentIndex(current_index + 1)
        if self.stacked_widget.currentIndex() == self.stacked_widget.count() - 1:
            self.next_button.setVisible(False)
            self.save_button.setVisible(True)

    def prev_page(self):
        current_index = self.stacked_widget.currentIndex()
        if current_index > 0:
            self.stacked_widget.setCurrentIndex(current_index - 1)
        if self.stacked_widget.currentIndex() < self.stacked_widget.count() - 1:
            self.next_button.setVisible(True)
            self.save_button.setVisible(False)

    def save_data(self):
        # Gyűjtsük össze a felhasználó által megadott adatokat egy dictionary-be:
        self.user_data = {
            "country": self.country_input.text(),
            "education": self.education_input.currentText(),
            "gender": self.gender_input.currentText(),
            "housing_status": self.housing_status_input.currentText(),
            "marital_status": self.marital_status_input.currentText(),
            "occupation": self.occupation_input.currentText(),
        }
        print("Mentett adatok:", self.user_data)

        # Adatok mentése a Firebase-be:
        self.firebase_dao_user_info.update(self.usr_email, self.user_data)

        # **Itt jön a lényeg:** sikeres mentés után a MainView betöltése.
        # Például, ha a MainView konstruktor paraméterként várja a felhasználó nevét és email címét:
        from src.views.main_view import MainView

        # Érdemes a felhasználói nevet megszerezni pl. a mentett adatokból vagy a user profile-ból,
        # itt feltételezzük, hogy "Felhasználó" az alapértelmezett név, de ezt cseréld le, ha mást vársz.
        user_name = self.user_data.get("name", "Felhasználó")
        self.main_window = MainView(user_name, self.usr_email)
        self.main_window.show()

        # Bezárjuk az adatfelvételi ablakot
        self.close()

