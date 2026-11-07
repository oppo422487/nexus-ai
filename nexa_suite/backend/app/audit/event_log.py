"""Real SQLite audit event log for executed/blocked actions.

This is the working audit trail. The older preview-only audit endpoints are
kept unchanged for compatibility; this module records actual events.
"""

from __future__ import annotations

import datetime
import sqlite3
import threading
from app.core.runtime_paths import data_dir

AUDIT_DB_PATH = data_dir() / "nexa_audit_events.sqlite3"

_lock = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    source TEXT NOT NULL,
    intent TEXT NOT NULL,
    status TEXT NOT NULL,
    risk_level TEXT NOT NULL DEFAULT '',
    target TEXT NOT NULL DEFAULT '',
    message TEXT NOT NULL DEFAULT ''
)
"""


def _connect() -> sqlite3.Connection:
    AUDIT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(AUDIT_DB_PATH))
    conn.execute(_SCHEMA)
    return conn


def record_audit_event(
    source: str,
    intent: str,
    status: str,
    risk_level: str = "",
    target: str = "",
    message: str = "",
) -> bool:
    """Persist one audit event. Failures never raise into request handling."""
    try:
        with _lock:
            conn = _connect()
            try:
                conn.execute(
                    "INSERT INTO audit_events "
                    "(created_at, source, intent, status, risk_level, target, message) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        source[:64],
                        intent[:64],
                        status[:64],
                        risk_level[:64],
                        target[:256],
                        message[:512],
                    ),
                )
                conn.commit()
            finally:
                conn.close()
        return True
    except Exception:
        return False


def list_audit_events(limit: int = 50) -> list[dict]:
    limit = max(1, min(int(limit), 200))
    try:
        with _lock:
            conn = _connect()
            try:
                rows = conn.execute(
                    "SELECT id, created_at, source, intent, status, risk_level, target, message "
                    "FROM audit_events ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            finally:
                conn.close()
        return [
            {
                "id": row[0],
                "created_at": row[1],
                "source": row[2],
                "intent": row[3],
                "status": row[4],
                "risk_level": row[5],
                "target": row[6],
                "message": row[7],
            }
            for row in rows
        ]
    except Exception:
        return []


def get_audit_event_count() -> int:
    try:
        with _lock:
            conn = _connect()
            try:
                row = conn.execute("SELECT COUNT(*) FROM audit_events").fetchone()
            finally:
                conn.close()
        return int(row[0]) if row else 0
    except Exception:
        return 0
