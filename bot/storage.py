"""data/ papkasidagi fayllar (context, topics, tech) va progress."""

import re
from dataclasses import dataclass, field
from datetime import date, datetime

from bot import db
from bot.config import settings

NUMBER_PREFIX = re.compile(r"^\d+[.)]\s*")


def today() -> date:
    """Toshkent vaqti bo'yicha bugungi sana."""
    return datetime.now(settings.tz).date()


def read_context() -> str:
    return settings.context_path.read_text(encoding="utf-8")


# ─────────────── Grammatika: topics.md ───────────────

def read_topics() -> list[str]:
    """topics.md dagi mavzular: izohlar, bo'sh qatorlar va raqamlarsiz."""
    topics = []
    for line in settings.topics_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        topics.append(NUMBER_PREFIX.sub("", line))
    return topics


# ─────────────── Progress ───────────────

DoneEntry = db.DoneEntry


def read_process() -> list[DoneEntry]:
    return db.done_topics()


def todays_topic() -> str | None:
    """Bugungi mavzu. Bugun bajarilgan bo'lsa ham kun oxirigacha o'sha mavzu qoladi."""
    entries = read_process()
    for entry in entries:
        if entry.day == today():
            return entry.topic
    done = {entry.topic for entry in entries}
    return next((topic for topic in read_topics() if topic not in done), None)


def is_done_today() -> bool:
    return any(entry.day == today() for entry in read_process())


def mark_done(topic: str) -> bool:
    """Bugungi mavzuni tugallangan deb belgilaydi. Bugun allaqachon belgilangan bo'lsa, False."""
    return db.add_done(today(), topic)


# ─────────────── Kunlik so'zlar ───────────────

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
    """Faqat topics.md da hozir bor mavzular hisoblanadi."""
    topics = read_topics()
    existing = set(topics)
    done = tuple(entry for entry in read_process() if entry.topic in existing)
    return Progress(done=done, total=len(topics))


# ─────────────── Tech: tech.md ───────────────

@dataclass
class TechTopic:
    name: str
    subsections: list[str] = field(default_factory=list)


@dataclass
class TechSection:
    name: str
    topics: list[TechTopic] = field(default_factory=list)


def read_tech() -> list[TechSection]:
    """'# ' bo'lim, '## ' mavzu, '- ' qism."""
    sections: list[TechSection] = []
    lines = settings.tech_path.read_text(encoding="utf-8").splitlines()
    for number, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("## "):
            if not sections:
                raise ValueError(f"tech.md:{number}: mavzu hech bir bo'limga tegishli emas")
            sections[-1].topics.append(TechTopic(name=line[3:].strip()))
        elif line.startswith("# "):
            sections.append(TechSection(name=line[2:].strip()))
        elif line.startswith("- "):
            if not sections or not sections[-1].topics:
                raise ValueError(f"tech.md:{number}: qism hech bir mavzuga tegishli emas")
            sections[-1].topics[-1].subsections.append(line[2:].strip())
    return sections


def tech_item(section: int, topic: int, subsection: int) -> tuple[str, str, str]:
    """Indekslardan bo'lim, mavzu va qism nomlarini qaytaradi. Topilmasa: LookupError."""
    sec = read_tech()[section]
    top = sec.topics[topic]
    return sec.name, top.name, top.subsections[subsection]