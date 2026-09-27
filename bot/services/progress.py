"""Grammatika progressi, har bir til alohida: tugallangan mavzular va bugungi mavzu."""

from dataclasses import dataclass
from datetime import date

from bot.content.loader import node_id
from bot.content.models import Subject
from bot.services import db


def today() -> date:
    """Toshkent vaqti bo'yicha bugungi sana."""
    return db.now().date()


def read_topics(subject: Subject) -> list[str]:
    """Tilning barcha grammatika mavzulari, tartib bilan."""
    return [topic for block in subject.grammar for topic in block.topics]


def topic_id(topic: str) -> str:
    """Tugmalar uchun mavzuning qisqa, barqaror ID si."""
    return node_id(topic)


def find_topic(subject: Subject, ident: str) -> str | None:
    return next((topic for topic in read_topics(subject) if topic_id(topic) == ident), None)


@dataclass(frozen=True)
class DoneEntry:
    day: date
    topic: str


def read_process(subject: Subject) -> list[DoneEntry]:
    rows = db.conn().execute(
        "SELECT day, topic FROM done_topics WHERE lang = ? ORDER BY day, rowid", (subject.code,)
    ).fetchall()
    return [DoneEntry(day=date.fromisoformat(row["day"]), topic=row["topic"]) for row in rows]


def todays_topic(subject: Subject) -> str | None:
    """Bugungi mavzu — hali bajarilmagan birinchi mavzu. Bir kunda bir nechta mavzu o'tish mumkin."""
    done = {entry.topic for entry in read_process(subject)}
    return next((topic for topic in read_topics(subject) if topic not in done), None)


def done_today(subject: Subject) -> int:
    """Bugun tugallangan mavzular soni."""
    return sum(entry.day == today() for entry in read_process(subject))


def is_done(subject: Subject, topic: str) -> bool:
    return any(entry.topic == topic for entry in read_process(subject))


def mark_done(subject: Subject, topic: str) -> bool:
    """Mavzuni tugallangan deb belgilaydi. Allaqachon belgilangan bo'lsa, False (har mavzu bir marta)."""
    cursor = db.conn().execute(
        "INSERT OR IGNORE INTO done_topics (lang, topic, day) VALUES (?, ?, ?)",
        (subject.code, topic, today().isoformat()),
    )
    return cursor.rowcount > 0


@dataclass(frozen=True)
class Progress:
    done: tuple[DoneEntry, ...]
    total: int

    @property
    def count(self) -> int:
        return len(self.done)

    @property
    def percent(self) -> int:
        return round(self.count * 100 / self.total) if self.total else 0


def progress(subject: Subject) -> Progress:
    """Faqat content/ da hozir bor mavzular hisoblanadi."""
    topics = read_topics(subject)
    existing = set(topics)
    done = tuple(entry for entry in read_process(subject) if entry.topic in existing)
    return Progress(done=done, total=len(topics))
