from typing import Optional

import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge


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

# --- ÚJ: monthly panel + exog készítő, leakage ellenőrzéssel ---
def build_monthly_panel_from_tx(df: pd.DataFrame, uid_local: Optional[str] = None,
                                date_col='date', uid_col='user_id', amount_col='amount') -> pd.DataFrame:
    """
    Átalakítja a tranzakciós DF-et user-month panel-re.
    Ha nincs user_id oszlop, beállítja a uid_local-t minden sorra (single-uid eset).
    """
    df = df.copy()
    # ha nincs user az adaton, adjuk hozzá (single-uid mode)
    if uid_col not in df.columns:
        df[uid_col] = uid_local if uid_local is not None else "unknown_user"

    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    # biztosítsuk a year/month oszlopokat (ha engineer_all_features generálta, ok)
    df['year'] = df[date_col].dt.year
    df['month'] = df[date_col].dt.month
    # alap aggregációk per user-month
    agg = df.groupby([uid_col, 'year', 'month']).agg(
        y_sum=(amount_col, 'sum'),
        y_mean=(amount_col, 'mean'),
        y_count=(amount_col, 'count'),
        y_max=(amount_col, 'max'),
        y_min=(amount_col, 'min'),
    ).reset_index()

    # kiegészítő jellemzők, ha elérhetők a raw trxn-ben
    # pl. user_avg_monthly_expense, user_transaction_count_month már lehet engineered mező
    # összekapcsoljuk a month-level engineered mezőket (ha léteznek)
    # merge példa: ha a df tartalmaz 'user_avg_monthly_expense' akkor használjuk
    extra_cols = [c for c in ['user_avg_monthly_expense', 'user_transaction_count_month',
                               'user_total_monthly_expense', 'user_max_transaction_month',
                               'user_min_transaction_month', 'top_category', 'top_category_pct',
                               'category_pct_of_month', 'is_salary', 'salary_count'] if c in df.columns]
    if extra_cols:
        # vegyük a legaggregáltabb (összeg vagy mean) értékeket per hónap, merge
        extras = df.groupby([uid_col, 'year', 'month'])[extra_cols].first().reset_index()
        agg = agg.merge(extras, on=[uid_col, 'year', 'month'], how='left')

    # dátum index: month-end
    agg['date'] = pd.to_datetime(agg[['year', 'month']].assign(day=1)) + pd.offsets.MonthEnd(0)
    agg = agg.sort_values([uid_col, 'date']).reset_index(drop=True)
    return agg


def make_monthly_exog_no_leakage(panel: pd.DataFrame, uid_col='user_id',
                                   date_col='date', shift_periods=1, keep_cols=None) -> pd.DataFrame:
    """
    Kiválasztja a panelből az exog feature-öket és SHIFT-eli őket (t-re vonatkozó jellemzők = t-1 információ).
    shift_periods default 1 month -> exog_at_time_t = features_from_previous_month
    Visszatér egy DataFrame-pel, index: date, suitable to be joined to monthly_series.
    """
    panel = panel.copy().sort_values([uid_col, date_col])
    if keep_cols is None:
        # vegyük a numerikus+bool oszlopokat, kivéve y_sum és a csoportosító mezők
        exclude = {uid_col, 'year', 'month', date_col, 'y_sum', 'y_mean', 'y_count', 'y_max', 'y_min'}
        keep_cols = [c for c in panel.columns if c not in exclude and (np.issubdtype(panel[c].dtype, np.number) or panel[c].dtype == 'bool' or panel[c].dtype.name == 'category')]
    # csak a szükséges oszlopok
    cols = [uid_col, date_col] + keep_cols
    exog = panel[cols].copy()
    # shifteljük per user csoportban, hogy ne legyen target leakage
    exog = exog.sort_values([uid_col, date_col])
    exog_shifted = exog.groupby(uid_col).shift(shift_periods)
    # restore identifier/date columns for alignment, then drop uid_col before returning
    exog_shifted[uid_col] = exog[uid_col].values
    exog_shifted[date_col] = exog[date_col].values
    # indexáljuk date-re
    exog_shifted = exog_shifted.set_index(date_col)
    # cast bool->int
    for c in exog_shifted.select_dtypes(include=['bool']).columns:
        exog_shifted[c] = exog_shifted[c].astype('int')

    # Drop identifier column (like user_id) so exog is purely numeric
    if uid_col in exog_shifted.columns:
        exog_shifted = exog_shifted.drop(columns=[uid_col])

    # Coerce all columns to numeric where possible (non-numeric -> NaN) and fill
    for c in exog_shifted.columns:
        if not np.issubdtype(exog_shifted[c].dtype, np.number):
            exog_shifted[c] = pd.to_numeric(exog_shifted[c], errors='coerce')

    # forward-fill then fill remaining NaNs with 0.0
    exog_shifted = exog_shifted.ffill().fillna(0.0)

    return exog_shifted


def fit_and_forecast_time_regression_with_exog(series: pd.Series, exog_df: pd.DataFrame,
                                               steps=10, lags_for_features=3, alpha=0.8):
    """
    Ridge-based time-regression ami használ exog-ot (már shift-elve, azaz leakage-mentes).
    - series: pd.Series indexed by date (month-end)
    - exog_df: pd.DataFrame indexed by same dates, columns = exog features (already shift-elt)
    Forecast-ol iteratív módon; a jövőbeli exog-okat naivan a legutolsó ismert sorral töltjük.
    (Ha vannak determinisztikus exogok mint month_sin/cos, akkor érdemes azokat előre generálni.)
    """
    try:
        # align
        exog = exog_df.reindex(series.index)
        # ensure exog is numeric and has no non-numeric columns
        exog = exog.apply(pd.to_numeric, errors='coerce')
        exog = exog.ffill().fillna(0.0)
        n = len(series)
        if n < 3:
            return None, None, None

        df = pd.DataFrame({'y': series.values}, index=series.index)
        used_lags = min(lags_for_features, max(1, n - 2))
        for i in range(1, used_lags + 1):
            df[f'lag{i}'] = df['y'].shift(i)

        # join exog (already shift-elt externally)
        df = df.join(exog, how='left')
        df = df.dropna()  # biztosítsuk, hogy nincs NaN a trainingben

        lag_features = [f'lag{i}' for i in range(1, used_lags + 1)]
        exog_features = [c for c in exog.columns]
        feat_cols = lag_features + exog_features

        X = df[feat_cols].values
        y = df['y'].values

        reg = Ridge(alpha=alpha, fit_intercept=True, random_state=42).fit(X, y)

        # forecasting iteratív módon
        last_vals = list(series.values[-used_lags:])
        last_exog = exog.iloc[-1].fillna(0.0).values.tolist() if len(exog) > 0 else [0.0] * len(exog_features)
        preds = []
        last_t_index = series.index[-1]
        for step in range(steps):
            # készítsük el a feature vektort: lagok + exog (jövőbeli exog=legutóbbi ismert)
            feat = np.array(last_vals[-used_lags:] + last_exog).reshape(1, -1)
            yhat = float(reg.predict(feat)[0])
            preds.append(yhat)
            # update last_vals (autoregresszív mód)
            last_vals.append(yhat)
            # naiv: exog nem változik -> marad last_exog (option: frissítsd month_sin/month_cos ha vannak)
        idx = pd.date_range(start=series.index[-1] + pd.offsets.MonthEnd(1), periods=steps, freq="ME")
        preds = pd.Series(preds, index=idx, name="time_reg_exog_forecast")
        preds = preds.clip(lower=0.0)
        return reg, preds, None

    except Exception as e:
        print("⚠️ Time-reg (Ridge+exog) fit error:", e)
        return None, None, None

def make_exog_forecast_from_last_known(exog_shifted: pd.DataFrame, steps: int = 10) -> Optional[pd.DataFrame]:
    """
    Készít egy naiv exog_forecast-et a SARIMAX vagy exog-aware modell számára.
    - determinisztikus mezőket (pl. month_sin/month_cos, month, is_start_of_month) újraszámoljuk,
    - a többi mezőt a legutolsó ismert értékkel (ffill) töltjük.
    Visszatér: DataFrame indexed by future month-ends, vagy None ha exog_shifted None/üres.
    """
    if exog_shifted is None or len(exog_shifted) == 0:
        return None
    last_idx = exog_shifted.index.max()
    future_idx = pd.date_range(start=last_idx + pd.offsets.MonthEnd(1), periods=steps, freq="ME")
    fut = pd.DataFrame(index=future_idx, columns=exog_shifted.columns, dtype=float)

    # regenerate deterministic time-based cols if present
    if 'month_sin' in exog_shifted.columns or 'month_cos' in exog_shifted.columns or 'month' in exog_shifted.columns:
        months = future_idx.month
        if 'month_sin' in fut.columns:
            fut['month_sin'] = np.sin(2 * np.pi * (months - 1) / 12.0)
        if 'month_cos' in fut.columns:
            fut['month_cos'] = np.cos(2 * np.pi * (months - 1) / 12.0)
        if 'month' in fut.columns:
            fut['month'] = months

    # boolean deterministics
    if 'is_start_of_month' in fut.columns:
        fut['is_start_of_month'] = (future_idx.day <= 5).astype(int)
    if 'is_end_of_month' in fut.columns:
        fut['is_end_of_month'] = ((future_idx.is_month_end) | ((future_idx.days_in_month - future_idx.day) <= 5)).astype(int)

    # ffill többi mezőt a legutolsó ismert értékkel
    # take last known row and coerce numeric values
    last_row = exog_shifted.iloc[-1]
    last_row = last_row.apply(pd.to_numeric, errors='coerce').fillna(0.0)
    for c in fut.columns:
        if fut[c].isna().all():
            try:
                fut[c] = last_row.get(c, 0.0)
            except Exception:
                fut[c] = 0.0

    # cast bools/ints helyesen
    for c in fut.columns:
        if c in exog_shifted.columns and exog_shifted[c].dtype == 'bool':
            fut[c] = fut[c].astype(int)
        # ensure numeric
        fut[c] = pd.to_numeric(fut[c], errors='coerce').fillna(0.0)
    return fut
