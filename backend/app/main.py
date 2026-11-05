from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from dotenv import load_dotenv
from app.routes import mandi
from app.routes import satellite
from app.routes import intelligence
import os

load_dotenv()
from app.routes import disease, soil, weather, assistant

app = FastAPI(title="HAL Lite API", version="1.0.0",
              description="Context-aware agricultural advisory demo")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://192.168.31.166:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "HAL Lite API"}

app.include_router(disease.router, prefix="/api/disease", tags=["Disease"])
app.include_router(soil.router, prefix="/api/soil", tags=["Soil"])
app.include_router(weather.router, prefix="/api/weather", tags=["Weather"])
app.include_router(assistant.router, prefix="/api/assistant", tags=["Assistant"])
app.include_router(mandi.router)
app.include_router(satellite.router)
app.include_router(intelligence.router)