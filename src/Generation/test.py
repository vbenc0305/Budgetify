from datetime import datetime

import bcrypt
from faker import Faker
import json

from src.DAO.DAOimpl import FirebaseDAO

# Faker objektum létrehozása
fake = Faker()

import base64
import json
from datetime import datetime
from faker import Faker
from src.DAO.DAOimpl import FirebaseDAO

# Faker objektum létrehozása
fake = Faker()


def encode_password(password):
    """
    Base64 kódolással kódolja a jelszót.
    (Ez nem tekinthető erős biztonságnak, de visszafejthető, így elmenthetjük az eredetit.)
    """
    password_bytes = password.encode('utf-8')
    encoded_bytes = base64.b64encode(password_bytes)
    return encoded_bytes.decode()


def GenerateTenUser():
    """
    Generál 10 felhasználói adatot, lekódolja a jelszavakat,
    és elmenti a felhasználónév (email) és eredeti jelszó párokat egy TXT fájlba.
    A lekódolt jelszót mentjük a Firebase-be.
    """
    user_data_list = []
    firebase_dao = FirebaseDAO("user")
    credentials_file = "user_password_pairs.txt"


    # Fájl megnyitása írásra (append mód)
    with open(credentials_file, "a", encoding="utf-8") as f:
        for _ in range(10):
            original_password = fake.password()
            hashed_password = bcrypt.hashpw(original_password.encode(), bcrypt.gensalt())

            user_data = {
                "name": fake.name(),
                "email": fake.email(),
                "password": hashed_password,
                "birthdate": fake.date_of_birth(tzinfo=None, minimum_age=18, maximum_age=80).strftime("%Y-%m-%d"),
                "phone": fake.phone_number(),
                "role": "user",  # Mindig 'user'
                "last_login": fake.date_this_year().strftime("%Y-%m-%d")
            }
            user_data_list.append(user_data)

            # Eredeti jelszó mentése a fájlba (email + eredeti jelszó)
            f.write(f"{user_data['email']} : {original_password}\n")

            # Feltöltés Firebase-be
            if firebase_dao.create(user_data):
                print(f"User {user_data['email']} successfully saved!")
            else:
                print(f"Error saving user {user_data['email']}!")

    # A lista kiírása
    for i, user in enumerate(user_data_list, 1):
        print(f"User {i}: {json.dumps(user, indent=4)}")


# Példa hívás:
GenerateTenUser()


def generateTenTransaction(email):
    # Generáljunk 10 tranzakció adatot
    transaction_data_list = []
    firebase_dao = FirebaseDAO("transactions")

    for _ in range(10):
        transaction_data = {
            "amount": fake.random_int(min=1, max=100000),  # Egész szám 1 és 100 000 között
            "category": fake.random.choice([
            "Számlák, rezsi", "Vendéglátás", "Bevásárlás", "Készpénzfelvétel",
            "Szórakozás", "Egyéb", "Egészség, szépség", "Otthon",
            "Közlekedés", "Adomány", "Ruházat"
        ]),
            # A QDateTimeEdit-ből érdemes a dateTime() metódust használni a megfelelő formázás érdekében:
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # Jelenlegi időpont megfelelő formátumban
            "description": fake.sentence(nb_words=6),  # Egy rövid random leírás
            "for_who": fake.name(),  # Random ember neve
            "tran_type": fake.random.choice(["Bevétel", "Kiadás"]),
            "email": email,
        }
        print(transaction_data)
        transaction_data_list.append(transaction_data)


        # Feltöltés Firebase-be
        if firebase_dao.create(transaction_data):
            print(f"Transaction successfully saved for {email}!")

GenerateTenUser()