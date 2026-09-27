"""SQLite ulanishi, sxema va FSM holati (data/bot.db)."""

import json
import sqlite3
from datetime import date, datetime
from typing import Any

from bot.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS fsm (
    key TEXT PRIMARY KEY,
    state TEXT,
    data TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS done_topics (
    day TEXT PRIMARY KEY,
    topic TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lessons (
    day TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS words (
    day TEXT NOT NULL,
    position INTEGER NOT NULL,
    word TEXT NOT NULL,
    uz TEXT NOT NULL,
    example TEXT NOT NULL,
    used_at TEXT,
    PRIMARY KEY (day, word)
);
CREATE TABLE IF NOT EXISTS answers (
    id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL,
    day TEXT NOT NULL,
    mode TEXT NOT NULL,
    text TEXT NOT NULL,
    words INTEGER NOT NULL,
    seconds INTEGER,
    mistakes INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS mistakes (
    id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL,
    day TEXT NOT NULL,
    wrong TEXT NOT NULL,
    right TEXT NOT NULL,
    note TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS answers_day ON answers (day);
CREATE INDEX IF NOT EXISTS mistakes_day ON mistakes (day);
"""

_conn: sqlite3.Connection | None = None


def conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(settings.db_path, check_same_thread=False, isolation_level=None)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.executescript(SCHEMA)
    return _conn


def close() -> None:
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None


def now() -> datetime:
    return datetime.now(settings.tz)


def init() -> None:
    conn()
    _import_process_md()


def _import_process_md() -> None:
    path = settings.process_path
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        day, separator, topic = line.removeprefix("- ").partition(" | ")
        if not line.startswith("- ") or not separator:
            continue
        try:
            date.fromisoformat(day.strip())
        except ValueError:
            continue
        conn().execute(
            "INSERT OR IGNORE INTO done_topics (day, topic) VALUES (?, ?)",
            (day.strip(), topic.strip()),
        )
    path.rename(path.with_suffix(".md.imported"))


# ─────────────── FSM (aiogram adapteri: bot/handlers/fsm.py) ───────────────

def fsm_set_state(key: str, value: str | None) -> None:
    conn().execute(
        "INSERT INTO fsm (key, state) VALUES (?, ?) "
        "ON CONFLICT (key) DO UPDATE SET state = excluded.state",
        (key, value),
    )


def fsm_get_state(key: str) -> str | None:
    row = conn().execute("SELECT state FROM fsm WHERE key = ?", (key,)).fetchone()
    return row["state"] if row else None


def fsm_set_data(key: str, data: dict[str, Any]) -> None:
    conn().execute(
        "INSERT INTO fsm (key, data) VALUES (?, ?) "
        "ON CONFLICT (key) DO UPDATE SET data = excluded.data",
        (key, json.dumps(data, ensure_ascii=False)),
    )


def fsm_get_data(key: str) -> dict[str, Any]:
    row = conn().execute("SELECT data FROM fsm WHERE key = ?", (key,)).fetchone()
    return json.loads(row["data"]) if row else {}
