"""Ovozli xabar: ffmpeg + Whisper -> matn -> suhbat bilan bir xil oqim."""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.config import settings
from bot.handlers.chat import knowledge_subject, practice_language, respond
from bot.handlers.common import Tech, exclusive, is_tech, thinking
from bot.handlers.knowledge import scope_node
from bot.services import progress
from bot.ui import texts
from bot.ui.format import short
from bot.voice import stt

log = logging.getLogger(__name__)

router = Router(name="voice")

MAX_VOICE_SECONDS = 300


async def voice_context(state: FSMContext) -> tuple[str, str]:
    """Whisper uchun (izoh, til): mavzu nomi atamalarni to'g'riroq tanitadi, til — suhbat tili."""
    current, data = await state.get_state(), await state.get_data()
    if is_tech(current):
        subject = knowledge_subject(data)
        language = (subject.code if subject else "") or settings.stt_language
        scope = scope_node(data) if current == Tech.chat.state else None
        if scope is None:
            return "", language
        _, topic, subsection = scope.scope_names()
        return f"{topic}. {subsection}.", language
    subject = practice_language(data)
    if subject is None:
        return "", settings.stt_language
    topic = progress.todays_topic(subject)
    return (f"{short(topic)}." if topic else ""), subject.code


@router.message(F.voice | F.audio | F.video_note)
async def on_voice(message: Message, state: FSMContext) -> None:
    media = message.voice or message.audio or message.video_note
    if media.duration and media.duration > MAX_VOICE_SECONDS:
        await message.reply(texts.voice_too_long(MAX_VOICE_SECONDS))
        return
    async with exclusive(message.chat.id) as free:
        if not free:
            await message.reply(texts.BUSY)
            return
        try:
            async with thinking(message.bot, message.chat.id):
                audio = await message.bot.download(media)
                prompt, language = await voice_context(state)
                text = await stt.transcribe(audio.read(), prompt=prompt, language=language)
        except Exception:
            log.exception("Ovoz matnga o'girilmadi")
            await message.reply(texts.VOICE_FAILED)
            return
        if not text:
            await message.reply(texts.VOICE_EMPTY)
            return
        await respond(message.bot, message.chat.id, state, text, reply_to=message.message_id, seconds=media.duration or 0)
