"""Kunlik dars keshi va kunning so'zlari."""

import asyncio
import re
from dataclasses import dataclass
from datetime import date

from bot.ai import client as ai
from bot.ai.schemas import Lesson
from bot.services import db
from bot.services.progress import today

# ─────────────── Dars keshi ───────────────

_lesson_lock = asyncio.Lock()


def cached_lesson(day: date, topic: str) -> str | None:
    row = db.conn().execute(
        "SELECT data FROM lessons WHERE day = ? AND topic = ?", (day.isoformat(), topic)
    ).fetchone()
    return row["data"] if row else None


def save_lesson(day: date, topic: str, data: str, words: list[tuple[str, str, str]]) -> None:
    conn = db.conn()
    conn.execute("BEGIN")
    try:
        conn.execute(
            "INSERT OR REPLACE INTO lessons (day, topic, data) VALUES (?, ?, ?)",
            (day.isoformat(), topic, data),
        )
        conn.execute("DELETE FROM words WHERE day = ?", (day.isoformat(),))
        conn.executemany(
            "INSERT OR IGNORE INTO words (day, position, word, uz, example) VALUES (?, ?, ?, ?, ?)",
            [(day.isoformat(), n, word, uz, example) for n, (word, uz, example) in enumerate(words)],
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


async def get_lesson(topic: str) -> Lesson:
    """Bugungi darsni bir marta yaratadi va DB da saqlaydi."""
    day = today()
    async with _lesson_lock:
        saved = cached_lesson(day, topic)
        if saved:
            return Lesson.model_validate_json(saved)
        lesson = await ai.make_lesson(topic)
        words = [(w.word, w.uz, w.example) for w in lesson.words]
        save_lesson(day, topic, lesson.model_dump_json(), words)
        return lesson


# ─────────────── Kunlik so'zlar ───────────────

@dataclass(frozen=True)
class DayWord:
    word: str
    uz: str
    example: str
    used: bool


def day_words(day: date) -> list[DayWord]:
    rows = db.conn().execute(
        "SELECT word, uz, example, used_at FROM words WHERE day = ? ORDER BY position",
        (day.isoformat(),),
    ).fetchall()
    return [DayWord(row["word"], row["uz"], row["example"], row["used_at"] is not None) for row in rows]


def today_words() -> list[str]:
    return [w.word for w in day_words(today())]


def mark_words_used(day: date, words: list[str]) -> None:
    db.conn().executemany(
        "UPDATE words SET used_at = ? WHERE day = ? AND word = ? AND used_at IS NULL",
        [(db.now().isoformat(), day.isoformat(), word) for word in words],
    )


ARTICLES = {"to", "a", "an", "the"}


def _word_pattern(word: str) -> re.Pattern | None:
    """'to deploy' -> deploy, deploys, deployed, deploying."""
    parts = re.findall(r"[a-z']+", word.lower())
    if len(parts) > 1 and parts[0] in ARTICLES:
        parts = parts[1:]
    if not parts:
        return None
    *head, last = parts
    stem = last[:-1] if len(last) > 4 and last.endswith("e") else last
    body = r"\s+".join([*map(re.escape, head), re.escape(stem) + r"[a-z']{0,3}"])
    return re.compile(rf"\b{body}\b")


def find_used_words(text: str, words: list[str]) -> list[str]:
    lowered = text.lower()
    return [word for word in words if (pattern := _word_pattern(word)) and pattern.search(lowered)]
