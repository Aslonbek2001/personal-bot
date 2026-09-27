"""Mashq rejimlari (suhbat, tarjima, yozish, gapirish, xatolar ustida ishlash) va talaffuz."""

import logging
from datetime import timedelta

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, ReplyParameters
from aiogram.utils.chat_action import ChatActionSender

from bot.ai import client as ai
from bot.content.models import Subject
from bot.handlers.common import exclusive, send_text, thinking
from bot.handlers.language import resolve
from bot.services import journal, lessons, progress
from bot.ui import keyboards as kb
from bot.ui import texts
from bot.ui.callbacks import MenuCb, ModeCb
from bot.ui.format import short
from bot.voice import tts

log = logging.getLogger(__name__)

router = Router(name="practice")

REVIEW_DAYS = 14


def topic_title(subject: Subject) -> str:
    topic = progress.todays_topic(subject)
    return short(topic) if topic else "free practice"


def review_mistakes(subject: Subject) -> list[str]:
    since = progress.today() - timedelta(days=REVIEW_DAYS)
    return [f"{m.wrong} -> {m.right}" for m in journal.recent_mistakes(subject.code, 30, since)]


async def start_mode(bot: Bot, chat_id: int, state: FSMContext, subject: Subject, mode: str) -> None:
    await state.set_state(None)
    mistakes = review_mistakes(subject) if mode == "review" else []
    if mode == "review" and not mistakes:
        await bot.send_message(chat_id, texts.NO_REVIEW_MISTAKES, reply_markup=kb.language_menu(subject))
        return
    try:
        async with thinking(bot, chat_id):
            words = lessons.today_words(subject.code)
            opening = await ai.opening(subject, mode, topic_title(subject), words, mistakes)
    except Exception:
        log.exception("Rejim boshlanmadi: %s", mode)
        await bot.send_message(chat_id, texts.ERROR)
        return
    await send_text(bot, chat_id, texts.opening_text(mode, opening.message, opening.question),
                    kb.reply_nav(lang=subject.code))
    await state.update_data(
        lang=subject.code,
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
        await callback.answer(texts.STALE)
        return
    if not (subject := await resolve(callback, callback_data.lang)):
        return
    async with exclusive(callback.from_user.id) as free:
        if not free:
            await callback.answer(texts.BUSY)
            return
        await callback.answer()
        await start_mode(callback.bot, callback.from_user.id, state, subject, callback_data.mode)


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
