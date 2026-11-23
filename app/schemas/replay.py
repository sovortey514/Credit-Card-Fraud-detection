"""Schemas for replay stream configuration and scored events."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ReplaySpeed = Literal[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 50, 100, 250]


class ReplayEvent(BaseModel):
    sequence: int = Field(..., ge=0)
    time_seconds: float
    amount: float
    model: Literal["xgboost", "random_forest"]
    fraud_probability: float
    is_fraud: bool
    threshold: float
    ml_probability: float
    route: Literal["approve", "step_up", "flag"]
    triggered_rules: list[dict[str, object]] = Field(default_factory=list)
    velocity: dict[str, float | int] = Field(default_factory=dict)
    request_id: str
    top_contributions: list[dict[str, object]] = Field(default_factory=list)
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
