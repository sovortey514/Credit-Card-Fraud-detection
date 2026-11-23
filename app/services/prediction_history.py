"""Durable, privacy-conscious prediction history for the FastAPI service."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PATH = ROOT / "data" / "prediction_history.db"


class PredictionHistoryRepository:
    """Persist prediction metadata without storing raw PCA payloads."""

    def __init__(self, path: Path = DEFAULT_PATH) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS prediction_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    context_id TEXT,
                    transaction_time REAL NOT NULL,
                    amount_hash TEXT NOT NULL,
                    model TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    feature_version TEXT NOT NULL,
                    probability REAL NOT NULL,
                    threshold REAL NOT NULL,
                    is_fraud INTEGER NOT NULL,
                    latency_ms REAL NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_prediction_created ON prediction_history(created_at)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_prediction_model ON prediction_history(model)"
            )
            existing = {row[1] for row in connection.execute("PRAGMA table_info(prediction_history)").fetchall()}
            for column, definition in {
                "route": "TEXT NOT NULL DEFAULT 'approve'",
                "triggered_rules": "TEXT NOT NULL DEFAULT '[]'",
                "top_contributions": "TEXT NOT NULL DEFAULT '[]'",
            }.items():
                if column not in existing:
                    connection.execute(f"ALTER TABLE prediction_history ADD COLUMN {column} {definition}")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS analyst_dispositions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT NOT NULL,
                    disposition TEXT NOT NULL CHECK(disposition IN ('APPROVED', 'CONFIRMED_FRAUD', 'ESCALATED')),
                    reviewer_id TEXT NOT NULL,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                )
                """
            )

    def record(
        self,
        *,
        request_id: str,
        source: str,
        context_id: str | None,
        transaction_time: float,
        amount: float,
        model: str,
        model_version: str,
        feature_version: str,
        probability: float,
        threshold: float,
        is_fraud: bool,
        latency_ms: float,
        route: str = "approve",
        triggered_rules: list[dict[str, object]] | None = None,
        top_contributions: list[dict[str, object]] | None = None,
    ) -> int:
        amount_hash = hashlib.sha256(f"{float(amount):.12g}".encode()).hexdigest()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO prediction_history
                (request_id, source, context_id, transaction_time, amount_hash,
                 model, model_version, feature_version, probability, threshold,
                 is_fraud, route, triggered_rules, top_contributions, latency_ms, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request_id,
                    source,
                    context_id,
                    float(transaction_time),
                    amount_hash,
                    model,
                    model_version,
                    feature_version,
                    float(probability),
                    float(threshold),
                    int(is_fraud),
                    route,
                    json.dumps(triggered_rules or []),
                    json.dumps(top_contributions or []),
                    float(latency_ms),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            return int(cursor.lastrowid)

    def record_disposition(self, request_id: str, disposition: str, reviewer_id: str, notes: str = "") -> None:
        if disposition not in {"APPROVED", "CONFIRMED_FRAUD", "ESCALATED"}:
            raise ValueError("Invalid analyst disposition")
        with self._connect() as connection:
            found = connection.execute("SELECT 1 FROM prediction_history WHERE request_id = ?", (request_id,)).fetchone()
            if found is None:
                raise ValueError(f"Request ID {request_id} was not found")
            connection.execute(
                "INSERT INTO analyst_dispositions (request_id, disposition, reviewer_id, notes, created_at) VALUES (?, ?, ?, ?, ?)",
                (request_id, disposition, reviewer_id, notes, datetime.now(timezone.utc).isoformat()),
            )

    def summary(self, limit: int = 1000) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS total,
                       COALESCE(SUM(is_fraud), 0) AS alerts,
                       COALESCE(AVG(latency_ms), 0) AS average_latency_ms
                FROM prediction_history
                """
            ).fetchone()
            latencies = [
                float(item[0])
                for item in connection.execute(
                    "SELECT latency_ms FROM prediction_history ORDER BY id DESC LIMIT ?",
                    (max(1, min(int(limit), 10_000)),),
                ).fetchall()
            ]
        latencies.sort()
        p95 = latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))] if latencies else 0.0
        total = int(row["total"])
        return {
            "total_predictions": total,
            "fraud_alerts": int(row["alerts"]),
            "alert_rate": (int(row["alerts"]) / total) if total else 0.0,
            "average_latency_ms": float(row["average_latency_ms"]),
            "p95_latency_ms": p95,
        }

    def recent(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM prediction_history ORDER BY id DESC LIMIT ?",
                (max(1, min(int(limit), 500)),),
            ).fetchall()
        return [dict(row) for row in rows]
