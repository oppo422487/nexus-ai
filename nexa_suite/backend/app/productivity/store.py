"""Small local SQLite store for memories, notes, calendar, drafts and profiles."""

from __future__ import annotations

import datetime as dt
import sqlite3
import threading
import uuid

from app.core.runtime_paths import data_dir

DB_PATH = data_dir() / "nexa_productivity.sqlite3"
_LOCK = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
  id TEXT PRIMARY KEY, profile TEXT NOT NULL, fact TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS notes (
  id TEXT PRIMARY KEY, profile TEXT NOT NULL, kind TEXT NOT NULL, text TEXT NOT NULL,
  status TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS calendar_events (
  id TEXT PRIMARY KEY, profile TEXT NOT NULL, title TEXT NOT NULL, start_at TEXT,
  location TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS drafts (
  id TEXT PRIMARY KEY, profile TEXT NOT NULL, channel TEXT NOT NULL, recipient TEXT NOT NULL,
  subject TEXT NOT NULL, body TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS voice_profiles (
  id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, wake_word TEXT NOT NULL,
  language TEXT NOT NULL, created_at TEXT NOT NULL
);
"""


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn


def _insert(table: str, fields: dict[str, object]) -> dict:
    item = {"id": uuid.uuid4().hex, **fields, "created_at": _now()}
    columns = ", ".join(item)
    placeholders = ", ".join("?" for _ in item)
    with _LOCK:
        conn = _connect()
        try:
            conn.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", tuple(item.values()))
            conn.commit()
        finally:
            conn.close()
    return item


def _list(table: str, profile: str = "default", limit: int = 100) -> list[dict]:
    with _LOCK:
        conn = _connect()
        try:
            rows = conn.execute(
                f"SELECT * FROM {table} WHERE profile = ? ORDER BY created_at DESC LIMIT ?",
                (profile, max(1, min(limit, 500))),
            ).fetchall()
        finally:
            conn.close()
    return [dict(row) for row in rows]


def add_memory(fact: str, profile: str = "default") -> dict:
    return _insert("memories", {"profile": profile[:80], "fact": fact.strip()[:1000]})


def list_memories(profile: str = "default", limit: int = 50) -> list[dict]:
    return _list("memories", profile, limit)


def add_note(text: str, kind: str = "note", profile: str = "default") -> dict:
    selected_kind = kind if kind in {"note", "task", "shopping"} else "note"
    return _insert("notes", {"profile": profile[:80], "kind": selected_kind, "text": text.strip()[:1500], "status": "pending"})


def list_notes(profile: str = "default", kind: str | None = None, limit: int = 100) -> list[dict]:
    items = _list("notes", profile, limit)
    return [item for item in items if kind is None or item["kind"] == kind]


def set_note_status(note_id: str, status: str) -> bool:
    if status not in {"pending", "done", "dismissed"}:
        return False
    with _LOCK:
        conn = _connect()
        try:
            cursor = conn.execute("UPDATE notes SET status = ? WHERE id = ?", (status, note_id))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()


def add_calendar_event(title: str, start_at: str | None = None, location: str = "", profile: str = "default") -> dict:
    return _insert("calendar_events", {
        "profile": profile[:80], "title": title.strip()[:300], "start_at": start_at,
        "location": location.strip()[:300], "status": "scheduled",
    })


def list_calendar_events(profile: str = "default", limit: int = 100) -> list[dict]:
    return _list("calendar_events", profile, limit)


def add_draft(channel: str, recipient: str, body: str, subject: str = "", profile: str = "default") -> dict:
    return _insert("drafts", {
        "profile": profile[:80], "channel": channel[:30], "recipient": recipient.strip()[:200],
        "subject": subject.strip()[:300], "body": body.strip()[:3000], "status": "draft",
    })


def list_drafts(profile: str = "default", limit: int = 100) -> list[dict]:
    return _list("drafts", profile, limit)


def create_voice_profile(name: str, wake_word: str = "Nexa", language: str = "bn-BD") -> dict:
    clean_name = name.strip()[:80]
    with _LOCK:
        conn = _connect()
        try:
            existing = conn.execute("SELECT * FROM voice_profiles WHERE name = ?", (clean_name,)).fetchone()
            if existing:
                return dict(existing)
            item = {"id": uuid.uuid4().hex, "name": clean_name, "wake_word": wake_word.strip()[:80], "language": language[:20], "created_at": _now()}
            conn.execute(
                "INSERT INTO voice_profiles (id, name, wake_word, language, created_at) VALUES (?, ?, ?, ?, ?)",
                tuple(item.values()),
            )
            conn.commit()
            return item
        finally:
            conn.close()


def list_voice_profiles() -> list[dict]:
    with _LOCK:
        conn = _connect()
        try:
            rows = conn.execute("SELECT * FROM voice_profiles ORDER BY created_at DESC").fetchall()
        finally:
            conn.close()
    return [dict(row) for row in rows]


def dashboard_snapshot(profile: str = "default") -> dict:
    return {
        "memories": list_memories(profile), "notes": list_notes(profile),
        "calendar_events": list_calendar_events(profile), "drafts": list_drafts(profile),
        "voice_profiles": list_voice_profiles(),
    }
