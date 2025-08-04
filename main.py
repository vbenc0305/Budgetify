import os
import uvicorn
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Hello from Budgetify FastAPI!"}

@app.get("/predict")
def predict():
    return {"prediction": "Coming soon... 🔮"}

if __name__ == "__main__":
    # Először próbáljuk meg a környezeti változót használni
    port = int(os.getenv("PORT", 8080))  # Alapértelmezett érték: 8080
    uvicorn.run(app, host="0.0.0.0", port=port)
