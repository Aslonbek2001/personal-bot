"""/start, /reload, asosiy menyu (content/ dagi fanlardan) va eskirgan tugmalar."""

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import settings
from bot.content import loader
from bot.handlers import knowledge, language
from bot.handlers.menu import main_menu_kb, main_menu_text, show_home
from bot.ui import texts
from bot.ui.callbacks import MenuCb, SubjectCb

log = logging.getLogger(__name__)

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.greeting(settings.lesson_hour, settings.reminder_hour))
    sent = await message.answer(main_menu_text(), reply_markup=main_menu_kb())
    await state.update_data(nav_id=sent.message_id)


@router.message(Command("reload"))
async def cmd_reload(message: Message) -> None:
    try:
        library = loader.reload()
    except Exception as error:
        log.exception("Kontent yuklanmadi")
        await message.answer(texts.reload_failed(error))
        return
    await message.answer(texts.reloaded(len(library.subjects), len(library.grammar_topics()), len(library.nodes)))


@router.callback_query(MenuCb.filter(F.action == "home"))
async def open_home(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await show_home(callback, state)


@router.callback_query(MenuCb.filter(F.action == "noop"))
async def noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(SubjectCb.filter())
async def open_subject(callback: CallbackQuery, callback_data: SubjectCb, state: FSMContext) -> None:
    library = loader.current()
    root = library.nodes.get(callback_data.id)
    if root is None or root.kind != "subject":
        await callback.answer(texts.LIST_CHANGED)
        await show_home(callback, state)
        return
    subject = library.subject_by_root(root)
    if subject.type == "language":
        await language.open_language(callback, state)
    else:
        await knowledge.open_node(callback, state, root, 0)


fallback = Router(name="fallback")


@fallback.callback_query()
async def stale_button(callback: CallbackQuery) -> None:
    """Eski formatdagi yoki endi yo'q tugmalar."""
    await callback.answer(texts.STALE)
