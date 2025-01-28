import unittest

from src.DAO.DAOimpl import FirebaseDAO
from src.models.company import Company


class TestCompany(unittest.TestCase):

    def test_to_dict(self):
        company = Company("Cég A", "1234 Budapest", "ABC123", "email@ceg.hu", "Péter János", "+36123456789")
        company_dict = company.to_dict()

        expected_dict = {
            "name": "Cég A",
            "address": "1234 Budapest",
            "company_id": "ABC123",
            "con_email": "email@ceg.hu",
            "con_person": "Péter János",
            "con_phone": "+36123456789"
        }

        self.assertEqual(company_dict, expected_dict)


class TestFirebaseDAO(unittest.TestCase):

    def setUp(self):
        # Itt inicializáljuk a Firestore kapcsolatot
        self.firebase_dao = FirebaseDAO("company")

    def test_create_data(self):
        data = {"name": "Cég B", "address": "9876 Pécs", "company_id": "XYZ789"}
        self.firebase_dao.create(data)
        retrieved_data = self.firebase_dao.read("XYZ789")

        self.assertEqual(retrieved_data["name"], "Cég B")
        self.assertEqual(retrieved_data["address"], "9876 Pécs")

    def test_update_data(self):
        data = {"name": "Cég C", "address": "4567 Debrecen", "company_id": "XYZ101"}
        self.firebase_dao.create(data)
        updated_data = {"name": "Cég C Updated", "address": "4567 Debrecen Updated", "company_id": "XYZ101"}
        self.firebase_dao.update("XYZ101", updated_data)
        retrieved_data = self.firebase_dao.read("XYZ101")

        self.assertEqual(retrieved_data["name"], "Cég C Updated")
        self.assertEqual(retrieved_data["address"], "4567 Debrecen Updated")

    def test_delete_data(self):
        data = {"name": "Cég D", "address": "7654 Szeged", "company_id": "XYZ102"}
        self.firebase_dao.create(data)
        self.firebase_dao.delete("XYZ102")
        retrieved_data = self.firebase_dao.read("XYZ102")

        self.assertEqual(retrieved_data,{})


class TestCompanySetters(unittest.TestCase):

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




if __name__ == '__main__':
    unittest.main()
