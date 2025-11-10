import pandas as pd
import numpy as np

def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    df['date'] = pd.to_datetime(df['date'])

    df['month'] = df['date'].dt.month
    df['year'] = df['date'].dt.year
    df['day_of_week'] = df['date'].dt.dayofweek
    df['is_weekend'] = df['day_of_week'] >= 5
    df['quarter'] = df['date'].dt.quarter
    df['is_start_of_month'] = df['date'].dt.day <= 5
    df['is_end_of_month'] = df['date'].dt.is_month_end | (df['date'].dt.days_in_month - df['date'].dt.day <= 5)

    # Plusz jellemzők
    df['week_of_year'] = df['date'].dt.isocalendar().week
    df['day_of_month'] = df['date'].dt.day
    df['days_in_month'] = df['date'].dt.days_in_month

    return df

def add_user_monthly_stats(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df[df['internal_transfer'] == 'none']  # csak valós tranzakciók

    group = df.groupby(['user_id', 'year', 'month'])

    df['user_avg_monthly_expense'] = group['amount'].transform('mean')
    df['user_transaction_count_month'] = group['amount'].transform('count')
    df['user_total_monthly_expense'] = group['amount'].transform('sum')
    df['user_max_transaction_month'] = group['amount'].transform('max')
    df['user_min_transaction_month'] = group['amount'].transform('min')

    return df

def add_salary_related_features(
    df: pd.DataFrame,
    salary_amount: float = 5000,
    salary_cycle: int = 30
) -> pd.DataFrame:
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(by=['user_id', 'date'], ignore_index=True)

    df['is_salary'] = (df['tran_type'] == 'income') & (df['amount'] == salary_amount)
    df['salary_date'] = df['date'].where(df['is_salary'])

    df['last_salary_date'] = df.groupby('user_id')['salary_date'].ffill()
    df['days_since_last_salary'] = (df['date'] - df['last_salary_date']).dt.days
    df['days_since_last_salary'] = df['days_since_last_salary'].fillna(salary_cycle)
    df['days_until_next_salary'] = (salary_cycle - df['days_since_last_salary']).clip(lower=0)

    return df

def clip_outliers_zscore(df: pd.DataFrame, columns: list = None, threshold: float = 3.0) -> pd.DataFrame:
    if columns is None:
        columns = df.select_dtypes(include=[np.number]).columns.tolist()
    for col in columns:
        mean = df[col].mean()
        std = df[col].std()
        lower = mean - threshold * std
        upper = mean + threshold * std
        df[col] = df[col].clip(lower=lower, upper=upper)
    return df

def add_category_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Kategória-alapú jellemzők: átlag, tranzakciószám, százalékos arány a hónaphoz képest
    """
    df = df.copy()
    df = df[df['internal_transfer'] == 'none']

    # Csoportosítás user-hónap-kategória szerint
    group = df.groupby(['user_id', 'year', 'month', 'category'])
    df['category_avg'] = group['amount'].transform('mean')
    df['category_count'] = group['amount'].transform('count')

    # Kategória arány a havi összes költéshez képest
    monthly_group = df.groupby(['user_id', 'year', 'month'])['amount'].transform('sum')
    df['category_pct_of_month'] = df['amount'] / monthly_group

    return df

def engineer_all_features(df: pd.DataFrame) -> pd.DataFrame:
    # csak a valós tranzakciókat tartjuk
    df = df[df['internal_transfer'] == 'none'].copy()

    df = add_time_features(df)
    df = add_user_monthly_stats(df)
    df = add_salary_related_features(df)
    df = add_category_features(df)

    # Clip outliers a numerikus mezőkön
    df = clip_outliers_zscore(df)

    # Mentés CSV-be (opcionális)
    df.to_csv("transactions_with_features.csv", index=False)

    return df
