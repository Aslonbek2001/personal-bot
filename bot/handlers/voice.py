"""Ovozli xabar: ffmpeg + Whisper -> matn -> suhbat bilan bir xil oqim."""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.handlers.chat import respond
from bot.handlers.common import Tech, exclusive, thinking
from bot.handlers.knowledge import scope_node
from bot.services import progress
from bot.ui import texts
from bot.ui.format import short
from bot.voice import stt

log = logging.getLogger(__name__)

router = Router(name="voice")

MAX_VOICE_SECONDS = 300


async def voice_prompt(state: FSMContext) -> str:
    """Whisper'ga mavzu nomini beradi: atamalar to'g'riroq taniladi."""
    if await state.get_state() == Tech.chat.state:
        scope = scope_node(await state.get_data())
        if scope is not None:
            _, topic, subsection = scope.scope_names()
            return f"{topic}. {subsection}."
    topic = progress.todays_topic()
    return f"{short(topic)}." if topic else ""


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
                text = await stt.transcribe(audio.read(), prompt=await voice_prompt(state))
        except Exception:
            log.exception("Ovoz matnga o'girilmadi")
            await message.reply(texts.VOICE_FAILED)
            return
        if not text:
            await message.reply(texts.VOICE_EMPTY)
            return
        await respond(message.bot, message.chat.id, state, text, reply_to=message.message_id, seconds=media.duration or 0)
