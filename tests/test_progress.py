from datetime import date, timedelta

import pytest

from bot.config import settings
from bot.services import db, lessons, progress

DAY = date(2026, 9, 27)


@pytest.fixture
def today(fresh_db, monkeypatch):
    current = {"day": DAY}
    monkeypatch.setattr(progress, "today", lambda: current["day"])
    return current


def test_process_md_is_imported_once(tmp_path, monkeypatch):
    db.close()
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    (tmp_path / "process.md").write_text(
        "# Done\n- 2026-09-20 | Past Simple - reporting what you did yesterday\n"
        "- bad line\n- 2026-13-01 | broken date\n- 2026-09-21 |  Articles a, an, the  \n",
        encoding="utf-8",
    )
    db.init()
    entries = progress.read_process()
    assert [(e.day, e.topic) for e in entries] == [
        (date(2026, 9, 20), "Past Simple - reporting what you did yesterday"),
        (date(2026, 9, 21), "Articles a, an, the"),
    ]
    assert not (tmp_path / "process.md").exists()
    assert (tmp_path / "process.md.imported").exists()
    db.close()


def test_todays_topic_is_first_not_done(today):
    topics = progress.read_topics()
    assert progress.todays_topic() == topics[0]
    assert not progress.is_done_today()


def test_mark_done_once_per_day_and_topic_stays_until_day_ends(today):
    topics = progress.read_topics()
    assert progress.mark_done(topics[0]) is True
    assert progress.mark_done(topics[0]) is False
    assert progress.mark_done(topics[1]) is False
    assert progress.is_done_today()
    assert progress.todays_topic() == topics[0]
    assert progress.next_topic() == topics[1]
    today["day"] = DAY + timedelta(days=1)
    assert progress.todays_topic() == topics[1]
    assert progress.mark_done(topics[1]) is True


def test_progress_counts_only_existing_topics(today):
    topics = progress.read_topics()
    progress.mark_done(topics[0])
    db.conn().execute("INSERT INTO done_topics (day, topic) VALUES ('2026-01-01', 'Removed topic')")
    stats = progress.progress()
    assert (stats.count, stats.total) == (1, 32)
    assert stats.percent == 3


def test_find_used_words():
    words = ["to deploy", "a rollback", "feedback", "set up"]
    used = lessons.find_used_words("We deployed it, got feedbacks and set   up CI.", words)
    assert used == ["to deploy", "feedback", "set up"]
