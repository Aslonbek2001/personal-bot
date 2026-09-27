"""Grammatika progressi: tugallangan mavzular va bugungi mavzu."""

from dataclasses import dataclass
from datetime import date

from bot.content import loader
from bot.services import db


def today() -> date:
    """Toshkent vaqti bo'yicha bugungi sana."""
    return db.now().date()


def read_topics() -> list[str]:
    """Kunlik dars tilidagi barcha grammatika mavzulari, tartib bilan."""
    return loader.current().grammar_topics()


@dataclass(frozen=True)
class DoneEntry:
    day: date
    topic: str


def read_process() -> list[DoneEntry]:
    rows = db.conn().execute("SELECT day, topic FROM done_topics ORDER BY day").fetchall()
    return [DoneEntry(day=date.fromisoformat(row["day"]), topic=row["topic"]) for row in rows]


def todays_topic() -> str | None:
    """Bugungi mavzu. Bugun bajarilgan bo'lsa ham kun oxirigacha o'sha mavzu qoladi."""
    entries = read_process()
    for entry in entries:
        if entry.day == today():
            return entry.topic
    done = {entry.topic for entry in entries}
    return next((topic for topic in read_topics() if topic not in done), None)


def next_topic() -> str | None:
    """Hali bajarilmagan birinchi mavzu (Bajardim dan keyin — ertangi mavzu)."""
    done = {entry.topic for entry in read_process()}
    return next((topic for topic in read_topics() if topic not in done), None)


def is_done_today() -> bool:
    return any(entry.day == today() for entry in read_process())


def mark_done(topic: str) -> bool:
    """Bugungi mavzuni tugallangan deb belgilaydi. Bugun allaqachon belgilangan bo'lsa, False."""
    cursor = db.conn().execute(
        "INSERT OR IGNORE INTO done_topics (day, topic) VALUES (?, ?)", (today().isoformat(), topic)
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


def progress() -> Progress:
    """Faqat content/ da hozir bor mavzular hisoblanadi."""
    topics = read_topics()
    existing = set(topics)
    done = tuple(entry for entry in read_process() if entry.topic in existing)
    return Progress(done=done, total=len(topics))
