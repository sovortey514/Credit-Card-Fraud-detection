"""Schemas for replay stream configuration and scored events."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ReplaySpeed = Literal[10, 50, 100, 250]


class ReplayEvent(BaseModel):
    sequence: int = Field(..., ge=0)
    time_seconds: float
    amount: float
    model: Literal["xgboost", "random_forest"]
    fraud_probability: float
    is_fraud: bool
    threshold: float
    latency_ms: float
    pca_features: dict[str, float]


class ReplayComplete(BaseModel):
    type: Literal["complete"] = "complete"
    emitted: int
    acknowledged: int
    dropped: int


class ReplayAck(BaseModel):
    type: Literal["ack"]
    sequence: int = Field(..., ge=0)
