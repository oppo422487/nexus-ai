"""Local SQLite reminder storage for Nexa AI.

Reminders are plain local records. Creating one requires explicit user
confirmation from the UI. No background execution, no notifications are
sent anywhere — the frontend polls for due reminders and shows them in-app.
"""

from __future__ import annotations

import datetime
import sqlite3
import threading
import uuid
import re
from app.core.runtime_paths import data_dir
from zoneinfo import ZoneInfo

REMINDERS_DB_PATH = data_dir() / "nexa_reminders.sqlite3"

MAX_TITLE_LENGTH = 200
MAX_NOTE_LENGTH = 1000

_lock = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS reminders (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    due_at TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL
)
"""

_OPTIONAL_COLUMNS = {
    "recurrence": "TEXT NOT NULL DEFAULT ''",
    "last_triggered_at": "TEXT",
}


def _connect() -> sqlite3.Connection:
    REMINDERS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(REMINDERS_DB_PATH))
    conn.execute(_SCHEMA)
    existing = {row[1] for row in conn.execute("PRAGMA table_info(reminders)").fetchall()}
    for name, declaration in _OPTIONAL_COLUMNS.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE reminders ADD COLUMN {name} {declaration}")
    conn.commit()
    return conn


def _row_to_dict(row: tuple) -> dict:
    return {
        "id": row[0],
        "title": row[1],
        "note": row[2],
        "due_at": row[3],
        "status": row[4],
        "created_at": row[5],
        "recurrence": row[6] or "",
        "last_triggered_at": row[7],
    }


def create_reminder(title: str, note: str = "", due_at: str | None = None, recurrence: str = "") -> dict:
    cleaned_title = (title or "").strip()[:MAX_TITLE_LENGTH]
    if not cleaned_title:
        return {"ok": False, "reminder": None, "error": "Reminder title is empty."}

    if due_at:
        try:
            datetime.datetime.fromisoformat(due_at)
        except ValueError:
            return {"ok": False, "reminder": None, "error": "due_at must be an ISO datetime string."}

    recurrence = (recurrence or "").strip().lower()
    if recurrence not in {"", "daily", "weekly", "monthly", "yearly"}:
        return {"ok": False, "reminder": None, "error": "Invalid recurrence value."}

    reminder = {
        "id": uuid.uuid4().hex,
        "title": cleaned_title,
        "note": (note or "").strip()[:MAX_NOTE_LENGTH],
        "due_at": due_at,
        "status": "pending",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "recurrence": recurrence,
        "last_triggered_at": None,
    }
    try:
        with _lock:
            conn = _connect()
            try:
                conn.execute(
                    "INSERT INTO reminders (id, title, note, due_at, status, created_at, recurrence, last_triggered_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        reminder["id"],
                        reminder["title"],
                        reminder["note"],
                        reminder["due_at"],
                        reminder["status"],
                        reminder["created_at"],
                        reminder["recurrence"],
                        reminder["last_triggered_at"],
                    ),
                )
                conn.commit()
            finally:
                conn.close()
        return {"ok": True, "reminder": reminder, "error": None}
    except Exception as exc:
        return {"ok": False, "reminder": None, "error": f"Reminder could not be saved: {exc}"}


def list_reminders(include_done: bool = True, limit: int = 100) -> list[dict]:
    limit = max(1, min(int(limit), 500))
    query = "SELECT id, title, note, due_at, status, created_at, recurrence, last_triggered_at FROM reminders"
    if not include_done:
        query += " WHERE status = 'pending'"
    query += " ORDER BY COALESCE(due_at, created_at) ASC LIMIT ?"
    try:
        with _lock:
            conn = _connect()
            try:
                rows = conn.execute(query, (limit,)).fetchall()
            finally:
                conn.close()
        return [_row_to_dict(r) for r in rows]
    except Exception:
        return []


def list_due_reminders() -> list[dict]:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        with _lock:
            conn = _connect()
            try:
                rows = conn.execute(
                    "SELECT id, title, note, due_at, status, created_at, recurrence, last_triggered_at FROM reminders "
                    "WHERE status = 'pending' AND due_at IS NOT NULL AND due_at <= ? "
                    "ORDER BY due_at ASC LIMIT 50",
                    (now,),
                ).fetchall()
            finally:
                conn.close()
        return [_row_to_dict(r) for r in rows]
    except Exception:
        return []


def set_reminder_status(reminder_id: str, status: str) -> dict:
    if status not in ("pending", "done", "dismissed"):
        return {"ok": False, "error": "Invalid reminder status."}
    try:
        with _lock:
            conn = _connect()
            try:
                row = conn.execute(
                    "SELECT due_at, recurrence FROM reminders WHERE id = ?", (reminder_id,)
                ).fetchone()
                if row and status == "done" and row[0] and row[1]:
                    due = datetime.datetime.fromisoformat(row[0])
                    if row[1] == "daily":
                        next_due = due + datetime.timedelta(days=1)
                    elif row[1] == "weekly":
                        next_due = due + datetime.timedelta(weeks=1)
                    elif row[1] == "monthly":
                        next_due = due + datetime.timedelta(days=30)
                    else:
                        next_due = due.replace(year=due.year + 1)
                    now = datetime.datetime.now(datetime.timezone.utc)
                    while next_due <= now:
                        next_due += datetime.timedelta(days=1 if row[1] == "daily" else 7 if row[1] == "weekly" else 30 if row[1] == "monthly" else 365)
                    cursor = conn.execute(
                        "UPDATE reminders SET status = 'pending', due_at = ?, last_triggered_at = ? WHERE id = ?",
                        (next_due.isoformat(), now.isoformat(), reminder_id),
                    )
                else:
                    cursor = conn.execute(
                        "UPDATE reminders SET status = ? WHERE id = ?",
                        (status, reminder_id),
                    )
                conn.commit()
                updated = cursor.rowcount
            finally:
                conn.close()
        if updated == 0:
            return {"ok": False, "error": "Reminder was not found."}
        return {"ok": True, "error": None}
    except Exception as exc:
        return {"ok": False, "error": f"Reminder could not be updated: {exc}"}


def snooze_reminder(reminder_id: str, minutes: int = 10) -> dict:
    minutes = max(1, min(int(minutes), 10080))
    due_at = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=minutes)).isoformat()
    try:
        with _lock:
            conn = _connect()
            try:
                cursor = conn.execute(
                    "UPDATE reminders SET status = 'pending', due_at = ? WHERE id = ?",
                    (due_at, reminder_id),
                )
                conn.commit()
                updated = cursor.rowcount
            finally:
                conn.close()
        if updated == 0:
            return {"ok": False, "error": "Reminder was not found."}
        return {"ok": True, "due_at": due_at, "error": None}
    except Exception as exc:
        return {"ok": False, "error": f"Reminder could not be snoozed: {exc}"}


def update_reminder(reminder_id: str, *, title: str | None = None, note: str | None = None, due_at: str | None = None, recurrence: str | None = None) -> dict:
    fields: list[str] = []
    values: list[object] = []
    if title is not None:
        cleaned = title.strip()[:MAX_TITLE_LENGTH]
        if not cleaned:
            return {"ok": False, "error": "Reminder title is empty."}
        fields.append("title = ?"); values.append(cleaned)
    if note is not None:
        fields.append("note = ?"); values.append(note.strip()[:MAX_NOTE_LENGTH])
    if due_at is not None:
        cleaned_due_at = due_at.strip()
        if cleaned_due_at:
            try: datetime.datetime.fromisoformat(cleaned_due_at)
            except ValueError: return {"ok": False, "error": "due_at must be an ISO datetime string."}
        fields.append("due_at = ?"); values.append(cleaned_due_at or None)
    if recurrence is not None:
        clean_recurrence = recurrence.strip().lower()
        if clean_recurrence not in {"", "daily", "weekly", "monthly", "yearly"}:
            return {"ok": False, "error": "Invalid recurrence value."}
        fields.append("recurrence = ?"); values.append(clean_recurrence)
    if not fields: return {"ok": False, "error": "No reminder changes supplied."}
    try:
        with _lock:
            conn = _connect()
            try:
                values.append(reminder_id)
                cursor = conn.execute(f"UPDATE reminders SET {', '.join(fields)} WHERE id = ?", values)
                conn.commit()
            finally: conn.close()
        return {"ok": cursor.rowcount > 0, "error": None if cursor.rowcount > 0 else "Reminder was not found."}
    except Exception as exc:
        return {"ok": False, "error": f"Reminder could not be updated: {exc}"}


def parse_natural_reminder(text: str, now: datetime.datetime | None = None) -> dict:
    """Parse common English/Banglish reminder phrases without an LLM."""
    raw = " ".join((text or "").strip().split())
    if not raw:
        return {"ok": False, "error": "Reminder text is empty."}
    current = now or datetime.datetime.now(ZoneInfo("Asia/Dhaka"))
    lowered = raw.lower()
    recurrence = ""
    for token, value in (("every day", "daily"), ("daily", "daily"), ("protidin", "daily"), ("প্রতিদিন", "daily"), ("every week", "weekly"), ("weekly", "weekly"), ("every month", "monthly"), ("monthly", "monthly")):
        if token in lowered:
            recurrence = value
            lowered = lowered.replace(token, " ")
            break

    due: datetime.datetime | None = None
    duration = re.search(r"\bin\s+(\d+)\s*(minute|minutes|min|hour|hours|day|days)\b", lowered)
    if not duration:
        duration = re.search(r"(\d+)\s*(minit|minute|ghonta|hour|din|day)\s*(?:por|pore)", lowered)
    if duration:
        amount = int(duration.group(1))
        unit = duration.group(2)
        if unit in {"minute", "minutes", "min", "minit"}:
            due = current + datetime.timedelta(minutes=amount)
        elif unit in {"hour", "hours", "ghonta"}:
            due = current + datetime.timedelta(hours=amount)
        else:
            due = current + datetime.timedelta(days=amount)
        lowered = lowered.replace(duration.group(0), " ")
    else:
        clock = re.search(r"(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", lowered)
        if clock and ("tomorrow" in lowered or "kal" in lowered or "আগামীকাল" in lowered):
            hour = int(clock.group(1))
            minute = int(clock.group(2) or 0)
            meridiem = clock.group(3)
            if meridiem == "pm" and hour < 12:
                hour += 12
            if meridiem == "am" and hour == 12:
                hour = 0
            due = (current + datetime.timedelta(days=1)).replace(hour=hour, minute=minute, second=0, microsecond=0)
            lowered = lowered.replace(clock.group(0), " ").replace("tomorrow", " ").replace("kal", " ").replace("আগামীকাল", " ")

    title = re.sub(r"^(remind me|set a reminder|reminder|amake mone koriye dio|মনে করিয়ে দাও)\s*", "", lowered).strip(" ,.-")
    title = re.sub(r"\b(to|je|যে)\b\s*", "", title, count=1).strip()
    if not title:
        title = "Reminder"
    return {
        "ok": True,
        "title": title[:MAX_TITLE_LENGTH],
        "due_at": due.astimezone(datetime.timezone.utc).isoformat() if due else None,
        "recurrence": recurrence,
        "error": None,
    }


def delete_reminder(reminder_id: str) -> dict:
    """Delete one reminder record (a local database row, not a user file)."""
    try:
        with _lock:
            conn = _connect()
            try:
                cursor = conn.execute(
                    "DELETE FROM reminders WHERE id = ?", (reminder_id,)
                )
                conn.commit()
                deleted = cursor.rowcount
            finally:
                conn.close()
        if deleted == 0:
            return {"ok": False, "error": "Reminder was not found."}
        return {"ok": True, "error": None}
    except Exception as exc:
        return {"ok": False, "error": f"Reminder could not be deleted: {exc}"}
