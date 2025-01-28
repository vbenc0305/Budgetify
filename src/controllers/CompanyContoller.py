"""CompanyController.py"""


from src.DAO.DAOimpl import FirebaseDAO
from src.models.company import Company
from typing import List, Dict, Any


class CompanyController:
    """
    A CompanyController osztály felelős a cégekkel kapcsolatos műveletek kezeléséért.
    A cégadatokat a Firebase adatbázisban tároljuk.
    """

    def __init__(self, collection_name: str):
        """
        Inicializálja a CompanyController osztályt.

        Args:
            collection_name (str): A Firestore adatbázis gyűjteménye, ahol a cégeket tároljuk.
        """
        self.company_dao = FirebaseDAO(collection_name)

    def create_company(self, name: str, address: str, company_id: str,
                       con_email: str, con_person: str, con_phone: str) -> bool:
        """
        Létrehozza egy új cég adatokat a Firestore adatbázisban.

        Args:
            name (str): A cég neve.
            address (str): A cég címe.
            company_id (str): A cég azonosítója.
            con_email (str): A kapcsolattartó e-mail címe.
            con_person (str): A kapcsolattartó neve.
            con_phone (str): A kapcsolattartó telefonszáma.

        Returns:
            bool: Ha sikeres volt a létrehozás, True, egyébként False.
        """
        try:
            company = Company(name, address, company_id, con_email, con_person, con_phone)
            return self.company_dao.create(company.to_dict())
        except ValueError as ve:
            print(f"Hiba a cég létrehozásakor: {ve}")
            return False

    def update_company(self, company_id: str, data: Dict[str, Any]) -> bool:
        """
        Frissíti a cég adatokat a Firestore adatbázisban.

        Args:
            company_id (str): A cég egyedi azonosítója.
            data (Dict[str, Any]): Az új adatokat tartalmazó szótár, amit frissíteni kell.

        Returns:
            bool: Ha sikeres volt a frissítés, True, egyébként False.
        """
        try:
            return self.company_dao.update(company_id, data)
        except Exception as e:
            print(f"Hiba a cég frissítésekor: {e}")
            return False

    def delete_company(self, company_id: str) -> bool:
        """
        Törli a cég adatokat a Firestore adatbázisból.

        Args:
            company_id (str): A törlendő cég egyedi azonosítója.

        Returns:
            bool: Ha sikeres volt a törlés, True, egyébként False.
        """
        try:
            return self.company_dao.delete(company_id)
        except Exception as e:
            print(f"Hiba a cég törlésekor: {e}")
            return False

    def get_company(self, company_id: str) -> Dict[str, Any]:
        """
        Lekérdezi a cég adatait a Firestore adatbázisból.

        Args:
            company_id (str): A lekérdezendő cég egyedi azonosítója.

        Returns:
            Dict[str, Any]: A cég adatai szótár formájában.
        """
        try:
            return self.company_dao.read(company_id)
        except Exception as e:
            print(f"Hiba a cég adatainak lekérdezésekor: {e}")
            return {}

    def get_all_companies(self) -> List[Dict[str, Any]]:
        """
        Lekérdezi az összes cég adatait a Firestore adatbázisból.

        Returns:
            List[Dict[str, Any]]: Az összes cég adatai szótáraként.
        """
        try:
            return self.company_dao.find_all()
        except Exception as e:
            print(f"Hiba a cégek lekérdezésekor: {e}")
            return []
