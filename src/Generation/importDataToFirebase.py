from pathlib import Path

# --- Kiegészítés a DAOImpl.py-ból (Firebase inicializálás a db eléréséhez) ---
import firebase_admin
import pandas as pd
from firebase_admin import credentials, firestore

from src.DAO.DAOimpl import FirebaseDAO
from src.Generation.helper import for_who

# A 'conninfo.json' útvonalának beállítása a DAOImpl.py alapján.
# Ha ez a fájl nem létezik, a szkript futása hibát dob!
conn_path = Path(__file__).resolve().parents[2] / "conninfo.json"
try:
    cred = credentials.Certificate(str(conn_path))
    # Ezt csak egyszer kell inicializálni, a try-except blokk segít ebben.
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    print(f"FIGYELEM: A Firebase inicializálása nem sikerült! {e}")
# -------------------------------------------------------------------------


# CSV fájl beolvasása
# csv_path = "../../datasets/Dataset.csv" # Eredeti
csv_path = "../../datasets/Dataset_Magyar.csv" # A feltételezett, magyarosított fájl
df = pd.read_csv(csv_path)

# 1. Dátum konverzió: 'D/M/YY' -> ISO 8601
# Megadjuk a formátumot: '%d/%m/%y'
df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%y')

firebase_dao = FirebaseDAO("transactions")


from datetime import datetime
import re

def _normalize_amount(value):
    """
    Befogad stringet vagy számot.
    Visszatér: string formátumban (pl. "23300" vagy "23300.5" ha tört volt).
    Próbálja eltávolítani a valutajeleket, szóközöket, ezerelválasztókat.
    """
    s = str(value).strip()
    # vesszőt ponttá alakítunk (ha tizedes vessző van)
    s = s.replace(',', '.')
    # eltávolítunk minden karaktert, ami nem szám vagy pont
    s = re.sub(r'[^\d.]', '', s)
    if s == '':
        return '0'
    try:
        if '.' in s:
            val = float(s)
            # ha egészre jön ki, adjuk vissza egész számként
            if val.is_integer():
                return str(int(val))
            # egyértelmű lebegőpontos string (nem kötelező, de hasznos)
            return str(val).rstrip('0').rstrip('.')
        else:
            return str(int(s))
    except Exception:
        # ha valamiért nem sikerül parse-olni, hagyjuk az eredeti megtisztított stringet
        return s

def _normalize_date(date_input):
    """
    Befogad:
      - datetime objektumot,
      - ISO string-et (2025-03-24T08:20:07Z vagy 2025-03-24T08:20:07+02:00),
      - vagy már 'YYYY-MM-DD HH:MM:SS' formátumú stringet.
    Visszatér: 'YYYY-MM-DD HH:MM:SS' stringgel (ha nem sikerül parse-olni, visszaadja az eredeti stringet).
    """
    if isinstance(date_input, datetime):
        return date_input.strftime('%Y-%m-%d %H:%M:%S')
    s = str(date_input).strip()
    # próbáljuk ISO-ból parse-olni (kezeljük a Z-t is)
    try:
        iso = s.replace('Z', '')
        dt = datetime.fromisoformat(iso)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        # próbáljuk meg a már kívánt formátum szerint
        try:
            dt = datetime.strptime(s, '%Y-%m-%d %H:%M:%S')
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            # ha minden kudarcot vall, visszaadjuk az eredetit (feltéve, hogy az hasonló)
            return s

def _map_tran_type(category_type):
    """
    Egyszerű leképzés:
      - 'expense' / 'out' / 'outgoing' -> 'outgoing'
      - 'income' / 'in' / 'incoming' -> 'incoming'
    Egyébként visszaadja a bemenetet változatlanul.
    """
    if category_type is None:
        return ''
    t = str(category_type).strip().lower()
    if t in ('expense', 'out', 'outgoing'):
        return 'outgoing'
    if t in ('income', 'in', 'incoming'):
        return 'incoming'
    return category_type  # fallback: ahogy kaptuk

def build_transaction_record(date_input,
                             description,
                             amount_value,
                             category,
                             sub_category,
                             category_type,
                             email,
                             user_id,
                             for_who=''):
    """
    Visszaadja a Firebase-kompatibilis tranzakció dict-et.
    """
    date_str = _normalize_date(date_input)
    amount_str = _normalize_amount(amount_value)
    tran_type = _map_tran_type(category_type)

    transaction_data = {
        "date": date_str,                     # pl. "2025-03-24 08:20:07"
        "description": description or "",
        "amount": amount_str,                 # stringként, pl. "23300"
        "category": category or "",
        "sub_category:": sub_category or "",
        "tran_type": tran_type,               # "outgoing" vagy "incoming"
        "email": email,
        "for_who": for_who or "",
        "user_id": user_id
    }
    return transaction_data


# Függvény, hogy egy sorból kinyerjük a tranzakció adatait
def process_row(datarow):
    # 1. Dátum konverzió: ISO formátumra
    # Alapértelmezett idő: 00:00:00, de ha kell, utólag beállítható
    date_iso = datarow['Date'].strftime("%Y-%m-%dT%H:%M:%S")

    # 2. Description: egyszerűen az ok (az eredeti 'Description')
    description = datarow['Leírás']

    # 3. Debit/Credit: Ha Debit NaN (üres), akkor Credit, ellenkező esetben Debit
    # Figyeljük, hogy a pandas NaN értékeit np.isnan()-al is vizsgálhatjuk
    debit = datarow.get('Terhelés')
    credit = datarow.get('Jóváírás')

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
    category_type = str(datarow['Kategória Típus'])


    category = datarow['Kategória']
    sub_category = datarow['Al-kategória']

    # Összeállítjuk a tranzakció dict-et
    transaction_data = build_transaction_record(
        date_input=date_iso,
        description= description,
        amount_value= amount_value,
        category= category,
        sub_category=sub_category,
        category_type= category_type,
        for_who=for_who,# income vagy expense
        email= "aliciacantu@gmail.com",
        user_id="wXIqQmSZ1gc8SCe1crg4gf9ImmB2"
    )  # Új felhasználó azonosítója

    return transaction_data
'''
# Feldolgozzuk az összes sort, majd készítünk egy listát az tranzakciókról
transactions = []
for idx, row in df.iterrows():
    txn = process_row(row)
    transactions.append(txn)

# Debug: Nyomjuk ki az első 5 tranzakciót
for txn in transactions[:5]:
    print(txn)

# --- Firebase feltöltés az új metódussal ---
upload_count = firebase_dao.upload_transactions(transactions)
print(f"✅ Adatok sikeresen feltöltve a Firebase-be! ({upload_count} tranzakció)")'''

user_id_to_delete = '3Dye4gBbAdPQSto3WbqgkBu6lrj2'
deleted_count = firebase_dao.delete_all_user_transactions(user_id_to_delete)
print(f"🗑️ Törlés kész — törölt dokumentumok száma: {deleted_count}")