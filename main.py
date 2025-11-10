import os
import uvicorn
from fastapi import FastAPI
from api.routes import router, profile, transactions
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()

app.include_router(profile.router, prefix="/api", tags=["profile"])
app.include_router(transactions.router, prefix="/api", tags=["transactions"])

origins = [
    "http://localhost:5173",
    "http://localhost:8080",
    "http://localhost",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/")
def root():
    return {"message": "Hello from Budgetify FastAPI!"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
