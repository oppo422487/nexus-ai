"""Shared durable local store for selected documents, jobs, follow-ups and receipts."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import json
import sqlite3
import uuid

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'memory/life.sqlite3'
DATA = ROOT / 'memory/life_data'


def now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connection():
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA busy_timeout=15000')
    con.executescript('''
      CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY,kind TEXT,title TEXT,
        status TEXT,payload TEXT,created TEXT,updated TEXT);
      CREATE TABLE IF NOT EXISTS evidence(id TEXT PRIMARY KEY,document_id TEXT,
        location TEXT,text TEXT);
      CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY,path TEXT,name TEXT,
        sha256 TEXT,created TEXT,metadata TEXT);
      CREATE VIRTUAL TABLE IF NOT EXISTS evidence_fts USING fts5(id UNINDEXED,text);
      CREATE TABLE IF NOT EXISTS activity(id TEXT PRIMARY KEY,kind TEXT,title TEXT,
        locator TEXT,detail TEXT,created TEXT);
    ''')
    try:
        with con:
            yield con
    finally:
        con.close()


def add(kind, title, payload=None, status='open'):
    key = uuid.uuid4().hex
    with connection() as con:
        con.execute('INSERT INTO records VALUES(?,?,?,?,?,?,?)',
                    (key, kind, title[:300], status, json.dumps(payload or {}, ensure_ascii=False), now(), now()))
    return get(key)


def get(key):
    with connection() as con:
        row = con.execute('SELECT * FROM records WHERE id=?', (key,)).fetchone()
    if not row:
        raise ValueError('Record not found; use list to get its exact ID.')
    item = dict(row)
    item['payload'] = json.loads(item['payload'])
    return item


def update(key, status=None, payload=None):
    old = get(key)
    with connection() as con:
        con.execute('UPDATE records SET status=?,payload=?,updated=? WHERE id=?',
                    (status or old['status'], json.dumps(payload if payload is not None else old['payload'], ensure_ascii=False), now(), key))
    return get(key)


def records(kind='', status='', limit=100):
    with connection() as con:
        rows = con.execute('SELECT id FROM records WHERE (?="" OR kind=?) AND (?="" OR status=?) ORDER BY updated DESC LIMIT ?',
                           (kind, kind, status, status, min(max(int(limit), 1), 200))).fetchall()
    return [get(row['id']) for row in rows]


def activity(kind, title, locator='', detail=''):
    with connection() as con:
        con.execute('INSERT INTO activity VALUES(?,?,?,?,?,?)',
                    (uuid.uuid4().hex, kind, title[:300], locator, detail[:4000], now()))


def find_activity(query='', limit=20):
    with connection() as con:
        rows = con.execute('SELECT * FROM activity WHERE instr(lower(title||" "||detail),lower(?))>0 ORDER BY created DESC LIMIT ?',
                           (query, min(max(int(limit), 1), 50))).fetchall()
    return [dict(row) for row in rows]
