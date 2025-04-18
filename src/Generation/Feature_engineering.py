import pandas as pd
import numpy as np
from datetime import datetime

def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    df['date'] = pd.to_datetime(df['date'])

    # Hónap
    df['month'] = df['date'].dt.month

    # Hét napja (0 = hétfő, 6 = vasárnap)
    df['day_of_week'] = df['date'].dt.dayofweek

    # Hétvége?
    df['is_weekend'] = df['day_of_week'] >= 5

    # Negyedév
    df['quarter'] = df['date'].dt.quarter

    # Hónap eleje
    df['is_start_of_month'] = df['date'].dt.day <= 5

    # Hónap vége (utolsó 3 nap)
    df['is_end_of_month'] = df['date'].dt.is_month_end | (df['date'].dt.days_in_month - df['date'].dt.day <= 5)


    return df


def add_user_monthly_stats(df: pd.DataFrame) -> pd.DataFrame:
    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.month
    df['year'] = df['date'].dt.year

    # Csoportosítás év-hónap-email alapján
    group = df.groupby(['email', 'year', 'month'])

    # Átlagos havi költés
    df['user_avg_monthly_expense'] = group['amount'].transform('mean')

    # Tranzakciók száma havonta
    df['user_transaction_count_month'] = group['amount'].transform('count')

    return df


import pandas as pd

def add_salary_related_features(
    df: pd.DataFrame,
    salary_amount: float = 5000,
    salary_cycle: int = 30
) -> pd.DataFrame:
    """
    A salary-hez kapcsolódó jellemzők dinamikus kiszámítása:
      - salary_amount: a fix összeg, amely salary tranzakciónak minősül.
      - salary_cycle: a fizetés ciklusának hossza napokban.

    Frissített oszlopok:
      - is_salary: Bool, hogy a tranzakció salary-e.
      - salary_date: csak a salary soroknál tartalmaz dátumot.
      - last_salary_date: az előző salary dátum email-csoporton belül (ffill).
      - days_since_last_salary: napok száma aktuális tranzakció és utolsó fizetés között.
      - days_until_next_salary: mennyi nap van még a következő fizetésig.
    """
    # 1) Biztonsági másolat
    df = df.copy()

    # 2) Dátum konvertálás
    df['date'] = pd.to_datetime(df['date'])  # Pandas datetime konverzió :contentReference[oaicite:0]{index=0}

    # 3) Helyes rendezés email és dátum szerint
    df = df.sort_values(by=['email', 'date'], ignore_index=True)  # Rendezés email→dátum :contentReference[oaicite:1]{index=1}

    # 4) Salary tranzakciók jelölése
    df['is_salary'] = (
        (df['tran_type'] == 'income') &
        (df['amount'] == salary_amount)
    )

    # 5) Salary dátumok elkülönítése
    df['salary_date'] = df['date'].where(df['is_salary'])  # csak salary soroknál marad dátum :contentReference[oaicite:2]{index=2}

    # 6) Utolsó fizetés dátuma csoporton belül
    df['last_salary_date'] = (
        df.groupby('email')['salary_date']
          .ffill()  # előrefill (forward fill) csoporton belül :contentReference[oaicite:3]{index=3}
    )

    # 7) Napok száma az utolsó fizetés óta
    df['days_since_last_salary'] = (
        (df['date'] - df['last_salary_date'])
          .dt.days  # timedelta → napok :contentReference[oaicite:4]{index=4}

    )
    print(df['days_since_last_salary'])


    # 8) Hiányzó napok pótlása (első fizetés előtt)
    df['days_since_last_salary'] = df['days_since_last_salary'] \
        .fillna(salary_cycle)  # NaN → ciklushossz :contentReference[oaicite:5]{index=5}

    # 9) Napok a következő fizetésig (negatív értékeket 0-ra kerekítve)
    df['days_until_next_salary'] = (
        salary_cycle - df['days_since_last_salary']
    )
    df['days_until_next_salary'] = df['days_until_next_salary'] \
        .clip(lower=0)  # negatív → 0 :contentReference[oaicite:6]{index=6}

    return df



def clip_outliers_zscore(df: pd.DataFrame, columns: list = None, threshold: float = 3.0) -> pd.DataFrame:
    """
    Z-score alapján levágja a kiugró értékeket a numerikus oszlopokban.

    Minden értéket a mean és standard deviation alapján korlátozunk úgy, hogy az ne lépje túl a megadott küszöböt.
    """
    if columns is None:
        columns = df.select_dtypes(include=[np.number]).columns.tolist()

    for col in columns:
        mean = df[col].mean()
        std = df[col].std()
        lower_bound = mean - threshold * std
        upper_bound = mean + threshold * std
        df[col] = df[col].clip(lower=lower_bound, upper=upper_bound)
    return df


def engineer_all_features(df: pd.DataFrame) -> pd.DataFrame:
    df = add_time_features(df)
    df = add_user_monthly_stats(df)
    df = add_salary_related_features(df)
    df = clip_outliers_zscore(df)
    df.to_csv("transactions_with_features.csv", index=False)
    return df
