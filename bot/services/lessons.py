"""Dars keshi va kunning so'zlari — har bir til (lang) alohida."""

import asyncio
import re
from dataclasses import dataclass
from datetime import date

from bot.ai import client as ai
from bot.ai.schemas import Lesson
from bot.content.models import Subject
from bot.services import db
from bot.services.progress import today

# ─────────────── Dars keshi ───────────────

_lesson_lock = asyncio.Lock()


def cached_lesson(lang: str, day: date, topic: str) -> str | None:
    row = db.conn().execute(
        "SELECT data FROM lessons WHERE lang = ? AND day = ? AND topic = ?", (lang, day.isoformat(), topic)
    ).fetchone()
    return row["data"] if row else None


def save_lesson(lang: str, day: date, topic: str, data: str, words: list[tuple[str, str, str]]) -> None:
    """Darsni saqlaydi; kunning so'zlari — shu tildagi oxirgi darsning so'zlari."""
    conn = db.conn()
    conn.execute("BEGIN")
    try:
        conn.execute(
            "INSERT OR REPLACE INTO lessons (lang, day, topic, data) VALUES (?, ?, ?, ?)",
            (lang, day.isoformat(), topic, data),
        )
        conn.execute("DELETE FROM words WHERE lang = ? AND day = ?", (lang, day.isoformat()))
        conn.executemany(
            "INSERT OR IGNORE INTO words (lang, day, position, word, uz, example) VALUES (?, ?, ?, ?, ?, ?)",
            [(lang, day.isoformat(), n, word, uz, example) for n, (word, uz, example) in enumerate(words)],
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


async def get_lesson(subject: Subject, topic: str) -> Lesson:
    """Mavzu darsini bugun bir marta yaratadi va DB da saqlaydi (kalit: til, kun, mavzu)."""
    day = today()
    async with _lesson_lock:
        saved = cached_lesson(subject.code, day, topic)
        if saved:
            return Lesson.model_validate_json(saved)
        lesson = await ai.make_lesson(subject, topic)
        words = [(w.word, w.uz, w.example) for w in lesson.words]
        save_lesson(subject.code, day, topic, lesson.model_dump_json(), words)
        return lesson


# ─────────────── Kunlik so'zlar ───────────────

@dataclass(frozen=True)
class DayWord:
    word: str
    uz: str
    example: str
    used: bool


def day_words(lang: str, day: date) -> list[DayWord]:
    rows = db.conn().execute(
        "SELECT word, uz, example, used_at FROM words WHERE lang = ? AND day = ? ORDER BY position",
        (lang, day.isoformat()),
    ).fetchall()
    return [DayWord(row["word"], row["uz"], row["example"], row["used_at"] is not None) for row in rows]


def today_words(lang: str) -> list[str]:
    return [w.word for w in day_words(lang, today())]


def mark_words_used(lang: str, day: date, words: list[str]) -> None:
    db.conn().executemany(
        "UPDATE words SET used_at = ? WHERE lang = ? AND day = ? AND word = ? AND used_at IS NULL",
        [(db.now().isoformat(), lang, day.isoformat(), word) for word in words],
    )


ARTICLES = {"to", "a", "an", "the"}
VOWELS = set("eаеёиоуыэюя")
LETTERS = r"[^\W\d_]"


def _word_pattern(word: str) -> re.Pattern | None:
    """'to deploy' -> deploy, deploys, deployed; 'книга' -> книгу, книги, книгой (lotin va kirill)."""
    word = word.lower().replace("\u0301", "")  # urg'u belgisi
    parts = re.findall(rf"(?:{LETTERS}|')+", word)
    if len(parts) > 1 and parts[0] in ARTICLES:
        parts = parts[1:]
    if not parts:
        return None
    *head, last = parts
    stem = last[:-1] if len(last) > 4 and last[-1] in VOWELS else last
    body = r"\s+".join([*map(re.escape, head), re.escape(stem) + rf"(?:{LETTERS}|'){{0,3}}"])
    return re.compile(rf"(?<!\w){body}(?!\w)")


def find_used_words(text: str, words: list[str]) -> list[str]:
    lowered = text.lower()
    return [word for word in words if (pattern := _word_pattern(word)) and pattern.search(lowered)]
