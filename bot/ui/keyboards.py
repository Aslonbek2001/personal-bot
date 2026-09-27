"""Barcha inline klaviaturalar."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.content.models import Node, Subject
from bot.ui import texts as t
from bot.services.progress import topic_id
from bot.ui.callbacks import DoneCb, KnowCb, LangCb, MenuCb, ModeCb, SubjectCb

PAGE_SIZE = 8


def _home(builder: InlineKeyboardBuilder, lang: str | None = None) -> None:
    """Til ichida 🏠 Menyu o'sha til menyusini ochadi, boshqa joyda — asosiy menyuni."""
    data = LangCb(action="menu", lang=lang) if lang else MenuCb(action="home")
    builder.button(text=t.BTN_HOME, callback_data=data)


def _back(builder: InlineKeyboardBuilder, lang: str) -> None:
    builder.button(text=t.BTN_BACK, callback_data=LangCb(action="menu", lang=lang))


# ─────────────── Asosiy menyu ───────────────

def main_menu(subjects: list[Subject]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for subject in subjects:
        b.button(text=subject.label, callback_data=SubjectCb(id=subject.root.id))
    b.adjust(3)
    return b.as_markup()


# ─────────────── Til (English, Russian) ───────────────

def language_menu(subject: Subject) -> InlineKeyboardMarkup:
    lang = subject.code
    b = InlineKeyboardBuilder()
    b.button(text=t.BTN_GRAMMAR, callback_data=LangCb(action="grammar", lang=lang))
    b.button(text=t.BTN_SPEAKING, callback_data=ModeCb(mode="standup", lang=lang))
    b.button(text=t.BTN_WRITING, callback_data=LangCb(action="writing", lang=lang))
    b.button(text=t.BTN_MISTAKES, callback_data=LangCb(action="mistakes", lang=lang))
    b.button(text=t.BTN_WORDS, callback_data=LangCb(action="words", lang=lang))
    b.button(text=t.BTN_PROGRESS, callback_data=LangCb(action="progress", lang=lang))
    b.button(text=t.BTN_BACK, callback_data=MenuCb(action="home"))
    b.adjust(1, 2, 2, 2)
    return b.as_markup()


def _done(builder: InlineKeyboardBuilder, lang: str, topic: str | None) -> None:
    if topic is not None:
        builder.button(text=t.BTN_DONE, callback_data=DoneCb(lang=lang, topic=topic_id(topic)))


def grammar_menu(subject: Subject, topic: str | None) -> InlineKeyboardMarkup:
    lang = subject.code
    b = InlineKeyboardBuilder()
    b.button(text=t.BTN_TODAY, callback_data=LangCb(action="today", lang=lang))
    b.button(text=t.BTN_CHAT, callback_data=ModeCb(mode="chat", lang=lang))
    _done(b, lang, topic)
    _back(b, lang)
    b.adjust(2, 1, 1)
    return b.as_markup()


def writing_menu(subject: Subject) -> InlineKeyboardMarkup:
    lang = subject.code
    b = InlineKeyboardBuilder()
    b.button(text=t.BTN_TRANSLATE, callback_data=ModeCb(mode="translate", lang=lang))
    b.button(text=t.writing_label(subject.writing), callback_data=ModeCb(mode="task", lang=lang))
    _back(b, lang)
    b.adjust(2, 1)
    return b.as_markup()


def lesson_end(subject: Subject, topic: str) -> InlineKeyboardMarkup:
    lang = subject.code
    b = InlineKeyboardBuilder()
    b.button(text=t.BTN_START_CHAT, callback_data=ModeCb(mode="chat", lang=lang))
    _done(b, lang, topic)
    _home(b, lang)
    b.adjust(2, 1)
    return b.as_markup()


def after_done(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t.BTN_NEXT_TOPIC, callback_data=LangCb(action="today", lang=lang))
    b.button(text=t.BTN_PROGRESS, callback_data=LangCb(action="progress", lang=lang))
    _back(b, lang)
    b.adjust(2, 1)
    return b.as_markup()


def progress_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t.BTN_TODAY, callback_data=LangCb(action="today", lang=lang))
    _home(b, lang)
    b.adjust(2)
    return b.as_markup()


def mistakes_kb(lang: str, has_mistakes: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if has_mistakes:
        b.button(text=t.BTN_REVIEW, callback_data=ModeCb(mode="review", lang=lang))
    _home(b, lang)
    b.adjust(1)
    return b.as_markup()


def words_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t.BTN_CHAT, callback_data=ModeCb(mode="chat", lang=lang))
    _home(b, lang)
    b.adjust(2)
    return b.as_markup()


def reminder_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t.BTN_CHAT, callback_data=ModeCb(mode="chat", lang=lang))
    b.button(text=t.BTN_SPEAKING, callback_data=ModeCb(mode="standup", lang=lang))
    _home(b, lang)
    b.adjust(2, 1)
    return b.as_markup()


def home_only(lang: str | None = None) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    _home(b, lang)
    return b.as_markup()


# ─────────────── Suhbat javobi ostida ───────────────

def reply_nav(
    topic: Node | None = None,
    next_node: Node | None = None,
    speak: bool = False,
    lang: str | None = None,
) -> InlineKeyboardMarkup:
    """Suhbat javobi ostidagi navigatsiya; bilim qismida keyingi qism va orqaga."""
    b = InlineKeyboardBuilder()
    rows = []
    if speak:
        b.button(text=t.BTN_SPEAK, callback_data=MenuCb(action="speak"))
        rows.append(1)
    if topic is None:
        _home(b, lang)
        b.adjust(*rows, 1)
        return b.as_markup()
    if next_node is not None:
        b.button(text=t.btn_next_subsection(next_node.title), callback_data=KnowCb(id=next_node.id))
        rows.append(1)
    b.button(text=t.BTN_SUBSECTIONS, callback_data=KnowCb(id=topic.id))
    _home(b)
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
    _home(b)
    rows.append(2)
    b.adjust(*rows)
    return b.as_markup()


def _page_of(node: Node) -> int:
    """Orqaga bosilganda ota ro'yxatining shu tugun turgan sahifasi ochiladi."""
    assert node.parent is not None
    return node.parent.children.index(node) // PAGE_SIZE
