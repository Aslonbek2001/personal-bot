"""Javoblar va xatolar jurnali, statistika."""

from dataclasses import dataclass
from datetime import date

from bot.services import db


def add_answer(mode: str, text: str, words: int, seconds: int | None, mistakes: int) -> None:
    moment = db.now()
    db.conn().execute(
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
    row = db.conn().execute(
        "SELECT COUNT(*) AS answers, COALESCE(SUM(words), 0) AS words, "
        "COALESCE(SUM(mistakes), 0) AS mistakes, "
        "COALESCE(SUM(CASE WHEN seconds > 0 THEN words END), 0) AS voice_words, "
        "COALESCE(SUM(CASE WHEN seconds > 0 THEN seconds END), 0) AS voice_seconds "
        "FROM answers WHERE day >= ?",
        (since.isoformat(),),
    ).fetchone()
    return Stats(**dict(row))


def add_mistakes(fixes: list[tuple[str, str, str]]) -> None:
    moment = db.now()
    db.conn().executemany(
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
    rows = db.conn().execute(
        "SELECT day, wrong, right, note FROM mistakes WHERE day >= ? ORDER BY id DESC LIMIT ?",
        ((since or date.min).isoformat(), limit),
    ).fetchall()
    return [Mistake(date.fromisoformat(row["day"]), row["wrong"], row["right"], row["note"]) for row in rows]


def mistakes_count(since: date) -> int:
    return db.conn().execute(
        "SELECT COUNT(*) FROM mistakes WHERE day >= ?", (since.isoformat(),)
    ).fetchone()[0]
