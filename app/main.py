"""FastAPI application entry point for credit-card fraud inference."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.feature_contract import router as feature_router

app = FastAPI(title="Credit Card Fraud Detection API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
app.include_router(router)
app.include_router(feature_router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}
