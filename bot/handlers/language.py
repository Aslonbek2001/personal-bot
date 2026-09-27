"""English: menyu, kunlik dars, mashq rejimlari, xatolar, so'zlar, progress va talaffuz."""

import asyncio
import logging
from datetime import timedelta

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, ReplyParameters
from aiogram.utils.chat_action import ChatActionSender

from bot.ai import client as ai
from bot.content import loader
from bot.handlers.common import exclusive, send_text, show_nav, thinking
from bot.services import journal, lessons, progress
from bot.ui import keyboards as kb
from bot.ui import texts
from bot.ui.callbacks import MenuCb, ModeCb
from bot.ui.card import render_card
from bot.ui.format import short
from bot.voice import tts

log = logging.getLogger(__name__)

router = Router(name="language")

REVIEW_DAYS = 14


# ─────────────── Menyu ───────────────

def summary() -> list[str]:
    stats = progress.progress()
    return texts.today_lines(
        progress.todays_topic(), progress.is_done_today(), stats.count, stats.total,
        lessons.day_words(progress.today()),
    )


async def open_language(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(None)
    language = loader.current().language
    label = language.label if language else "English"
    await show_nav(callback, state, texts.language_menu(label, summary()), kb.language_menu())


@router.callback_query(MenuCb.filter(F.action == "lang"))
async def language_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await open_language(callback, state)


# ─────────────── Kunlik dars ───────────────

async def send_lesson(bot: Bot, chat_id: int, morning: bool = False) -> None:
    topic = progress.todays_topic()
    if topic is None:
        await bot.send_message(chat_id, texts.ALL_TOPICS_DONE)
        return
    try:
        async with thinking(bot, chat_id):
            lesson = await lessons.get_lesson(topic)
    except Exception:
        log.exception("Dars yaratilmadi")
        await bot.send_message(chat_id, texts.LESSON_FAILED, reply_markup=kb.language_menu())
        return

    topics = progress.read_topics()
    number = topics.index(topic) + 1 if topic in topics else 0
    png = await asyncio.to_thread(render_card, lesson, number, len(topics), progress.today())
    await bot.send_photo(
        chat_id, BufferedInputFile(png, filename="lesson.png"), caption=texts.lesson_caption(lesson.title, morning)
    )
    *parts, last = texts.lesson_parts(lesson)
    for part in parts:
        await send_text(bot, chat_id, part)
    await send_text(bot, chat_id, last, kb.lesson_end())


@router.callback_query(MenuCb.filter(F.action == "today"))
async def today_lesson(callback: CallbackQuery, state: FSMContext) -> None:
    async with exclusive(callback.from_user.id) as free:
        if not free:
            await callback.answer(texts.BUSY)
            return
        await callback.answer()
        await state.set_state(None)
        await send_lesson(callback.bot, callback.from_user.id)


# ─────────────── Mashq rejimlari ───────────────

def topic_title() -> str:
    topic = progress.todays_topic()
    return short(topic) if topic else "free practice"


def review_mistakes() -> list[str]:
    since = progress.today() - timedelta(days=REVIEW_DAYS)
    return [f"{m.wrong} -> {m.right}" for m in journal.recent_mistakes(30, since)]


async def start_mode(bot: Bot, chat_id: int, state: FSMContext, mode: str) -> None:
    await state.set_state(None)
    mistakes = review_mistakes() if mode == "review" else []
    if mode == "review" and not mistakes:
        await bot.send_message(chat_id, texts.NO_REVIEW_MISTAKES, reply_markup=kb.language_menu())
        return
    try:
        async with thinking(bot, chat_id):
            opening = await ai.opening(mode, topic_title(), lessons.today_words(), mistakes)
    except Exception:
        log.exception("Rejim boshlanmadi: %s", mode)
        await bot.send_message(chat_id, texts.ERROR)
        return
    await send_text(bot, chat_id, texts.opening_text(mode, opening.message, opening.question), kb.reply_nav())
    await state.update_data(
        mode=mode,
        history_day=progress.today().isoformat(),
        history=[
            {"role": "user", "content": "Let's start. Give me the first question or task."},
            {"role": "assistant", "content": f"{opening.message}\n{opening.question}"},
        ],
    )


@router.callback_query(ModeCb.filter())
async def mode_chosen(callback: CallbackQuery, callback_data: ModeCb, state: FSMContext) -> None:
    if callback_data.mode not in texts.MODE_ICONS:
        await callback.answer()
        return
    async with exclusive(callback.from_user.id) as free:
        if not free:
            await callback.answer(texts.BUSY)
            return
        await callback.answer()
        await start_mode(callback.bot, callback.from_user.id, state, callback_data.mode)


# ─────────────── Xatolar, so'zlar, progress ───────────────

@router.callback_query(MenuCb.filter(F.action == "mistakes"))
async def show_mistakes(callback: CallbackQuery) -> None:
    await callback.answer()
    mistakes = journal.recent_mistakes(15)
    week = journal.mistakes_count(progress.today() - timedelta(days=6))
    await send_text(callback.bot, callback.from_user.id, texts.mistakes_text(mistakes, week),
                    kb.mistakes_kb(bool(mistakes)))


@router.callback_query(MenuCb.filter(F.action == "words"))
async def show_words(callback: CallbackQuery) -> None:
    await callback.answer()
    words = lessons.day_words(progress.today())
    await callback.bot.send_message(callback.from_user.id, texts.words_text(words), reply_markup=kb.words_kb())


@router.callback_query(MenuCb.filter(F.action == "done"))
async def mark_done(callback: CallbackQuery) -> None:
    topic = progress.todays_topic()
    if topic is None:
        await callback.answer(texts.DONE_NOTHING)
        return
    if not progress.mark_done(topic):
        await callback.answer(texts.DONE_ALREADY)
        return
    await callback.answer(texts.DONE_OK)
    await callback.bot.send_message(
        callback.from_user.id, texts.done_text(topic, progress.next_topic()), reply_markup=kb.after_done()
    )


@router.callback_query(MenuCb.filter(F.action == "progress"))
async def show_progress(callback: CallbackQuery) -> None:
    await callback.answer()
    text = texts.progress_text(
        progress.progress(),
        journal.stats(progress.today() - timedelta(days=6)),
        progress.todays_topic(),
        progress.is_done_today(),
        lessons.day_words(progress.today()),
    )
    await callback.bot.send_message(callback.from_user.id, text, reply_markup=kb.progress_kb())


# ─────────────── Talaffuz ───────────────

@router.callback_query(MenuCb.filter(F.action == "speak"))
async def speak_reply(callback: CallbackQuery, state: FSMContext) -> None:
    message_id = callback.message.message_id if callback.message else 0
    text = (await state.get_data()).get("speak", {}).get(str(message_id))
    if not text:
        await callback.answer(texts.STALE)
        return
    chat_id = callback.from_user.id
    async with exclusive(chat_id) as free:
        if not free:
            await callback.answer(texts.BUSY)
            return
        await callback.answer()
        try:
            async with ChatActionSender.record_voice(bot=callback.bot, chat_id=chat_id):
                audio = await tts.speak(text)
        except Exception:
            log.exception("Ovoz yaratilmadi")
            await callback.bot.send_message(chat_id, texts.SPEAK_FAILED)
            return
    await callback.bot.send_voice(
        chat_id,
        BufferedInputFile(audio, filename="speech.ogg"),
        caption=texts.speak_caption(text),
        reply_parameters=ReplyParameters(message_id=message_id, allow_sending_without_reply=True),
    )
