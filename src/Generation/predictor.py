# src/predictor.py

import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from data_loader import load_global_data

class MonthlySpendingPredictor:
    """
    Osztály, ami betölti az adatokat, tréning nélkül
    csak a betanított modellt használva havi predikciót készít.
    """
    def __init__(self, model, numerical, categorical):
        # Preprocessor létrehozása
        num_pipe = Pipeline([
            ('imputer', SimpleImputer()),
            ('scaler', StandardScaler())
        ])
        cat_pipe = Pipeline([
            ('imputer', SimpleImputer(strategy='most_frequent')),
            ('ohe', OneHotEncoder(handle_unknown='ignore'))
        ])
        self.preprocessor = ColumnTransformer([
            ('num', num_pipe, numerical),
            ('cat', cat_pipe, categorical)
        ])
        self.model = model
        self.numerical = numerical
        self.categorical = categorical

    def predict_monthly(self, email: str) -> pd.DataFrame:
        # 1) Adatok betöltése
        df = load_global_data(email)
        if df.empty:
            return pd.DataFrame(columns=['date','monthly_pred'])  # üres visszatérés :contentReference[oaicite:11]{index=11}

        # 2) Feature matrix előkészítése
        X = df[self.numerical + self.categorical]
        X_proc = self.preprocessor.fit_transform(X)  # egyszeri fit, mert batch predikció :contentReference[oaicite:12]{index=12}

        # 3) Predikció és havi aggregálás
        df['pred'] = self.model.predict(X_proc)
        df['date'] = pd.to_datetime(df['date'])
        monthly = (df.set_index('date')['pred']
                     .resample('M').sum()
                     .reset_index(name='monthly_pred')
                  )  # resample a DatetimeIndex-en :contentReference[oaicite:13]{index=13}

        return monthly
