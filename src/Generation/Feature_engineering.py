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


def add_salary_related_features(df: pd.DataFrame) -> pd.DataFrame:
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(by=['email', 'date'])  # fontos a sorrend!

    # Új oszlop: salary-like tranzakció
    df['is_salary'] = (df['tran_type'] == 'income') & (df['amount'] == 5000)

    # Segédoszlop: utolsó salary dátum
    df['last_salary_date'] = (
        df[df['is_salary']]
        .groupby('email')['date']
        .transform(lambda x: x.ffill())
    )

    # Eltérés napokban
    df['days_since_last_salary'] = (df['date'] - df['last_salary_date']).dt.days

    # Lehetőség: következő salary nap becslése (ha érdekel)
    # Tipp: a salaryk közt eltelt napok átlagát megnézhetjük:
    # --> ehelyett most csak dummy 30 nappal számolunk
    df['days_until_next_salary'] = 30 - df['days_since_last_salary']
    df['days_until_next_salary'] = df['days_until_next_salary'].clip(lower=0)

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
    return df
