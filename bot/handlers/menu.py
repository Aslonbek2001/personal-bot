"""Asosiy menyu: content/ dagi fanlar tugmalari va bugungi holat."""

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup

from bot.content import loader
from bot.handlers.common import show_nav
from bot.handlers.language import summary
from bot.ui import keyboards as kb
from bot.ui import texts


def main_menu_text() -> str:
    return texts.main_menu(summary())


def main_menu_kb() -> InlineKeyboardMarkup:
    return kb.main_menu(loader.current().subjects)


async def show_home(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(None)
    await show_nav(callback, state, main_menu_text(), main_menu_kb())
