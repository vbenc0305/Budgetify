import pandas as pd
import matplotlib.pyplot as plt

from sklearn.linear_model import Ridge, Lasso, LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.tree import plot_tree

from src.DAO.DAOimpl import FirebaseDAO
from src.Generation.Feature_engineering import engineer_all_features
from src.Generation.model_utils import save_pipeline



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

# --- 3. Feature lista definiálása ---
numerical_features = [
    'month', 'day_of_week', 'quarter',
    'user_avg_monthly_expense', 'user_transaction_count_month',
    'days_since_last_salary', 'days_until_next_salary'
]
categorical_features = [
    'tran_type', 'is_weekend', 'is_start_of_month', 'is_end_of_month'
]
existing_numerical = [col for col in numerical_features if col in df.columns]
existing_categorical = [col for col in categorical_features if col in df.columns]

# --- 4. Preprocessing pipeline ---
numeric_transformer = Pipeline([
    ('imputer', SimpleImputer()),
    ('scaler', StandardScaler())
])
categorical_transformer = Pipeline([
    ('imputer', SimpleImputer(strategy='most_frequent')),
    ('onehot', OneHotEncoder(handle_unknown='ignore'))
])
preprocessor = ColumnTransformer([
    ('num', numeric_transformer, existing_numerical),
    ('cat', categorical_transformer, existing_categorical)
])

# --- 5. Target és feature szeparáció ---
X = df[existing_numerical + existing_categorical]
y = df[TARGET]

# --- 6. Train-test split ---
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# --- 7. Transzformálás ---
X_train_processed = preprocessor.fit_transform(X_train)
X_test_processed = preprocessor.transform(X_test)

# --- 8. Modellek definiálása és GridSearch ---
models = {
    'LinearRegression': LinearRegression(),
    'Ridge': GridSearchCV(Ridge(), {'alpha': [0.01, 0.1, 1.0, 10.0]}, cv=5),
    'Lasso': GridSearchCV(Lasso(max_iter=10000), {'alpha': [0.01, 0.1, 1.0, 10.0]}, cv=5),
    'RandomForest': GridSearchCV(RandomForestRegressor(), {
        'n_estimators': [50, 100],
        'max_depth': [None, 5, 10]
    }, cv=5)
}

results = {}

for name, model in models.items():
    print(f"\n🤖 Modell tanítása: {name}")
    model.fit(X_train_processed, y_train)
    best_model = model.best_estimator_ if hasattr(model, 'best_estimator_') else model
    y_pred = best_model.predict(X_test_processed)
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    results[name] = {'model': best_model, 'mse': mse, 'r2': r2, 'y_pred': y_pred}
    print(f"  \U0001F4C9 MSE: {mse:.2f}, R²: {r2:.4f}")

# --- 9. Legjobb modell kiválasztása ---
best_model_name = min(results, key=lambda modelname: results[modelname]['mse'])
best_model_info = results[best_model_name]
print(f"\n🏆 Legjobb modell: {best_model_name} (MSE: {best_model_info['mse']:.2f})")

# --- 10. Teljes adat predikció és mentés ---
X_all = df[existing_numerical + existing_categorical]
X_all_processed = preprocessor.transform(X_all)
df['predicted_amount'] = best_model_info['model'].predict(X_all_processed)

# Mentsük el a preprocesszált adatokat egy CSV fájlba
df.to_csv("preprocessed_transactions_with_predictions.csv", index=False)
print("Preprocesszált adatok és predikciók elmentve a 'preprocessed_transactions_with_predictions.csv' fájlba.")

# Mentsük el a modellt és a pipelinet
user_email = "aliciacantu@gmail.com"
save_pipeline(user_email, best_model_info['model'], preprocessor)

# --- 10.1. Havi összegek számítása és kiírása ---
df['month'] = df['date'].dt.month  # Feltételezve, hogy van 'date' oszlopod, ami dátum típusú
monthly_sum = df.groupby('month')['amount'].sum()

print("\n📊 Havi összegek:")
print(monthly_sum)


# --- 11. Vizualizáció ---
plt.figure(figsize=(10, 6))
plt.scatter(y_test, best_model_info['y_pred'], alpha=0.6, color='coral')
plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], '--', color='navy')
plt.xlabel("Valós érték")
plt.ylabel("Predikált érték")
plt.title(f"🎯 Valós vs Predikált értékek ({best_model_name})")
plt.grid(True)
plt.tight_layout()
plt.show()


# Végy ki egy fát az erdőből
tree = best_model_info['model'].estimators_[0]

# Rajzold ki limitált mélységgel
plt.figure(figsize=(16, 8))
plot_tree(tree,
          max_depth=3,  # Csak a legfelső döntéseket rajzoljuk ki
          feature_names=preprocessor.get_feature_names_out(),
          filled=True,
          rounded=True,
          fontsize=10)  # Állítható a betűméret is
plt.title("🌳 Egy egyszerűbb fa a Random Forest erdőből (max depth = 3)")
plt.tight_layout()
plt.show()
