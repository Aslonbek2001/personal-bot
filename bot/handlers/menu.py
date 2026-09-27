"""Asosiy menyu: content/ dagi fanlar tugmalari va bugungi holat."""

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup

from bot.content import loader
from bot.handlers.common import show_nav
from bot.services import progress
from bot.ui import keyboards as kb
from bot.ui import texts


def main_menu_text() -> str:
    lines = []
    for subject in loader.current().languages:
        stats = progress.progress(subject)
        lines.append(texts.main_menu_line(subject.icon, progress.todays_topic(subject), stats.count, stats.total))
    return texts.main_menu(lines)


def main_menu_kb() -> InlineKeyboardMarkup:
    return kb.main_menu(loader.current().subjects)


async def show_home(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(None)
    await show_nav(callback, state, main_menu_text(), main_menu_kb())
