from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path

from ouri.config import DATA_DIR
from ouri.wellness.models import WellnessSnapshot

DB_PATH = DATA_DIR / "ouri.db"


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS wellness_snapshots (
            day TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    return conn


def save_snapshot(snapshot: WellnessSnapshot) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO wellness_snapshots (day, payload, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(day) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at
            """,
            (
                snapshot.day.isoformat(),
                snapshot.model_dump_json(),
                snapshot.captured_at.isoformat(),
            ),
        )
        conn.commit()


def load_snapshot(day: date | None = None) -> WellnessSnapshot | None:
    target = (day or date.today()).isoformat()
    with _connect() as conn:
        row = conn.execute(
            "SELECT payload FROM wellness_snapshots WHERE day = ?",
            (target,),
        ).fetchone()
    if not row:
        return None
    return WellnessSnapshot.model_validate(json.loads(row[0]))


def load_recent_snapshots(days: int = 7) -> list[WellnessSnapshot]:
    """Most recent ``days`` snapshots, ordered oldest -> newest."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT payload FROM wellness_snapshots ORDER BY day DESC LIMIT ?",
            (days,),
        ).fetchall()
    snapshots = [WellnessSnapshot.model_validate(json.loads(r[0])) for r in rows]
    return list(reversed(snapshots))
