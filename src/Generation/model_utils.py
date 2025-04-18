# src/Utils/model_utils.py
import os
import joblib
from sklearn.pipeline import Pipeline

def save_pipeline(email: str, model, preprocessor, directory="models"):
    os.makedirs(directory, exist_ok=True)
    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('model', model)
    ])
    filepath = os.path.join(directory, f"{email}_pipeline.pkl")
    joblib.dump(pipeline, filepath)
    print(f"💾 Modell elmentve ide: {filepath}")
