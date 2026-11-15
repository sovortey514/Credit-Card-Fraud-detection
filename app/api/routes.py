"""Versioned fraud prediction and explanation endpoints."""

from __future__ import annotations

import asyncio
import json
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from app.schemas.creditcard import CreditCardTransaction, ExplanationResponse, PredictionResponse
from app.schemas.replay import ReplayAck, ReplayComplete
from app.services.model_service import CreditCardModelService
from app.services.replay_service import ALLOWED_SPEEDS, CreditCardReplayService, sse_message

router = APIRouter(prefix="/api/v1", tags=["credit-card-fraud"])
service = CreditCardModelService()
replay_service = CreditCardReplayService(service)


@router.post("/predict", response_model=PredictionResponse)
def predict(
    transaction: CreditCardTransaction,
    model: Literal["xgboost", "random_forest"] = Query("xgboost"),
) -> PredictionResponse:
    return service.predict(transaction, model)


@router.post("/explain", response_model=ExplanationResponse)
def explain(
    transaction: CreditCardTransaction,
    model: Literal["xgboost", "random_forest"] = Query("xgboost"),
    top_n: int = Query(3, ge=1, le=10),
) -> ExplanationResponse:
    return service.explain(transaction, model, top_n)


@router.get("/replay/stream")
async def replay_stream(
    speed: int = Query(10, description="Held-out replay speed in transactions per second"),
    model: Literal["xgboost", "random_forest"] = Query("xgboost"),
    limit: int | None = Query(None, ge=1, le=42_557),
) -> StreamingResponse:
    """Stream scored held-out transactions as Server-Sent Events."""
    if speed not in ALLOWED_SPEEDS:
        raise HTTPException(status_code=422, detail=f"speed must be one of {ALLOWED_SPEEDS}")

    async def stream():
        async for event in replay_service.events(speed, model, limit):
            yield sse_message(event)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@router.websocket("/replay/ws")
async def replay_websocket(websocket: WebSocket) -> None:
    """Push scored events and require an acknowledgement for every sequence ID."""
    await websocket.accept()
    emitted = 0
    acknowledged = 0
    try:
        configuration = await websocket.receive_json()
        speed = configuration.get("speed", 10)
        model = configuration.get("model", "xgboost")
        limit = configuration.get("limit")
        if speed not in ALLOWED_SPEEDS or model not in ("xgboost", "random_forest"):
            await websocket.close(code=1003, reason="Invalid replay configuration")
            return
        if limit is not None and (not isinstance(limit, int) or not 1 <= limit <= 42_557):
            await websocket.close(code=1003, reason="Invalid replay limit")
            return

        async for event in replay_service.events(speed, model, limit):
            await websocket.send_json(event.model_dump())
            emitted += 1
            ack = ReplayAck.model_validate(await websocket.receive_json())
            if ack.sequence != event.sequence:
                await websocket.close(code=1008, reason="Replay sequence acknowledgement mismatch")
                return
            acknowledged += 1
        complete = ReplayComplete(emitted=emitted, acknowledged=acknowledged, dropped=emitted - acknowledged)
        await websocket.send_json(complete.model_dump())
    except WebSocketDisconnect:
        return
    except (ValueError, json.JSONDecodeError):
        await websocket.close(code=1003, reason="Invalid replay acknowledgement")
