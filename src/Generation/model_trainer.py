# src/model_trainer.py

from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.linear_model import Ridge, Lasso, LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from data_loader import load_global_data

def train_for_test(email: str):
    """
    Teszt-predikció: betölti a korábbi adatokat, felépíti a pipeline-t,
    grid search-el kiválasztja a legjobb modellt és kiértékeli.
    """
    df = load_global_data(email)
    if df.empty:
        raise ValueError("Nincsenek tranzakciók a teszthez")  # egyszerű hiba kezelés :contentReference[oaicite:6]{index=6}

    # 1) Feature és target szeparálás
    X = df[['month','day_of_week','quarter']]
    y = df['amount']

    # 2) Train-test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.5, random_state=42
    )  # reprodukálható véletlenszerűség :contentReference[oaicite:7]{index=7}

    # 3) Modellek definiálása + GridSearch
    models = {
        'LinearRegression': LinearRegression(),
        'Ridge': GridSearchCV(Ridge(), {'alpha': [0.1, 1.0]}, cv=3),
        'Lasso': GridSearchCV(Lasso(max_iter=5000), {'alpha': [0.1, 1.0]}, cv=3),
        'RF': GridSearchCV(RandomForestRegressor(), {'n_estimators': [50], 'max_depth': [5]}, cv=3)
    }

    results = {}
    for name, m in models.items():
        m.fit(X_train, y_train)  # itt a Pipeline nélküli példa :contentReference[oaicite:8]{index=8}
        estimator = getattr(m, 'best_estimator_', m)
        preds = estimator.predict(X_test)
        results[name] = {
            'mse': mean_squared_error(y_test, preds),
            'r2': r2_score(y_test, preds)
        }

    return results  # a unit-test itt tudja ellenőrizni az értékeket :contentReference[oaicite:9]{index=9}
