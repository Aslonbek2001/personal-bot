"""Handler'lar uchun umumiy: holatlar, band holat, "Thinking…", yuborish va menyu tahriri."""

import asyncio
import logging
import random
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message, ReplyParameters

from bot.ui.format import split_text

log = logging.getLogger(__name__)

DRAFT_REFRESH = 20


class Tech(StatesGroup):
    browse = State()
    chat = State()


def is_tech(state: str | None) -> bool:
    """Bilim daraxtidagi har qanday holat (eski Tech:sections/topics/... ham)."""
    return bool(state) and state.startswith("Tech:")


# ─────────────── Kutish: band holat va "Thinking…" ───────────────

_busy: set[int] = set()


@asynccontextmanager
async def exclusive(chat_id: int) -> AsyncIterator[bool]:
    """Bir vaqtda bitta so'rov: band bo'lsa False beradi."""
    if chat_id in _busy:
        yield False
        return
    _busy.add(chat_id)
    try:
        yield True
    finally:
        _busy.discard(chat_id)


@asynccontextmanager
async def thinking(bot: Bot, chat_id: int) -> AsyncIterator[None]:
    """Chatda 'Thinking…' qoralamasini ko'rsatadi; qoralama 30 s yashagani uchun yangilab turadi."""
    draft_id = random.randint(1, 2**31 - 1)

    async def refresh() -> None:
        while True:
            try:
                await bot.send_message_draft(chat_id=chat_id, draft_id=draft_id, text="")
            except TelegramAPIError as error:
                log.warning("Qoralama yuborilmadi: %s", error)
                return
            await asyncio.sleep(DRAFT_REFRESH)

    task = asyncio.create_task(refresh())
    try:
        yield
    finally:
        task.cancel()


# ─────────────── Yuborish ───────────────

async def send_text(
    bot: Bot,
    chat_id: int,
    text: str,
    markup: InlineKeyboardMarkup | None = None,
    reply_to: int | None = None,
) -> Message:
    """Matnni yuboradi; klaviatura oxirgi qismga, reply birinchi qismga qo'yiladi."""
    parts = split_text(text)
    message: Message | None = None
    for index, part in enumerate(parts):
        message = await bot.send_message(
            chat_id,
            part,
            reply_markup=markup if index == len(parts) - 1 else None,
            reply_parameters=(
                ReplyParameters(message_id=reply_to, allow_sending_without_reply=True)
                if reply_to and index == 0
                else None
            ),
        )
    assert message is not None
    return message


async def show_nav(callback: CallbackQuery, state: FSMContext, text: str, markup: InlineKeyboardMarkup) -> None:
    """Menyu xabarini joyida tahrirlaydi; boshqa xabardan bosilgan bo'lsa, yangisini yuboradi."""
    data = await state.get_data()
    message = callback.message
    if isinstance(message, Message) and message.message_id == data.get("nav_id"):
        try:
            await message.edit_text(text, reply_markup=markup)
        except TelegramBadRequest as error:
            if "not modified" not in str(error):
                raise
        return
    sent = await callback.bot.send_message(callback.from_user.id, text, reply_markup=markup)
    await state.update_data(nav_id=sent.message_id)
