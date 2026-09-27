"""Rejali xabarlar: ertalabki dars, kechki natija va haftalik takrorlash."""

from datetime import timedelta

from aiogram import Bot
from aiogram.fsm.context import FSMContext

from bot.handlers.language import send_lesson, start_mode
from bot.services import journal, lessons, progress
from bot.ui import keyboards as kb
from bot.ui import texts


async def morning_lesson(bot: Bot, chat_id: int) -> None:
    await send_lesson(bot, chat_id, morning=True)


async def evening_summary(bot: Bot, chat_id: int) -> None:
    today = progress.today()
    stats = journal.stats(today)
    if not stats.answers:
        await bot.send_message(chat_id, texts.EVENING_EMPTY, reply_markup=kb.reminder_kb())
        return
    words = lessons.day_words(today)
    await bot.send_message(chat_id, texts.evening_text(stats, words), reply_markup=kb.words_kb())


async def weekly_review(bot: Bot, chat_id: int, state: FSMContext) -> None:
    if not journal.mistakes_count(progress.today() - timedelta(days=6)):
        return
    await bot.send_message(chat_id, texts.WEEKLY_REVIEW)
    await start_mode(bot, chat_id, state, "review")
