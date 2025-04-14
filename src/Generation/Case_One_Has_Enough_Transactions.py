import pandas as pd
from sklearn.linear_model import Ridge, Lasso
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score

from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split, GridSearchCV

from src.DAO.DAOimpl import FirebaseDAO
from src.Generation.Feature_engineering import engineer_all_features


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
data = get_all_transactions("aliciacantu@example.com")
df = pd.DataFrame(data)

if df.empty:
    raise ValueError("Nincs elérhető tranzakció az adott emailhez.")

df = engineer_all_features(df)

# --- 2. Célváltozó (target) definiálása ---
TARGET = 'amount'
if TARGET not in df.columns:
    raise ValueError(f"A '{TARGET}' oszlop nem található meg a dataframe-ben.")

# --- 3. Feature lista definiálása ---
numerical_features = [
    'month', 'day_of_week', 'quarter',
    'user_avg_monthly_expense', 'user_transaction_count_month',
    'days_since_last_salary', 'days_until_next_salary'
]

categorical_features = [
    'tran_type', 'is_weekend', 'is_start_of_month', 'is_end_of_month'
]

# Csak azokkal az oszlopokkal dolgozzunk, amik ténylegesen léteznek
existing_numerical = [col for col in numerical_features if col in df.columns]
existing_categorical = [col for col in categorical_features if col in df.columns]

# --- 4. Preprocessing pipeline ---
numeric_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy="mean")),
    ('scaler', StandardScaler())
])

categorical_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='most_frequent')),
    ('onehot', OneHotEncoder(handle_unknown='ignore'))
])

preprocessor = ColumnTransformer(
    transformers=[
        ('num', numeric_transformer, existing_numerical),
        ('cat', categorical_transformer, existing_categorical)
    ]
)

# --- 5. Target és feature szeparáció ---
X = df[existing_numerical + existing_categorical]
y = df[TARGET]

# --- 6. Train-test split ---
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.5, random_state=42)

# --- 7. Transzformálás ---
X_train_processed = preprocessor.fit_transform(X_train)
X_test_processed = preprocessor.transform(X_test)

# --- 8. Lasso modell betanítása és GridSearch ---
lasso = Lasso(max_iter=10000)

param_grid = {'alpha': [0.01, 0.1, 1.0, 5.0, 10.0, 50.0, 100.0]}
grid_search = GridSearchCV(lasso, param_grid, cv=5, scoring='neg_mean_squared_error')
grid_search.fit(X_train_processed, y_train)

best_lasso = grid_search.best_estimator_
print(f"🏅 Legjobb alpha érték: {grid_search.best_params_['alpha']}")

# --- 9. Predikció és értékelés ---
y_pred = best_lasso.predict(X_test_processed)

mse = mean_squared_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print(f"📉 Teszt MSE: {mse:.2f}")
print(f"📈 Teszt R² score: {r2:.4f}")

# --- 10. Teljes adat predikció és mentés ---
X_all = df[existing_numerical + existing_categorical]
X_all_processed = preprocessor.transform(X_all)
df['predicted_amount'] = best_lasso.predict(X_all_processed)

# --- 11. Feature fontosságok megtekintése ---
feature_names = preprocessor.get_feature_names_out()
coefficients = best_lasso.coef_

lasso_feature_importance = pd.DataFrame({
    'Feature': feature_names,
    'Coefficient': coefficients
}).sort_values(by="Coefficient", key=abs, ascending=False)

print("\n🔍 Lasso által legfontosabbnak ítélt jellemzők:")
print(lasso_feature_importance.head(10))

# --- 12. Vizualizáció ---
import matplotlib.pyplot as plt

plt.figure(figsize=(10, 6))
plt.scatter(y_test, y_pred, alpha=0.6, color='coral')
plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], '--', color='navy')
plt.xlabel("Valós érték")
plt.ylabel("Predikált érték")
plt.title("🎯 Valós vs Predikált értékek (Lasso Regression)")
plt.grid(True)
plt.tight_layout()
plt.show()

