from pathlib import Path
from time import perf_counter
from fastapi.middleware.cors import CORSMiddleware

import joblib
import numpy as np
import pandas as pd

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "xgboost.joblib"

# 1. Create the FastAPI application FIRST
app = FastAPI(
    title="Money Transfer Fraud Detection API",
    version="1.0.0",
    description="Research prototype using PaySim data",
)

# 2. Add the homepage AFTER creating app

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/")
def home():
    return {
        "application": "Money Transfer Fraud Detection API",
        "status": "running",
        "documentation": "/docs",
        "health_check": "/health",
    }


# 3. Load the trained model
if not MODEL_PATH.exists():
    raise FileNotFoundError(f"Model not found: {MODEL_PATH}")

artifact = joblib.load(MODEL_PATH)

model = artifact["model"]
features = artifact["features"]
threshold = float(artifact["threshold"])
