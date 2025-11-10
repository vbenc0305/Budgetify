import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("conninfo.json")

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

def get_user_doc(uid: str):
    # Firestore usr_info
    usr_info_ref = db.collection("usr_info").document(uid)
    usr_info_snap = usr_info_ref.get()
    usr_info = usr_info_snap.to_dict() if usr_info_snap.exists else {}

    # Firestore users kollekció
    user_ref = db.collection("users").document(uid)
    user_snap = user_ref.get()
    user_data = user_snap.to_dict() if user_snap.exists else {}

    # Merge: user_data felülírja az usr_info-t ha ütköznek a kulcsok
    merged = {**usr_info, **user_data}

    return merged

def update_user_doc(uid: str, data: dict):
    # Két szótár a frissítendő adatoknak
    users_data_to_save = {}
    usr_info_data_to_save = {}

    # 1. Adatok szétválasztása és szűrése

    # Mezők, amik a 'users' kollekcióhoz tartoznak (pl. név)
    USERS_FIELDS = ["name", "phone", "birthdate"]
    # Mezők, amik a 'usr_info' kollekcióhoz tartoznak (pl. demográfiai adatok)
    USR_INFO_FIELDS = ["country", "education", "gender", "housing_status", "marital_status",
                       "occupation"]  # Aage is ide jönne, de azt a backend számolja

    for key, value in data.items():
        if key == 'email':
            # Ezt ignoráljuk, a Firebase Auth-ot nem frissítjük a Firestore-ból
            continue

        if key in USERS_FIELDS:
            users_data_to_save[key] = value

        elif key in USR_INFO_FIELDS:
            usr_info_data_to_save[key] = value

        # Opcionálisan: itt kezelhetnénk azokat az adatokat, amik egyik listában sincsenek (pl. hibajelzés vagy ignorálás)

    # 2. Frissítések végrehajtása (csak ha van mentendő adat)

    # FRISSÍTÉS 1: users kollekció (ha szükséges)
    if users_data_to_save:
        users_doc_ref = db.collection("users").document(uid)
        users_doc_ref.set(users_data_to_save, merge=True)

    # FRISSÍTÉS 2: usr_info kollekció (ha szükséges)
    if usr_info_data_to_save:
        usr_info_doc_ref = db.collection("usr_info").document(uid)
        usr_info_doc_ref.set(usr_info_data_to_save, merge=True)

    # 3. Visszaadjuk a frissített teljes dokumentumot (mindkét kollekcióból összeolvasztva)
    return get_user_doc(uid)

def get_all_occupations():
    """
    Lekéri a 'occupations' gyűjteményben tárolt összes foglalkozást.
    A dokumentum ID-je a foglalkozás neve.
    """
    try:
        # Lekérjük az összes dokumentumot az 'occupations' gyűjteményből
        docs = db.collection("occupations").stream()

        # Létrehozzuk a listát a dokumentum ID-kből (ezek a foglalkozás nevek)
        occupations = [doc.id for doc in docs]

        # Ábécé sorrendben adjuk vissza a listát
        return sorted(occupations)
    except Exception as e:
        print(f"Hiba a foglalkozások lekérésekor: {e}")
        return []

def add_new_occupation(name: str):
    """
    Hozzáad egy új foglalkozást az 'occupations' gyűjteményhez.
    A foglalkozás neve a dokumentum azonosítója lesz, a felülírás elkerüléséért.
    """
    # Tisztítás és normalizálás
    normalized_name = name.strip()

    if not normalized_name:
        return False

    try:
        # A dokumentum ID-je a foglalkozás neve
        doc_ref = db.collection("occupations").document(normalized_name)

        # A .set({}, merge=True) parancs:
        # 1. Létrehozza a dokumentumot az adott ID-vel (a névvel).
        # 2. Ha már létezik, nem ír felül semmit (azaz elkerüljük a felesleges mentést/frissítést),
        #    mivel a mentendő adat egy üres szótár {}.
        doc_ref.set({}, merge=True)

        return True
    except Exception as e:
        print(f"Hiba az új foglalkozás hozzáadásakor '{name}': {e}")
        return False

def get_user_transactions(uid: str):
    """
    Lekéri egy adott felhasználó tranzakcióit a Firestore-ból.
    A tranzakciók a /users/{uid}/transactions alkollekcióban vannak tárolva.

    Visszatérési érték:
        List[dict] - lista a tranzakciók szótáraiból; hiba vagy hiány esetén üres lista.
    """
    if not uid:
        return []

    try:
        user_ref = db.collection("users").document(uid)
        transactions_ref = user_ref.collection("transactions")
        docs = transactions_ref.stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        print(f"Hiba a felhasználó tranzakcióinak lekérésekor for uid={uid}: {e}")
        return []

def get_usr_info_doc(id: str):
    doc_ref = db.collection("usr_info").document(id)
    doc = doc_ref.get()
    print(f"doc.exists={doc.exists}, id={id}")
    return doc.to_dict() if doc.exists else None

def update_usr_info_doc(id: str, data: dict):
    doc_ref = db.collection("usr_info").document(id)
    doc_ref.set(data, merge=True)
    return data

def save_user_transaction(uid: str, transaction_data: dict):
    """
    Ment egy tranzakciót a Firestore-ba a felhasználóhoz.

    Args:
        uid (str): Felhasználó azonosítója
        transaction_data (dict): Transaction.to_dict() által visszaadott dict
    """
    # Ha van 'id' mező, használjuk dokumentum ID-ként, különben auto generált ID
    doc_id = transaction_data.get("id")

    # Firestore path: users/{uid}/transactions/{doc_id}
    collection_ref = db.collection("users").document(uid).collection("transactions")

    if doc_id:
        doc_ref = collection_ref.document(doc_id)
    else:
        doc_ref = collection_ref.document()  # auto ID

    doc_ref.set(transaction_data)  # set overwrites vagy létrehoz új dokumentumot
    return doc_ref.id

def save_user_transactions(uid: str, transactions: list[dict]):
    """
    Tömegesen ment tranzakciókat a Firestore-ba a felhasználóhoz.

    Args:
        uid (str): Felhasználó azonosítója
        transactions (list[dict]): Transaction.to_dict() által visszaadott dict lista
    """
    if not transactions:
        return 0

    collection_ref = db.collection("users").document(uid).collection("transactions")
    batch = db.batch()  # batch write létrehozása

    for tx_data in transactions:
        # Ha van 'id', használjuk dokumentum ID-ként, különben auto ID
        doc_id = tx_data.get("id")
        doc_ref = collection_ref.document(doc_id) if doc_id else collection_ref.document()
        batch.set(doc_ref, tx_data)

    batch.commit()  # commit minden változtatást egyszerre
    return len(transactions)