"""FastAPI application entry point for credit-card fraud inference."""

from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(title="Credit Card Fraud Detection API", version="1.0.0")
app.include_router(router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}
