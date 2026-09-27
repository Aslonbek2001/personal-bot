"""Test muhiti: haqiqiy .env va data/ ga tegmaydi, tarmoqqa chiqmaydi."""

import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OWNER_ID = 111

# bot.config import qilinishidan oldin: muhit o'zgaruvchilari .env dan ustun turadi.
os.environ.update({
    "BOT_TOKEN": "123456:TEST",
    "OWNER_ID": str(OWNER_ID),
    "ANTHROPIC_API_KEY": "test",
    "GROQ_API_KEY": "test",
    "TIMEZONE": "Asia/Tashkent",
    "LESSON_HOUR": "5",
    "HISTORY_LIMIT": "6",
    "DATA_DIR": tempfile.mkdtemp(prefix="ustoz-test-"),
    "CONTENT_DIR": str(ROOT / "content"),
})


import pytest  # noqa: E402


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    """Har bir test uchun alohida bo'sh bot.db."""
    from bot.config import settings
    from bot.services import db

    db.close()
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    db.init()
    yield tmp_path
    db.close()
