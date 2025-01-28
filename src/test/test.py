import unittest
from datetime import datetime

from src.models.company import Company  # Importáljuk a Company osztályt
from src.DAO.DAOimpl import FirebaseDAO
from src.models.user import User


class TestCompany(unittest.TestCase):

    def test_to_dict(self):
        # Létrehozzuk a Company példányt a megfelelő adatokkal
        company = Company("Cég A", "1234 Budapest", "ABC123", "email@ceg.hu", "Péter János", "+36123456789")
        company_dict = company.to_dict()

        # Elvárt szótár, amit vissza kell adni a to_dict metódusnak
        expected_dict = {
            "name": "Cég A",
            "address": "1234 Budapest",
            "company_id": "ABC123",
            "con_email": "email@ceg.hu",
            "con_person": "Péter János",
            "con_phone": "+36123456789"
        }

        self.assertEqual(company_dict, expected_dict)  # Ellenőrizzük, hogy egyeznek-e

    def test_name_setter_empty(self):
        company = Company("Cég A", "1234 Budapest", "ABC123", "email@ceg.hu", "Péter János", "+36123456789")

        with self.assertRaises(ValueError):
            company.name = ""  # Üres név

    def test_con_email_setter_invalid(self):
        company = Company("Cég A", "1234 Budapest", "ABC123", "email@ceg.hu", "Péter János", "+36123456789")

        with self.assertRaises(ValueError):
            company.con_email = "invalid-email"  # Érvénytelen e-mail cím

    def test_con_phone_setter_invalid(self):
        company = Company("Cég A", "1234 Budapest", "ABC123", "email@ceg.hu", "Péter János", "+36123456789")

        with self.assertRaises(ValueError):
            company.con_phone = "1234567890"  # Nem '+' jellel kezdődő telefonszám
class TestFirebaseDAO(unittest.TestCase):

    def setUp(self):
        # Inicializáljuk a Firestore kapcsolatot
        self.firebase_dao = FirebaseDAO("company")

    def test_create_data(self):
        company = Company("Cég BABABAB", "9876 Pécs", "XYZ789", "contact@ceg.hu", "Kovács László", "+36201234567")
        data = company.to_dict()  # Használjuk a Company osztályt
        self.firebase_dao.create(data)
        retrieved_data = self.firebase_dao.read("XYZ789")

        self.assertEqual(retrieved_data["name"], "Cég BABABAB")  # Itt frissítve a várt adatokat
        self.assertEqual(retrieved_data["address"], "9876 Pécs")

    def test_update_data(self):
        company = Company("Cég C", "4567 Debrecen", "XYZ101", "ceg@example.com", "Nagy István", "+36301234567")
        data = company.to_dict()  # Használjuk a Company osztályt
        self.firebase_dao.create(data)

        updated_company = Company("Cég C Updated", "4567 Debrecen Updated", "XYZ101", "ceg_updated@example.com",
                                  "Nagy István", "+36301234567")
        updated_data = updated_company.to_dict()  # Használjuk a Company osztályt
        self.firebase_dao.update("XYZ101", updated_data)
        retrieved_data = self.firebase_dao.read("XYZ101")

        self.assertEqual(retrieved_data["name"], "Cég C Updated")
        self.assertEqual(retrieved_data["address"], "4567 Debrecen Updated")

    def test_delete_data(self):
        company = Company("Cég D", "7654 Szeged", "XYZ102", "ceg_d@example.com", "Szabó Zoltán", "+36401234567")
        data = company.to_dict()  # Használjuk a Company osztályt
        self.firebase_dao.create(data)
        self.firebase_dao.delete("XYZ102")
        retrieved_data = self.firebase_dao.read("XYZ102")

        self.assertIsNone(retrieved_data)  # A törlés után None-t kell kapnunk, nem üres szótárt
class TestUser(unittest.TestCase):

    def setUp(self):
        # Létrehozunk egy példányt a User osztályból, érvényes adatokkal
        self.valid_user = User(
            name="Kovács János",
            email="janos.kovacs@example.com",
            phone="+36123456789",
            pwd="password123",
            role="admin",
            birthdate=datetime(1990, 1, 1),
            last_login=datetime(2025, 1, 1)
        )

    def test_name_setter_empty(self):
        # Ellenőrizzük, hogy üres név beállításakor ValueError-t kapunk-e
        with self.assertRaises(ValueError):
            self.valid_user.name = ""

    def test_email_setter_invalid(self):
        # Érvénytelen e-mail beállítása
        with self.assertRaises(ValueError):
            self.valid_user.email = "invalid-email"

    def test_phone_setter_invalid(self):
        # Nem '+' jellel kezdődő telefonszám
        with self.assertRaises(ValueError):
            self.valid_user.phone = "1234567890"  # Ez nem valid telefonszám

    def test_pwd_setter_too_short(self):
        # Túl rövid jelszó beállítása
        with self.assertRaises(ValueError):
            self.valid_user.pwd = "123"  # Minimum 6 karakter

    def test_role_setter_empty(self):
        # Üres szerepkör beállítása
        with self.assertRaises(ValueError):
            self.valid_user.role = ""

    def test_birthdate_setter_invalid(self):
        # Nem datetime típusú születési dátum beállítása
        with self.assertRaises(ValueError):
            self.valid_user.birthdate = "1990-01-01"  # String típusú adat

    def test_last_login_setter_invalid(self):
        # Nem datetime típusú utolsó bejelentkezési idő beállítása
        with self.assertRaises(ValueError):
            self.valid_user.last_login = "2025-01-01"  # String típusú adat

    def test_user_initialization(self):
        # Ellenőrizzük, hogy a valid_user példányunk helyesen van inicializálva
        self.assertEqual(self.valid_user.name, "Kovács János")
        self.assertEqual(self.valid_user.email, "janos.kovacs@example.com")
        self.assertEqual(self.valid_user.phone, "+36123456789")
        self.assertEqual(self.valid_user.pwd, "password123")
        self.assertEqual(self.valid_user.role, "admin")
        self.assertEqual(self.valid_user.birthdate, datetime(1990, 1, 1))
        self.assertEqual(self.valid_user.last_login, datetime(2025, 1, 1))

    def test_name_setter_valid(self):
        # Valid név beállítása
        self.valid_user.name = "Szabó Péter"
        self.assertEqual(self.valid_user.name, "Szabó Péter")

    def test_email_setter_valid(self):
        # Valid e-mail beállítása
        self.valid_user.email = "peter.szabo@example.com"
        self.assertEqual(self.valid_user.email, "peter.szabo@example.com")

    def test_phone_setter_valid(self):
        # Valid telefonszám beállítása
        self.valid_user.phone = "+36201234567"
        self.assertEqual(self.valid_user.phone, "+36201234567")

    def test_pwd_setter_valid(self):
        # Valid jelszó beállítása
        self.valid_user.pwd = "newpassword123"
        self.assertEqual(self.valid_user.pwd, "newpassword123")

    def test_role_setter_valid(self):
        # Valid szerepkör beállítása
        self.valid_user.role = "user"
        self.assertEqual(self.valid_user.role, "user")

    def test_birthdate_setter_valid(self):
        # Valid birthdate beállítása
        self.valid_user.birthdate = datetime(2000, 12, 25)
        self.assertEqual(self.valid_user.birthdate, datetime(2000, 12, 25))

    def test_last_login_setter_valid(self):
        # Valid last login beállítása
        self.valid_user.last_login = datetime(2025, 2, 1)
        self.assertEqual(self.valid_user.last_login, datetime(2025, 2, 1))
if __name__ == '__main__':
    unittest.main()
