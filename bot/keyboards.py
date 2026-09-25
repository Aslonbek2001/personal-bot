"""Barcha inline klaviaturalar va callback_data klasslari."""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.storage import TechSection


class MenuCb(CallbackData, prefix="m"):
    action: str  # home, today, chat, done, progress


class TechCb(CallbackData, prefix="tech"):
    level: str  # root, section, topic, sub
    s: int = 0
    t: int = 0
    u: int = 0


class OptionCb(CallbackData, prefix="opt"):
    n: int


def _home(builder: InlineKeyboardBuilder) -> None:
    builder.button(text="🏠 Menyu", callback_data=MenuCb(action="home"))


def main_menu() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📚 Bugungi dars", callback_data=MenuCb(action="today"))
    b.button(text="💬 Suhbat", callback_data=MenuCb(action="chat"))
    b.button(text="🧠 Tech", callback_data=TechCb(level="root"))
    b.button(text="📊 Progress", callback_data=MenuCb(action="progress"))
    b.button(text="✅ Bajardim", callback_data=MenuCb(action="done"))
    b.adjust(2, 2, 1)
    return b.as_markup()


def lesson_end() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="💬 Suhbatni boshlash", callback_data=MenuCb(action="chat"))
    b.button(text="✅ Bajardim", callback_data=MenuCb(action="done"))
    _home(b)
    b.adjust(2, 1)
    return b.as_markup()


def progress_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📚 Bugungi dars", callback_data=MenuCb(action="today"))
    _home(b)
    b.adjust(2)
    return b.as_markup()


def after_done() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📊 Progress", callback_data=MenuCb(action="progress"))
    _home(b)
    b.adjust(2)
    return b.as_markup()


def answer(
    options: list[str],
    tech: tuple[int, int, int] | None = None,
    next_name: str | None = None,
) -> InlineKeyboardMarkup:
    """Javob variantlari; tech qismida qo'shimcha navigatsiya."""
    b = InlineKeyboardBuilder()
    for n, option in enumerate(options[:3]):
        b.button(text=option, callback_data=OptionCb(n=n))
    rows = [1] * len(options[:3])
    if tech:
        s, t, u = tech
        if next_name:
            b.button(text=f"➡️ Keyingi qism: {next_name}", callback_data=TechCb(level="sub", s=s, t=t, u=u + 1))
            rows.append(1)
        b.button(text="⬅️ Qismlar", callback_data=TechCb(level="topic", s=s, t=t))
        _home(b)
        rows.append(2)
    else:
        _home(b)
        rows.append(1)
    b.adjust(*rows)
    return b.as_markup()


def tech_sections(sections: list[TechSection]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for s, section in enumerate(sections):
        b.button(text=f"{s + 1}. {section.name} ({len(section.topics)})", callback_data=TechCb(level="section", s=s))
    _home(b)
    b.adjust(1)
    return b.as_markup()


def tech_topics(sections: list[TechSection], s: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for t, topic in enumerate(sections[s].topics):
        b.button(text=topic.name, callback_data=TechCb(level="topic", s=s, t=t))
    b.button(text="⬅️ Bo'limlar", callback_data=TechCb(level="root"))
    _home(b)
    b.adjust(*([1] * len(sections[s].topics)), 2)
    return b.as_markup()


def tech_subsections(sections: list[TechSection], s: int, t: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    subsections = sections[s].topics[t].subsections
    for u, name in enumerate(subsections):
        b.button(text=name, callback_data=TechCb(level="sub", s=s, t=t, u=u))
    b.button(text="⬅️ Mavzular", callback_data=TechCb(level="section", s=s))
    _home(b)
    b.adjust(*([1] * len(subsections)), 2)
    return b.as_markup()