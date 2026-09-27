"""Barcha inline klaviaturalar."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.content.models import Node, Subject
from bot.ui import texts as t
from bot.ui.callbacks import KnowCb, MenuCb, ModeCb, SubjectCb

PAGE_SIZE = 8


def _home(builder: InlineKeyboardBuilder, action: str = "lang") -> None:
    """English ichida 🏠 Menyu English menyusini ochadi, bilim daraxtida — asosiy menyuni."""
    builder.button(text=t.BTN_HOME, callback_data=MenuCb(action=action))


# ─────────────── Asosiy menyu ───────────────

def main_menu(subjects: list[Subject]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for subject in subjects:
        b.button(text=subject.label, callback_data=SubjectCb(id=subject.root.id))
    b.adjust(2)
    return b.as_markup()


# ─────────────── English ───────────────

def language_menu() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t.BTN_GRAMMAR, callback_data=MenuCb(action="grammar"))
    b.button(text=t.BTN_SPEAKING, callback_data=ModeCb(mode="standup"))
    b.button(text=t.BTN_WRITING, callback_data=MenuCb(action="writing"))
    b.button(text=t.BTN_MISTAKES, callback_data=MenuCb(action="mistakes"))
    b.button(text=t.BTN_WORDS, callback_data=MenuCb(action="words"))
    b.button(text=t.BTN_PROGRESS, callback_data=MenuCb(action="progress"))
    b.button(text=t.BTN_BACK, callback_data=MenuCb(action="home"))
    b.adjust(1, 2, 2, 2)
    return b.as_markup()


def grammar_menu() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t.BTN_TODAY, callback_data=MenuCb(action="today"))
    b.button(text=t.BTN_CHAT, callback_data=ModeCb(mode="chat"))
    b.button(text=t.BTN_DONE, callback_data=MenuCb(action="done"))
    b.button(text=t.BTN_BACK, callback_data=MenuCb(action="lang"))
    b.adjust(2, 1, 1)
    return b.as_markup()


def writing_menu() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t.BTN_TRANSLATE, callback_data=ModeCb(mode="translate"))
    b.button(text=t.BTN_TASK, callback_data=ModeCb(mode="task"))
    b.button(text=t.BTN_BACK, callback_data=MenuCb(action="lang"))
    b.adjust(2, 1)
    return b.as_markup()


def lesson_end() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t.BTN_START_CHAT, callback_data=ModeCb(mode="chat"))
    b.button(text=t.BTN_DONE, callback_data=MenuCb(action="done"))
    _home(b)
    b.adjust(2, 1)
    return b.as_markup()


def progress_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t.BTN_TODAY, callback_data=MenuCb(action="today"))
    _home(b)
    b.adjust(2)
    return b.as_markup()


def mistakes_kb(has_mistakes: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if has_mistakes:
        b.button(text=t.BTN_REVIEW, callback_data=ModeCb(mode="review"))
    _home(b)
    b.adjust(1)
    return b.as_markup()


def words_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t.BTN_CHAT, callback_data=ModeCb(mode="chat"))
    _home(b)
    b.adjust(2)
    return b.as_markup()


def reminder_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t.BTN_CHAT, callback_data=ModeCb(mode="chat"))
    b.button(text=t.BTN_STANDUP, callback_data=ModeCb(mode="standup"))
    _home(b)
    b.adjust(2, 1)
    return b.as_markup()


def after_done() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t.BTN_PROGRESS, callback_data=MenuCb(action="progress"))
    _home(b)
    b.adjust(2)
    return b.as_markup()


def home_only(action: str = "lang") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    _home(b, action)
    return b.as_markup()


# ─────────────── Suhbat javobi ostida ───────────────

def reply_nav(
    topic: Node | None = None,
    next_node: Node | None = None,
    speak: bool = False,
    home: str = "lang",
) -> InlineKeyboardMarkup:
    """Suhbat javobi ostidagi navigatsiya; bilim qismida keyingi qism va orqaga."""
    b = InlineKeyboardBuilder()
    rows = []
    if speak:
        b.button(text=t.BTN_SPEAK, callback_data=MenuCb(action="speak"))
        rows.append(1)
    if topic is None:
        _home(b, home)
        b.adjust(*rows, 1)
        return b.as_markup()
    if next_node is not None:
        b.button(text=t.btn_next_subsection(next_node.title), callback_data=KnowCb(id=next_node.id))
        rows.append(1)
    b.button(text=t.BTN_SUBSECTIONS, callback_data=KnowCb(id=topic.id))
    _home(b, "home")
    rows.append(2)
    b.adjust(*rows)
    return b.as_markup()


# ─────────────── Bilim daraxti ───────────────

def _label(node: Node) -> str:
    if node.kind == "group":
        return f"{node.title} ({node.count('topic')})"
    return node.title


def page_count(node: Node) -> int:
    return max(1, -(-len(node.children) // PAGE_SIZE))


def knowledge(node: Node, page: int) -> InlineKeyboardMarkup:
    """Tugun bolalari: sahifada ko'pi bilan 8 ta, ◀️ ▶️, Orqaga va Menyu."""
    b = InlineKeyboardBuilder()
    pages = page_count(node)
    page = min(max(page, 0), pages - 1)
    items = node.children[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    for child in items:
        b.button(text=_label(child), callback_data=KnowCb(id=child.id))
    rows = [1] * len(items)
    if pages > 1:
        nav = 1
        if page > 0:
            b.button(text=t.BTN_PREV, callback_data=KnowCb(id=node.id, page=page - 1))
            nav += 1
        b.button(text=f"{page + 1}/{pages}", callback_data=MenuCb(action="noop"))
        if page < pages - 1:
            b.button(text=t.BTN_NEXT, callback_data=KnowCb(id=node.id, page=page + 1))
            nav += 1
        rows.append(nav)
    if node.parent is not None:
        b.button(text=t.BTN_BACK, callback_data=KnowCb(id=node.parent.id, page=_page_of(node)))
    else:
        b.button(text=t.BTN_BACK, callback_data=MenuCb(action="home"))
    _home(b, "home")
    rows.append(2)
    b.adjust(*rows)
    return b.as_markup()


def _page_of(node: Node) -> int:
    """Orqaga bosilganda ota ro'yxatining shu tugun turgan sahifasi ochiladi."""
    assert node.parent is not None
    return node.parent.children.index(node) // PAGE_SIZE
