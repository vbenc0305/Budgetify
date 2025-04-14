class UsrInfo:
    def __init__(self, user_id="", age="N/A", gender="N/A", occupation="N/A",
                 education="N/A", housing_status="N/A", marital_status="N/A"):
        """
        Felhasználói információkat tároló osztály Firestore-hoz.

        :param user_id: A felhasználó Firestore azonosítója (str)
        :param age: Életkor (str)
        :param gender: Nem (str)
        :param occupation: Foglalkozás (str)
        :param education: Legmagasabb iskolai végzettség (str)
        :param location: Lakhely (str)
        :param housing_status: Lakáshelyzet (str)
        :param marital_status: Családi állapot (str)
        """
        self.user_id = user_id if user_id else "N/A"  # Firestore azonosító
        self.age = age
        self.gender = gender
        self.occupation = occupation
        self.education = education
        self.housing_status = housing_status
        self.marital_status = marital_status

    def to_dict(self):
        """Az objektumot szótárrá alakítja az adatbázis számára."""
        return {
            "user_id": self.user_id,
            "age": self.age,
            "gender": self.gender,
            "occupation": self.occupation,
            "education": self.education,
            "housing_status": self.housing_status,
            "marital_status": self.marital_status
        }

    @classmethod
    def from_dict(cls, data):
        """Szótárból hoz létre egy UsrInfo példányt."""
        return cls(
            user_id=data.get("user_id", "N/A"),
            age=data.get("age", "N/A"),
            gender=data.get("gender", "N/A"),
            occupation=data.get("occupation", "N/A"),
            education=data.get("education", "N/A"),
            housing_status=data.get("housing_status", "N/A"),
            marital_status=data.get("marital_status", "N/A")
        )
