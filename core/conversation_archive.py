from contextlib import contextmanager
"""Local searchable conversation archive; only user/assistant turns are stored."""
import sqlite3
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / 'memory/conversations.sqlite3'


@contextmanager
def database():
    PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(PATH, timeout=10)
    conn.execute('CREATE TABLE IF NOT EXISTS turns (id INTEGER PRIMARY KEY, role TEXT, text TEXT, at TEXT DEFAULT CURRENT_TIMESTAMP)')
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def record(text, assistant_name='Nexa AI'):
    prefix, sep, body = str(text).partition(':')
    role = 'user' if prefix.lower() in ('you', 'user') else 'assistant' if prefix.lower() in ('jarvis', 'nexa', 'nexa ai', assistant_name.lower()) else None
    if not role or not sep or not body.strip():
        return
    with database() as conn:
        conn.execute('INSERT INTO turns(role,text) VALUES (?,?)', (role, body.strip()))


def recall(query='', limit=12):
    limit = max(1, min(int(limit), 30))
    with database() as conn:
        rows = conn.execute('SELECT role,text,at FROM turns WHERE instr(lower(text),lower(?))>0 ORDER BY id DESC LIMIT ?', (query, limit)).fetchall()
    return [{'role': r, 'text': t[:4000], 'at': at} for r, t, at in reversed(rows)]


def clear():
    with database() as conn:
        conn.execute('DELETE FROM turns')
