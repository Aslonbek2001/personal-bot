"""Rejali xabarlar: ertalabki dars, kechki natija, haftalik takrorlash.

Faqat subject.toml da `scheduled = true` bo'lgan tillar uchun. Joblar ishga tushganda ro'yxatga olinadi.
"""

from datetime import timedelta

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import BaseStorage, StorageKey
from apscheduler.schedulers.base import BaseScheduler
from apscheduler.triggers.cron import CronTrigger

from bot.config import settings
from bot.content import loader
from bot.content.models import Subject
from bot.handlers.language import send_lesson
from bot.handlers.practice import start_mode
from bot.services import journal, lessons, progress
from bot.ui import keyboards as kb
from bot.ui import texts


def _current(subject: Subject) -> Subject | None:
    """/reload dan keyin ham yangi kontentdagi o'sha til."""
    return loader.current().language_by_code(subject.code)


async def morning_lesson(bot: Bot, chat_id: int, subject: Subject) -> None:
    if subject := _current(subject):
        await send_lesson(bot, chat_id, subject, morning=True)


async def evening_summary(bot: Bot, chat_id: int, subject: Subject) -> None:
    if not (subject := _current(subject)):
        return
    today = progress.today()
    stats = journal.stats(subject.code, today)
    if not stats.answers:
        await bot.send_message(chat_id, texts.EVENING_EMPTY, reply_markup=kb.reminder_kb(subject.code))
        return
    words = lessons.day_words(subject.code, today)
    await bot.send_message(chat_id, texts.evening_text(stats, words), reply_markup=kb.words_kb(subject.code))


async def weekly_review(bot: Bot, chat_id: int, state: FSMContext, subject: Subject) -> None:
    if not (subject := _current(subject)):
        return
    if not journal.mistakes_count(subject.code, progress.today() - timedelta(days=6)):
        return
    await bot.send_message(chat_id, texts.WEEKLY_REVIEW)
    await start_mode(bot, chat_id, state, subject, "review")


def register(scheduler: BaseScheduler, bot: Bot, storage: BaseStorage) -> None:
    tz, owner = settings.tz, settings.owner_id
    state = FSMContext(storage=storage, key=StorageKey(bot_id=bot.id, chat_id=owner, user_id=owner))
    options = {"misfire_grace_time": 3600, "coalesce": True}
    for subject in loader.current().languages:
        if not subject.scheduled:
            continue
        base = {"bot": bot, "chat_id": owner, "subject": subject}
        scheduler.add_job(morning_lesson, CronTrigger(hour=settings.lesson_hour, minute=0, timezone=tz),
                          kwargs=base, id=f"morning_lesson:{subject.code}", **options)
        scheduler.add_job(evening_summary, CronTrigger(hour=settings.reminder_hour, minute=0, timezone=tz),
                          kwargs=base, id=f"evening_summary:{subject.code}", **options)
        scheduler.add_job(
            weekly_review,
            CronTrigger(day_of_week=settings.review_day, hour=settings.review_hour, minute=0, timezone=tz),
            kwargs={**base, "state": state}, id=f"weekly_review:{subject.code}", **options,
        )
