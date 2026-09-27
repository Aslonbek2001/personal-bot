"""SQLite ulanishi, sxema va FSM holati (data/bot.db)."""

import json
import sqlite3
from datetime import datetime
from typing import Any

from bot.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS fsm (
    key TEXT PRIMARY KEY,
    state TEXT,
    data TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS done_topics (
    lang TEXT NOT NULL,
    topic TEXT NOT NULL,
    day TEXT NOT NULL,
    PRIMARY KEY (lang, topic)
);
CREATE TABLE IF NOT EXISTS lessons (
    lang TEXT NOT NULL,
    day TEXT NOT NULL,
    topic TEXT NOT NULL,
    data TEXT NOT NULL,
    PRIMARY KEY (lang, day, topic)
);
CREATE TABLE IF NOT EXISTS words (
    lang TEXT NOT NULL,
    day TEXT NOT NULL,
    position INTEGER NOT NULL,
    word TEXT NOT NULL,
    uz TEXT NOT NULL,
    example TEXT NOT NULL,
    used_at TEXT,
    PRIMARY KEY (lang, day, word)
);
CREATE TABLE IF NOT EXISTS answers (
    id INTEGER PRIMARY KEY,
    lang TEXT NOT NULL,
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
    lang TEXT NOT NULL,
    created_at TEXT NOT NULL,
    day TEXT NOT NULL,
    wrong TEXT NOT NULL,
    right TEXT NOT NULL,
    note TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS answers_day ON answers (lang, day);
CREATE INDEX IF NOT EXISTS mistakes_day ON mistakes (lang, day);
"""
LANG_TABLES = ("done_topics", "lessons", "words", "answers", "mistakes")


class OldSchemaError(RuntimeError):
    pass


_conn: sqlite3.Connection | None = None


def conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(settings.db_path, check_same_thread=False, isolation_level=None)
        connection.row_factory = sqlite3.Row
        try:
            _check_schema(connection)
        except OldSchemaError:
            connection.close()
            raise
        connection.execute("PRAGMA journal_mode=WAL")
        connection.executescript(SCHEMA)
        _conn = connection
    return _conn


def _check_schema(connection: sqlite3.Connection) -> None:
    """Eski sxemadagi bazani (lang ustunisiz) hech qachon o'zgartirmaydi: to'xtaydi va xabar beradi."""
    for table in LANG_TABLES:
        columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
        if columns and "lang" not in columns:
            raise OldSchemaError(
                f"{settings.db_path} eski sxemada ({table} jadvalida lang ustuni yo'q). "
                f"Bot uni o'zgartirmaydi. Botni to'xtating va {settings.db_path} hamda "
                f"{settings.db_path}-wal, {settings.db_path}-shm fayllarini o'chiring: yangi bo'sh baza yaratiladi."
            )


def close() -> None:
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None


def now() -> datetime:
    return datetime.now(settings.tz)


def init() -> None:
    conn()


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
