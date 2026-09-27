import sqlite3
from datetime import date, timedelta

import pytest

from bot.config import settings
from bot.content import loader
from bot.services import db, journal, lessons, progress

DAY = date(2026, 9, 27)


@pytest.fixture
def today(fresh_db, monkeypatch):
    current = {"day": DAY}
    monkeypatch.setattr(progress, "today", lambda: current["day"])
    return current


@pytest.fixture
def english():
    return loader.current().subject("english")


def test_todays_topic_is_first_not_done(today, english):
    topics = progress.read_topics(english)
    assert len(topics) == 32
    assert progress.todays_topic(english) == topics[0]
    assert progress.done_today(english) == 0


def test_mark_done_once_per_topic(today, english):
    topics = progress.read_topics(english)
    assert progress.mark_done(english, topics[0]) is True
    assert progress.mark_done(english, topics[0]) is False
    today["day"] = DAY + timedelta(days=3)
    assert progress.mark_done(english, topics[0]) is False
    assert progress.progress(english).count == 1


def test_todays_topic_moves_forward_after_done(today, english):
    topics = progress.read_topics(english)
    progress.mark_done(english, topics[0])
    assert progress.todays_topic(english) == topics[1]
    progress.mark_done(english, topics[1])
    assert progress.todays_topic(english) == topics[2]


def test_two_topics_done_on_the_same_day(today, english):
    topics = progress.read_topics(english)
    assert progress.mark_done(english, topics[0]) and progress.mark_done(english, topics[1])
    assert progress.done_today(english) == 2
    assert [e.topic for e in progress.read_process(english)] == topics[:2]
    today["day"] = DAY + timedelta(days=1)
    assert progress.done_today(english) == 0


def test_topic_ids_are_short_and_found(english):
    topic = progress.read_topics(english)[5]
    assert len(progress.topic_id(topic)) == 8
    assert progress.find_topic(english, progress.topic_id(topic)) == topic
    assert progress.find_topic(english, "deadbeef") is None


def test_progress_counts_only_existing_topics(today, english):
    topics = progress.read_topics(english)
    progress.mark_done(english, topics[0])
    db.conn().execute("INSERT INTO done_topics (lang, topic, day) VALUES ('en', 'Removed topic', '2026-01-01')")
    stats = progress.progress(english)
    assert (stats.count, stats.total, stats.percent) == (1, 32, 3)


def test_data_is_separate_per_language(today):
    journal.add_mistakes("en", [("has", "have", "n")])
    journal.add_mistakes("ru", [("книгу", "книга", "n")])
    journal.add_answer("ru", "chat", "Я читаю", 2, None, 1)
    assert [m.wrong for m in journal.recent_mistakes("ru", 10)] == ["книгу"]
    assert journal.mistakes_count("en", DAY) == 1
    assert journal.stats("ru", DAY).answers == 1 and journal.stats("en", DAY).answers == 0
    lessons.save_lesson("ru", DAY, "t", "{}", [("книга", "kitob", "Это книга.")])
    assert lessons.cached_lesson("ru", DAY, "t") == "{}" and lessons.cached_lesson("en", DAY, "t") is None
    assert [w.word for w in lessons.day_words("ru", DAY)] == ["книга"] and lessons.day_words("en", DAY) == []


def test_old_schema_is_refused_and_left_untouched(tmp_path, monkeypatch):
    db.close()
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    old = sqlite3.connect(tmp_path / "bot.db")
    old.execute("CREATE TABLE done_topics (day TEXT PRIMARY KEY, topic TEXT NOT NULL)")
    old.execute("INSERT INTO done_topics VALUES ('2026-09-01', 'x')")
    old.commit()
    old.close()
    before = (tmp_path / "bot.db").read_bytes()
    with pytest.raises(db.OldSchemaError, match="o'chiring"):
        db.init()
    assert (tmp_path / "bot.db").read_bytes() == before
    assert not (tmp_path / "bot.db-wal").exists()
    db.close()


def test_find_used_words():
    words = ["to deploy", "a rollback", "feedback", "set up"]
    used = lessons.find_used_words("We deployed it, got feedbacks and set   up CI.", words)
    assert used == ["to deploy", "feedback", "set up"]
