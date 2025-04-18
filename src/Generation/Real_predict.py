import pandas as pd
import joblib

# 1) Generáljuk a predikciós dátumokat:
future_months = pd.date_range(start="2021-05-01", end="2021-12-31", freq="MS")

# 2) Készítsünk DataFrame-et:
df_future = pd.DataFrame({"date": future_months})

# 3) Időbeli feature-ök:
df_future["month"] = df_future["date"].dt.month
df_future["quarter"] = df_future["date"].dt.quarter
df_future["day_of_week"] = df_future["date"].dt.dayofweek
df_future["is_weekend"] = df_future["day_of_week"].isin([5, 6]).astype(int)
df_future["is_start_of_month"] = df_future["date"].dt.is_month_start.astype(int)
df_future["is_end_of_month"] = df_future["date"].dt.is_month_end.astype(int)

# 4) Dummy tran_type hozzáadása
df_future["tran_type"] = "UNKNOWN"  # Alapértelmezett értékként hozzunk létre egy dummy változót

# 5) Betöltjük a mentett pipeline-t
user_email = "aliciacantu@gmail.com"
pipeline = joblib.load(f"models/{user_email}_pipeline.pkl")

# 6) A múltbeli tranzakciók betöltése
df_train = pd.read_csv("transactions_with_features.csv")  # Feltételezzük, hogy van ilyen fájl
df_train['date'] = pd.to_datetime(df_train['date'])
df_train.set_index("date", inplace=True)

# 7) Aggregáljuk a tranzakciók számát havonta
df_train['tran_type'] = df_train['tran_type'].astype(str)  # Biztosítjuk, hogy a tranzakció típus string
user_transaction_count_month = df_train.resample("M")['tran_type'].count()

# Hozzáadjuk a tranzakciók számát a jövőbeli hónapokhoz
df_future['user_transaction_count_month'] = df_future['date'].apply(lambda x: user_transaction_count_month.get(x.replace(day=1), 0))

# 8) Felhasználói átlagos havi költés
past = df_train.resample("M")["amount"].sum()  # Havonta összegezzük az amount-okat
user_avg = past.mean()
df_future["user_avg_monthly_expense"] = user_avg

# 9) Fizetési napokkal kapcsolatos feature-k
salary_days = [5, 20]  # Példa fizetési napokra

def calc_salary_feats(dt):
    day = dt.day
    prev = max([d for d in salary_days if d <= day] or [salary_days[-1] - 30])
    nxt = min([d for d in salary_days if d > day] or [salary_days[0] + 30])
    return day - prev, nxt - day

df_future[["days_since_last_salary", "days_until_next_salary"]] = \
    df_future["date"].apply(lambda dt: pd.Series(calc_salary_feats(dt)))

# 10) Az amount előrejelzése a jövőbeli hónapokra
df_future["predicted_amount"] = pipeline.predict(df_future)

# A predikált értékek és a hozzájuk tartozó dátumok kiírása a konzolra
print("\nPredikált havi költések a következő hónapokra:")
for idx, row in df_future.iterrows():
    print(f"{row['date'].strftime('%Y-%m-%d')} -> Predikált amount: {row['predicted_amount']:.2f}")

# 11) Ha szükséges a fájl mentése
df_future.to_csv("future_predictions_with_features.csv", index=False)
print("\nPredikciók elmentve a 'future_predictions_with_features.csv' fájlba.")
