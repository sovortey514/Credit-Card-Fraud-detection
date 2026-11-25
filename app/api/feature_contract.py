"""Explicit-history feature transformation endpoint for the F0/F1 contract."""
from functools import lru_cache
from pathlib import Path
from typing import Literal

import joblib
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.schemas.creditcard import CreditCardTransaction

router = APIRouter(prefix="/api/v1", tags=["feature-engineering"])
ROOT = Path(__file__).resolve().parents[2]


class FeatureRequest(BaseModel):
    transaction: CreditCardTransaction
    feature_set: Literal["F0", "F1"] = "F1"
    history: list[float] = Field(default_factory=list, max_length=1000)
    last_time: float | None = None


@lru_cache(maxsize=2)
def load_transformer(feature_set: str):
    return joblib.load(ROOT / "models" / "feature_contract" / f"{feature_set.lower()}_preprocessing.joblib").named_steps["features"]


@router.post("/features")
def features(request: FeatureRequest):
    try:
        values, history, last_time = load_transformer(request.feature_set).transform_one(
            request.transaction.model_dump(), request.history, request.last_time)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail="Feature pipeline has not been fitted") from error
    return {"feature_set": request.feature_set, "features": values, "history": history, "last_time": last_time}
