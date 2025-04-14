import pandas as pd

from src.DAO.DAOimpl import FirebaseDAO

# CSV fájl beolvasása
csv_path = "../../datasets/Dataset.csv"
df = pd.read_csv(csv_path)

# 1. Dátum konverzió: 'D/M/YY' -> ISO 8601
# Megadjuk a formátumot: '%d/%m/%y'
df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%y')

firebase_dao = FirebaseDAO("transactions")


# Függvény, hogy egy sorból kinyerjük a tranzakció adatait
def process_row(datarow):
    # 1. Dátum konverzió: ISO formátumra
    # Alapértelmezett idő: 00:00:00, de ha kell, utólag beállítható
    date_iso = datarow['Date'].strftime("%Y-%m-%dT%H:%M:%S")

    # 2. Description: egyszerűen az ok (az eredeti 'Description')
    description = datarow['Description']

    # 3. Debit/Credit: Ha Debit NaN (üres), akkor Credit, ellenkező esetben Debit
    # Figyeljük, hogy a pandas NaN értékeit np.isnan()-al is vizsgálhatjuk
    debit = datarow.get('Debit')
    credit = datarow.get('Credit')

    # Ellenőrizzük, hogy melyik nem null (NaN)
    if pd.isna(debit):
        amount_value = credit
    else:
        amount_value = debit

    # Általában, ha debit van, akkor az kiadás => negatív érték (és fordítva)
    # Ezt egyéni logikával tudod alakítani, pl.:
    # Feltételezve, hogy ha van Debit, az negatív, ha Credit, akkor pozitív
    # Tehát amount_value már tartalmazza a megfelelő előjelet, ha az adatok így vannak!

    # 5. Category type: kisbetűs string (income vagy expense)
    category_type = str(datarow['Category Type']).lower()

    # 4. Category: megtartjuk, de kihagyjuk a Sub-category-t
    category = datarow['Category']

    # Összeállítjuk a tranzakció dict-et
    transaction_data = {
        "date": date_iso,
        "description": description,
        "amount": amount_value,
        "category": category,
        "tran_type": category_type,  # income vagy expense
        "email": "aliciacantu@example.com"  # Új felhasználó azonosítója
    }
    return transaction_data


# Feldolgozzuk az összes sort, majd készítünk egy listát az tranzakciókról
transactions = []
for idx, row in df.iterrows():
    txn = process_row(row)
    transactions.append(txn)

# Debug: Nyomjuk ki az első 5 tranzakciót
for txn in transactions[:5]:
    print(txn)

# --- Firebase feltöltés ---
# Tegyük fel, hogy a "transactions" kollekciót a felhasználó "aliciacantu@example.com" alá szeretnénk rendezni.
# Például az alábbi struktúrát használhatjuk:
# /users/aliciacantu@example.com/transactions/{transactionID}


# Feltöltés: Minden tranzakciót egyedi dokumentumként mentünk fel.
for txn in transactions:
    if firebase_dao.create(txn):
        print(f"Transaction successfully saved for {txn['email']}!")

print("✅ Adatok sikeresen feltöltve a Firebase-be!")
