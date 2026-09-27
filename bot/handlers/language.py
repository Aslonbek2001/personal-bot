"""Til (English, Russian): menyu va ichki menyular, dars, Bajardim, xatolar, so'zlar, progress.

Til callback_data dagi `lang` (subject.toml dagi code) bilan tanlanadi: bitta kod barcha tillar uchun.
"""

import asyncio
import logging
from datetime import timedelta

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery

from bot.content import loader
from bot.content.models import Subject
from bot.handlers.common import exclusive, send_text, show_nav, thinking
from bot.services import journal, lessons, progress
from bot.ui import keyboards as kb
from bot.ui import texts
from bot.ui.callbacks import DoneCb, LangCb
from bot.ui.card import render_card

log = logging.getLogger(__name__)

router = Router(name="language")


async def resolve(callback: CallbackQuery, code: str) -> Subject | None:
    """Callback dagi til kodi bo'yicha fan; endi yo'q bo'lsa, tugma eskirgan."""
    subject = loader.current().language_by_code(code)
    if subject is None:
        await callback.answer(texts.STALE)
    return subject


async def select_language(state: FSMContext, subject: Subject) -> None:
    """Matnli xabarlar shu tilga boradi; til almashsa, suhbat tarixi yangidan boshlanadi."""
    data = await state.get_data()
    if data.get("lang") != subject.code:
        await state.update_data(lang=subject.code, mode="chat", history=[])


# ─────────────── Menyular ───────────────

def summary(subject: Subject) -> list[str]:
    stats = progress.progress(subject)
    return texts.today_lines(
        progress.todays_topic(subject), progress.done_today(subject), stats.count, stats.total,
        lessons.day_words(subject.code, progress.today()),
    )


async def open_language(callback: CallbackQuery, state: FSMContext, subject: Subject) -> None:
    await callback.answer()
    await state.set_state(None)
    await select_language(state, subject)
    await show_nav(callback, state, texts.language_menu(subject.label, summary(subject)), kb.language_menu(subject))


@router.callback_query(LangCb.filter(F.action == "menu"))
async def language_menu(callback: CallbackQuery, callback_data: LangCb, state: FSMContext) -> None:
    if subject := await resolve(callback, callback_data.lang):
        await open_language(callback, state, subject)


@router.callback_query(LangCb.filter(F.action == "grammar"))
async def grammar_menu(callback: CallbackQuery, callback_data: LangCb, state: FSMContext) -> None:
    if not (subject := await resolve(callback, callback_data.lang)):
        return
    await callback.answer()
    topic = progress.todays_topic(subject)
    text = texts.grammar_menu(topic, progress.done_today(subject))
    await show_nav(callback, state, text, kb.grammar_menu(subject, topic))


@router.callback_query(LangCb.filter(F.action == "writing"))
async def writing_menu(callback: CallbackQuery, callback_data: LangCb, state: FSMContext) -> None:
    if not (subject := await resolve(callback, callback_data.lang)):
        return
    await callback.answer()
    await show_nav(callback, state, texts.WRITING_MENU, kb.writing_menu(subject))


# ─────────────── Dars ───────────────

async def send_lesson(bot: Bot, chat_id: int, subject: Subject, morning: bool = False) -> None:
    """Hali bajarilmagan birinchi mavzu darsi: karta, grammatika, hikoya, 20 so'z."""
    topic = progress.todays_topic(subject)
    if topic is None:
        await bot.send_message(chat_id, texts.ALL_TOPICS_DONE)
        return
    try:
        async with thinking(bot, chat_id):
            lesson = await lessons.get_lesson(subject, topic)
    except Exception:
        log.exception("Dars yaratilmadi")
        await bot.send_message(chat_id, texts.LESSON_FAILED, reply_markup=kb.language_menu(subject))
        return

    topics = progress.read_topics(subject)
    number = topics.index(topic) + 1
    png = await asyncio.to_thread(render_card, lesson, number, len(topics), progress.today())
    await bot.send_photo(
        chat_id, BufferedInputFile(png, filename="lesson.png"), caption=texts.lesson_caption(lesson.title, morning)
    )
    *parts, last = texts.lesson_parts(lesson)
    for part in parts:
        await send_text(bot, chat_id, part)
    await send_text(bot, chat_id, last, kb.lesson_end(subject, topic))


@router.callback_query(LangCb.filter(F.action == "today"))
async def today_lesson(callback: CallbackQuery, callback_data: LangCb, state: FSMContext) -> None:
    """📚 Bugungi dars va 📖 Keyingi mavzu: ikkalasi ham hali bajarilmagan birinchi mavzu."""
    if not (subject := await resolve(callback, callback_data.lang)):
        return
    async with exclusive(callback.from_user.id) as free:
        if not free:
            await callback.answer(texts.BUSY)
            return
        await callback.answer()
        await state.set_state(None)
        await select_language(state, subject)
        await send_lesson(callback.bot, callback.from_user.id, subject)


@router.callback_query(DoneCb.filter())
async def mark_done(callback: CallbackQuery, callback_data: DoneCb) -> None:
    if not (subject := await resolve(callback, callback_data.lang)):
        return
    topic = progress.find_topic(subject, callback_data.topic)
    if topic is None:
        await callback.answer(texts.STALE)
        return
    if not progress.mark_done(subject, topic):
        await callback.answer(texts.DONE_ALREADY)
        return
    await callback.answer(texts.DONE_OK)
    await callback.bot.send_message(
        callback.from_user.id,
        texts.done_text(topic, progress.todays_topic(subject)),
        reply_markup=kb.after_done(subject.code),
    )


# ─────────────── Xatolar, so'zlar, progress (faqat shu til) ───────────────

@router.callback_query(LangCb.filter(F.action == "mistakes"))
async def show_mistakes(callback: CallbackQuery, callback_data: LangCb) -> None:
    if not (subject := await resolve(callback, callback_data.lang)):
        return
    await callback.answer()
    mistakes = journal.recent_mistakes(subject.code, 15)
    week = journal.mistakes_count(subject.code, progress.today() - timedelta(days=6))
    await send_text(callback.bot, callback.from_user.id, texts.mistakes_text(mistakes, week),
                    kb.mistakes_kb(subject.code, bool(mistakes)))


@router.callback_query(LangCb.filter(F.action == "words"))
async def show_words(callback: CallbackQuery, callback_data: LangCb) -> None:
    if not (subject := await resolve(callback, callback_data.lang)):
        return
    await callback.answer()
    words = lessons.day_words(subject.code, progress.today())
    await callback.bot.send_message(callback.from_user.id, texts.words_text(words),
                                    reply_markup=kb.words_kb(subject.code))


@router.callback_query(LangCb.filter(F.action == "progress"))
async def show_progress(callback: CallbackQuery, callback_data: LangCb) -> None:
    if not (subject := await resolve(callback, callback_data.lang)):
        return
    await callback.answer()
    text = texts.progress_text(
        progress.progress(subject),
        journal.stats(subject.code, progress.today() - timedelta(days=6)),
        progress.todays_topic(subject),
        progress.done_today(subject),
        lessons.day_words(subject.code, progress.today()),
    )
    await callback.bot.send_message(callback.from_user.id, text, reply_markup=kb.progress_kb(subject.code))
