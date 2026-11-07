"""SQLite persistence for predictions and analyst-confirmed labels."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "fraud_detection.db"


def init_db() -> None:
    """Initialize the transaction log schema if it does not exist."""
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS transaction_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                amount REAL NOT NULL,
                status TEXT NOT NULL,
                decision TEXT NOT NULL,
                risk_score REAL NOT NULL,
                reasons TEXT NOT NULL,
                confirmed_label INTEGER DEFAULT NULL
            )
            """
        )


def log_transaction(
    amount: float,
    status: str,
    decision: str,
    risk_score: float,
    reasons: list[str],
) -> int:
    """Log a prediction and return its database ID."""
    init_db()
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute(
            """
            INSERT INTO transaction_logs
                (timestamp, amount, status, decision, risk_score, reasons)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                float(amount),
                status,
                decision,
                float(risk_score),
                json.dumps(reasons),
            ),
        )
        return int(cursor.lastrowid)


def update_analyst_feedback(transaction_id: int, confirmed_label: int) -> None:
    """Attach an analyst label: ``1`` for fraud or ``0`` for legitimate."""
    if confirmed_label not in {0, 1}:
        raise ValueError("confirmed_label must be 0 or 1")

    init_db()
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute(
            """
            UPDATE transaction_logs
            SET confirmed_label = ?
            WHERE id = ?
            """,
            (confirmed_label, transaction_id),
        )
        if cursor.rowcount == 0:
            raise ValueError(f"Transaction ID {transaction_id} was not found")


def load_labeled_transactions() -> list[dict[str, Any]]:
    """Return analyst-labeled rows for a future retraining job."""
    init_db()
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT id, timestamp, amount, status, decision, risk_score,
                   reasons, confirmed_label
            FROM transaction_logs
            WHERE confirmed_label IS NOT NULL
            ORDER BY id
            """
        ).fetchall()
    return [dict(row) for row in rows]


def load_transactions(limit: int = 100) -> pd.DataFrame:
    """Return the most recent transaction logs for the analyst dashboard."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql_query(
            "SELECT * FROM transaction_logs ORDER BY id DESC LIMIT ?",
            conn,
            params=(max(1, min(int(limit), 500)),),
        )
    finally:
        conn.close()
