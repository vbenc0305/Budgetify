import os
import logging
import uvicorn
from fastapi import FastAPI
from api.routes import profile, transactions, stats
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse

# import FirebaseUnavailable for global handler
from db.firebase_client import FirebaseUnavailable

# configure logging early
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger(__name__)
logger.debug("main module imported")

app = FastAPI()

# global exception handler for FirebaseUnavailable
@app.exception_handler(FirebaseUnavailable)
async def firebase_unavailable_handler(request: Request, exc: FirebaseUnavailable):
    logger.error(f"Firebase unavailable (global handler): {exc}")
    return JSONResponse(status_code=503, content={"detail": "Firebase unavailable: " + str(exc)})

logger.debug("Including routers")
app.include_router(profile.router, prefix="/api", tags=["profile"])
app.include_router(transactions.router, prefix="/api", tags=["transactions"])
app.include_router(stats.router, prefix="/api", tags=["stats"])

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
    logger.debug("root endpoint called")
    return {"message": "Hello from Budgetify FastAPI!"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8081))
    logger.info(f"Starting uvicorn on 0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
