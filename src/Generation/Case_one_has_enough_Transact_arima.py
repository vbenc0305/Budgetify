import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.statespace.sarimax import SARIMAX
from sklearn.metrics import mean_squared_error, r2_score
from src.DAO.DAOimpl import FirebaseDAO
from src.Generation.Feature_engineering import engineer_all_features
from src.Generation.model_utils import save_pipeline


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


# --- 1. Adatok betöltése és feature engineering ---
data = get_all_transactions("aliciacantu@gmail.com")
df = pd.DataFrame(data)
if df.empty:
    raise ValueError("Nincs elérhető tranzakció az adott emailhez.")

df = engineer_all_features(df)

# --- 2. Célváltozó (target) definiálása ---
TARGET = 'amount'
if TARGET not in df.columns:
    raise ValueError(f"A '{TARGET}' oszlop nem található meg a dataframe-ben.")

# --- 3. Hónap szerinti összesítés (idősor előkészítése) ---
df['month'] = df['date'].dt.month  # Feltételezve, hogy van 'date' oszlopod, ami dátum típusú
monthly_sum = df.groupby('month')[TARGET].sum()

print("Hónap szerinti összegzés:\n", monthly_sum)

# --- 4. SARIMA modell alkalmazása ---
train_data = monthly_sum.values  # Használjuk a havi összegeket

# SARIMA modell paraméterezése (p, d, q) x (P, D, Q, s), ahol s = szezonális periódus
seasonal_order = (1, 1, 1, 12)  # 12 hónapos szezonális ciklus (éves hatás)
model = SARIMAX(train_data, order=(1, 1, 1), seasonal_order=seasonal_order)

# Modell tanítása
model_fit = model.fit()

# 12 hónapos előrejelzés (az év hátralévő részére)
forecast = model_fit.forecast(steps=10)

# Az utolsó 12 hónap kiválasztása az eredeti adatokból (teszt adatok)
test_data = train_data[-10:]  # Ezt bővítsd ki, ha több hónapra van szükség

# Ellenőrizzük, hogy a méretek megegyeznek
if len(test_data) == len(forecast):
    mse = mean_squared_error(test_data, forecast)
    r2 = r2_score(test_data, forecast)
else:
    print(f"⚠️ Figyelmeztetés: Az előrejelzés ({len(forecast)}) és a tesztadatok ({len(test_data)}) hossza nem egyezik.")
    mse = None
    r2 = None

print(f"🎯 SARIMA Modell MSE: {mse}, R²: {r2}")

# --- 5. Előrejelzés vizualizálása ---
plt.figure(figsize=(10, 6))
plt.plot(monthly_sum.index, monthly_sum.values, label='Valós adatok', color='blue')
plt.plot(range(len(monthly_sum), len(monthly_sum) + len(forecast)), forecast, label='Előrejelzés', color='red', linestyle='--')
plt.xlabel("Hónap")
plt.ylabel("Költés (Összeg)")
plt.title("SARIMA Előrejelzés (Következő 12 hónap)")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()


print(forecast)
