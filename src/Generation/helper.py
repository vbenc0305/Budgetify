from src.DAO.DAOimpl import FirebaseDAO
firebase_dao_trans = FirebaseDAO("transactions")





from faker import Faker
from datetime import datetime, timedelta
import random

# Inicializáljuk a Faker objektumot
fake = Faker()
Faker.seed(42)  # Opcionális: ismételhetőség miatt

# Dátumtartomány beállítása: 2024.04.14 - 2025.04.14
start_date = datetime(2024, 4, 14)
end_date = datetime(2025, 4, 14)

def random_date(start, end):
    """
    *Véletlenszerű dátum* generálása a start és end közötti intervallumban.
    """
    delta = end - start
    random_seconds = random.randrange(int(delta.total_seconds()))
    return start + timedelta(seconds=random_seconds)

# **Felhasználó adatai**
user = {
  "email" : "whitneynelson@example.org"
}



# **Lehetséges kategóriák listája**
categories = [
    "Szórakozás", "Étel", "Utazás", "Egészség", "Közlekedés", "Lakhatás"
]

# **Tranzakciók generálása**
transactions = []
num_transactions = 50  # Minimum 50 tranzakció

for _ in range(num_transactions):
    amount = round(random.uniform(10, 1000), 2)  # Véletlenszerű összeg 10 és 1000 között
    category = random.choice(categories)         # Véletlenszerűen kiválasztott kategória
    date = random_date(start_date, end_date).strftime("%Y-%m-%d %H:%M:%S")
    description = fake.sentence(nb_words=6)        # Rövid leírás véletlenszerű mondattal
    for_who = fake.name()                          # Véletlenszerű név
    tran_type = "outgoing"                         # Csak kiadás (outgoing) – módosítható, ha bevételre is szeretnél
    transaction = {
        "amount": amount,
        "category": category,
        "date": date,
        "description": description,
        "for_who": for_who,
        "tran_type": tran_type,
        "email": user["email"]  # A felhasználó email-je mint azonosító
    }
    transactions.append(transaction)

# Az eredmény szép kiíratása
print("**Generált tranzakciók:**\n")
for idx, t in enumerate(transactions, start=1):
    print(f"**Tranzakció {idx}:**")
    if firebase_dao_trans.create(t):
        print(f"User trans for: {user['email']} successfully saved!")

    for key, value in t.items():
        print(f" - **{key}**: {value}")
    print("\n")
