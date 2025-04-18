# src/data_loader.py

import pandas as pd
from src.DAO.DAOimpl import FirebaseDAO
from src.Generation.Feature_engineering import engineer_all_features

# Globálisan elérhető DataFrame
def load_global_data(email: str) -> pd.DataFrame:
    """
    Betölti az összes tranzakciót és végrehajtja a feature-engineeringet.
    """
    # 1. Tranzakciók beolvasása
    dao = FirebaseDAO("user")
    txs = dao.read_user_transactions(identifier=email)
    if not txs:
        return pd.DataFrame()

    df = pd.DataFrame(txs)
    df['user_email'] = email  # Felhasználó azonosítása
    # 2. Feature‐engineering
    df = engineer_all_features(df)
    return df  # Pandas DataFrame, később újrahasznosítható :contentReference[oaicite:4]{index=4}


def get_all_transactions(email):
    user_dao = FirebaseDAO("user")
    all_transactions = []
    if not email:
        return []

    transactions = user_dao.read_user_transactions(identifier=email)
    for t in transactions:
        t["user_email"] = email
        all_transactions.append(t)

    return all_transactions
