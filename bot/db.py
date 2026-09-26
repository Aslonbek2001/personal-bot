"""SQLite: holat, progress, darslar, so'zlar, xatolar va javoblar."""

import json
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StateType, StorageKey

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


# ─────────────── FSM ───────────────

class SQLiteStorage(BaseStorage):
    @staticmethod
    def _key(key: StorageKey) -> str:
        return f"{key.bot_id}:{key.chat_id}:{key.user_id}"

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        value = state.state if isinstance(state, State) else state
        conn().execute(
            "INSERT INTO fsm (key, state) VALUES (?, ?) "
            "ON CONFLICT (key) DO UPDATE SET state = excluded.state",
            (self._key(key), value),
        )

    async def get_state(self, key: StorageKey) -> str | None:
        row = conn().execute("SELECT state FROM fsm WHERE key = ?", (self._key(key),)).fetchone()
        return row["state"] if row else None

    async def set_data(self, key: StorageKey, data: Mapping[str, Any]) -> None:
        conn().execute(
            "INSERT INTO fsm (key, data) VALUES (?, ?) "
            "ON CONFLICT (key) DO UPDATE SET data = excluded.data",
            (self._key(key), json.dumps(dict(data), ensure_ascii=False)),
        )

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        row = conn().execute("SELECT data FROM fsm WHERE key = ?", (self._key(key),)).fetchone()
        return json.loads(row["data"]) if row else {}

    async def close(self) -> None:
        pass


# ─────────────── Tugallangan mavzular ───────────────

@dataclass(frozen=True)
class DoneEntry:
    day: date
    topic: str


def done_topics() -> list[DoneEntry]:
    rows = conn().execute("SELECT day, topic FROM done_topics ORDER BY day").fetchall()
    return [DoneEntry(day=date.fromisoformat(row["day"]), topic=row["topic"]) for row in rows]


def add_done(day: date, topic: str) -> bool:
    cursor = conn().execute(
        "INSERT OR IGNORE INTO done_topics (day, topic) VALUES (?, ?)", (day.isoformat(), topic)
    )
    return cursor.rowcount > 0


# ─────────────── Darslar va so'zlar ───────────────

def get_lesson(day: date, topic: str) -> str | None:
    row = conn().execute(
        "SELECT data FROM lessons WHERE day = ? AND topic = ?", (day.isoformat(), topic)
    ).fetchone()
    return row["data"] if row else None


def save_lesson(day: date, topic: str, data: str, words: list[tuple[str, str, str]]) -> None:
    db = conn()
    db.execute("BEGIN")
    try:
        db.execute(
            "INSERT OR REPLACE INTO lessons (day, topic, data) VALUES (?, ?, ?)",
            (day.isoformat(), topic, data),
        )
        db.execute("DELETE FROM words WHERE day = ?", (day.isoformat(),))
        db.executemany(
            "INSERT OR IGNORE INTO words (day, position, word, uz, example) VALUES (?, ?, ?, ?, ?)",
            [(day.isoformat(), n, word, uz, example) for n, (word, uz, example) in enumerate(words)],
        )
        db.execute("COMMIT")
    except Exception:
        db.execute("ROLLBACK")
        raise


@dataclass(frozen=True)
class DayWord:
    word: str
    uz: str
    example: str
    used: bool


def day_words(day: date) -> list[DayWord]:
    rows = conn().execute(
        "SELECT word, uz, example, used_at FROM words WHERE day = ? ORDER BY position",
        (day.isoformat(),),
    ).fetchall()
    return [DayWord(row["word"], row["uz"], row["example"], row["used_at"] is not None) for row in rows]


def mark_words_used(day: date, words: list[str]) -> None:
    conn().executemany(
        "UPDATE words SET used_at = ? WHERE day = ? AND word = ? AND used_at IS NULL",
        [(now().isoformat(), day.isoformat(), word) for word in words],
    )


# ─────────────── Javoblar ───────────────

def add_answer(mode: str, text: str, words: int, seconds: int | None, mistakes: int) -> None:
    moment = now()
    conn().execute(
        "INSERT INTO answers (created_at, day, mode, text, words, seconds, mistakes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (moment.isoformat(), moment.date().isoformat(), mode, text, words, seconds, mistakes),
    )


@dataclass(frozen=True)
class Stats:
    answers: int
    words: int
    mistakes: int
    voice_words: int
    voice_seconds: int

    @property
    def wpm(self) -> int | None:
        return round(self.voice_words * 60 / self.voice_seconds) if self.voice_seconds else None


def stats(since: date) -> Stats:
    row = conn().execute(
        "SELECT COUNT(*) AS answers, COALESCE(SUM(words), 0) AS words, "
        "COALESCE(SUM(mistakes), 0) AS mistakes, "
        "COALESCE(SUM(CASE WHEN seconds > 0 THEN words END), 0) AS voice_words, "
        "COALESCE(SUM(CASE WHEN seconds > 0 THEN seconds END), 0) AS voice_seconds "
        "FROM answers WHERE day >= ?",
        (since.isoformat(),),
    ).fetchone()
    return Stats(**dict(row))


# ─────────────── Xatolar ───────────────

def add_mistakes(fixes: list[tuple[str, str, str]]) -> None:
    moment = now()
    conn().executemany(
        "INSERT INTO mistakes (created_at, day, wrong, right, note) VALUES (?, ?, ?, ?, ?)",
        [(moment.isoformat(), moment.date().isoformat(), wrong, right, note) for wrong, right, note in fixes],
    )


@dataclass(frozen=True)
class Mistake:
    day: date
    wrong: str
    right: str
    note: str


def recent_mistakes(limit: int, since: date | None = None) -> list[Mistake]:
    rows = conn().execute(
        "SELECT day, wrong, right, note FROM mistakes WHERE day >= ? ORDER BY id DESC LIMIT ?",
        ((since or date.min).isoformat(), limit),
    ).fetchall()
    return [Mistake(date.fromisoformat(row["day"]), row["wrong"], row["right"], row["note"]) for row in rows]


def mistakes_count(since: date) -> int:
    return conn().execute("SELECT COUNT(*) FROM mistakes WHERE day >= ?", (since.isoformat(),)).fetchone()[0]
