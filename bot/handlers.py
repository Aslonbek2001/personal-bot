"""Telegram handler'lari: menyu, dars, mashq rejimlari, tech bo'limi va rejali xabarlar."""

import asyncio
import html
import logging
import random
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardMarkup,
    Message,
    ReplyParameters,
)
from aiogram.utils.chat_action import ChatActionSender

from bot import claude, db, storage, voice
from bot import keyboards as kb
from bot.ui.card import render_card
from bot.config import settings

log = logging.getLogger(__name__)

router = Router()
router.message.filter(F.from_user.id == settings.owner_id)
router.callback_query.filter(F.from_user.id == settings.owner_id)

MAX_LENGTH = 4000
CODE = re.compile(r"`([^`\n]+)`")
BOLD = re.compile(r"\*\*([^\n]+?)\*\*")
ITALIC = re.compile(r"(?<![\w*])\*(?=\S)([^*\n]+?)(?<=\S)\*(?![\w*])")
BLANK_LINES = re.compile(r"\n\s*\n")
ERROR_TEXT = "⚠️ Claude bilan bog'lanib bo'lmadi. Birozdan keyin qayta urinib ko'ring."
MAX_VOICE_SECONDS = 300
BUSY_TEXT = "⏳ Oldingi javob tayyorlanmoqda, biroz kuting."
DRAFT_REFRESH = 20
MARKUP = re.compile(r"[*`]")
GREETING = (
    "Salom! 👋 Men sizning shaxsiy ingliz tili va tech mentoringizman.\n\n"
    f"☀️ Har kuni {settings.lesson_hour:02d}:00 da yangi dars keladi.\n"
    "✍️ Inglizcha yozing yoki 🎙 ovozli xabar yuboring: xatolaringizni tuzataman.\n"
    "🔁 Tarjima, 💼 ish yozishmasi va 🎙 stand-up rejimlarida yozish va gapirishni mashq qilamiz.\n"
    "📝 Xatolaringiz saqlanadi va haftada bir marta takrorlanadi.\n"
    f"🌙 {settings.reminder_hour:02d}:00 da kunlik natija keladi.\n"
    "🧠 Tech bo'limida backend, RAG va ML mavzularini takrorlaymiz."
)
MODE_ICONS = {"chat": "💬", "translate": "🔁", "task": "💼", "standup": "🎙", "review": "📝"}
REVIEW_DAYS = 14
SPEAK_KEEP = 20


class Tech(StatesGroup):
    sections = State()
    topics = State()
    subsections = State()
    chat = State()


TECH_STATES = {Tech.sections.state, Tech.topics.state, Tech.subsections.state, Tech.chat.state}


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


# ─────────────── Formatlash va yuborish ───────────────

def esc(text: str) -> str:
    return html.escape(text, quote=False)


def fmt(text: str) -> str:
    """Claude matni: HTML'ni ekranlaydi; `kod`, **qalin**, *kursiv* ni teglarga aylantiradi."""
    text = CODE.sub(r"<code>\1</code>", esc(text))
    text = BOLD.sub(r"<b>\1</b>", text)
    return ITALIC.sub(r"<i>\1</i>", text)


def quote(text: str) -> str:
    """Blockquote; bo'sh qatorlar olib tashlanadi, aks holda split_text blokni bo'lib yuboradi."""
    return f"<blockquote>{BLANK_LINES.sub(chr(10), fmt(text).strip())}</blockquote>"


def question(text: str) -> str:
    return f"❓ <b>{esc(MARKUP.sub('', text))}</b>"


def short(topic: str) -> str:
    """'Past Simple - reporting ...' -> 'Past Simple'."""
    return topic.split(" - ")[0]


def split_text(text: str, limit: int = MAX_LENGTH) -> list[str]:
    """Uzun matnni paragraflar bo'yicha Telegram limitiga sig'adigan qismlarga bo'ladi."""
    parts: list[str] = []
    current = ""
    for paragraph in text.split("\n\n"):
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            parts.append(current)
        while len(paragraph) > limit:
            parts.append(paragraph[:limit])
            paragraph = paragraph[limit:]
        current = paragraph
    if current:
        parts.append(current)
    return parts


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


# ─────────────── Matnlar ───────────────

def topic_title() -> str:
    topic = storage.todays_topic()
    return short(topic) if topic else "free practice"


def words_line(words: list[db.DayWord]) -> str:
    return f"🔤 So'zlar: {sum(w.used for w in words)}/{len(words)}"


def menu_text() -> str:
    topic = storage.todays_topic()
    progress = storage.progress()
    if topic is None:
        today_line = "🎉 Barcha mavzular tugadi"
    else:
        today_line = f"📖 Bugun: {esc(short(topic))}" + (" ✅" if storage.is_done_today() else "")
    lines = ["🏠 <b>Asosiy menyu</b>", "", today_line, f"📊 Progress: {progress.count}/{progress.total}"]
    words = db.day_words(storage.today())
    if words:
        lines.append(words_line(words))
    return "\n".join(lines)


def progress_text() -> str:
    progress = storage.progress()
    filled = round(progress.percent / 10)
    bar = "▓" * filled + "░" * (10 - filled)
    week = db.stats(storage.today() - timedelta(days=6))
    lines = [
        "📊 <b>Progress</b>",
        "",
        f"Grammatika: {progress.count}/{progress.total}",
        f"{bar} {progress.percent}%",
        "",
        "<b>Oxirgi 7 kun:</b>",
        f"✍️ Javoblar: {week.answers} ta, {week.words} so'z",
        f"📝 Xatolar: {week.mistakes} ta",
    ]
    if week.wpm:
        lines.append(f"🗣 Gapirish tezligi: {week.wpm} so'z/daqiqa")
    if progress.done:
        lines += ["", "<b>Oxirgi tugallangan mavzular:</b>"]
        lines += [f"• {entry.day:%d.%m} — {esc(short(entry.topic))}" for entry in progress.done[-10:]]
    topic = storage.todays_topic()
    if topic:
        lines += ["", f"📖 Bugun: {esc(short(topic))} {'✅' if storage.is_done_today() else '⏳'}"]
        words = db.day_words(storage.today())
        if words:
            lines.append(words_line(words))
    return "\n".join(lines)


def mistakes_text(mistakes: list[db.Mistake]) -> str:
    week = db.mistakes_count(storage.today() - timedelta(days=6))
    lines = ["📝 <b>Xatolarim</b>", "", f"Oxirgi 7 kunda: {week} ta"]
    if not mistakes:
        return "\n".join([*lines, "", "Hali xatolar yo'q. Yozing yoki gapiring — xatolar shu yerda to'planadi."])
    lines.append("")
    lines += [
        f"• <s>{esc(m.wrong)}</s> → <b>{esc(m.right)}</b>\n   {fmt(m.note)}"
        for m in mistakes
    ]
    return "\n".join(lines)


def words_text(words: list[db.DayWord]) -> str:
    if not words:
        return "🔤 Bugungi so'zlar hali yo'q. Avval 📚 Bugungi dars ni oching."
    lines = [f"🔤 <b>Bugungi so'zlar: {sum(w.used for w in words)}/{len(words)}</b>", ""]
    lines += [f"{'✅' if w.used else '▫️'} <b>{esc(w.word)}</b> — {esc(w.uz)}" for w in words]
    lines += ["", "Suhbatda ishlatgan so'zlaringiz ✅ bilan belgilanadi."]
    return "\n".join(lines)


def reply_text(
    reply: claude.ChatReply,
    *,
    transcript: str | None = None,
    seconds: int | None = None,
    used: list[str] | None = None,
    words: list[db.DayWord] | None = None,
) -> str:
    parts = []
    if transcript:
        voice_lines = [f"🎙 <b>Eshitildi:</b> <i>{esc(transcript)}</i>"]
        if seconds:
            count = len(transcript.split())
            voice_lines.append(f"🗣 {count} so'z · {seconds} s · {round(count * 60 / seconds)} so'z/daqiqa")
        parts.append("\n".join(voice_lines))
    if reply.corrected:
        lines = ["✏️ <b>To'g'rilangan:</b>", quote(reply.corrected)]
        lines += [
            f"• <s>{esc(fix.wrong)}</s> → <b>{esc(fix.right)}</b>\n   {fmt(fix.note)}"
            for fix in reply.fixes
        ]
        parts.append("\n".join(lines))
    if reply.improved:
        parts.append(f"🚀 <b>Tabiiyroq:</b>\n{quote(reply.improved)}")
    if reply.tip:
        parts.append(f"📌 <b>Eslatma:</b>\n{quote(reply.tip)}")
    if used and words:
        names = ", ".join(f"<b>{esc(word)}</b>" for word in used)
        parts.append(f"🔤 Bugungi so'zlar: {names} ({sum(w.used for w in words)}/{len(words)})")
    parts.append(f"💬 {fmt(reply.reply)}")
    parts.append(question(reply.question))
    return "\n\n".join(parts)


def explanation_text(names: tuple[str, str, str], ex: claude.Explanation) -> str:
    section, topic, subsection = names
    mistakes = "\n".join(f"• {fmt(item)}" for item in ex.mistakes)
    return "\n\n".join([
        f"🧠 {esc(section)} › {esc(topic)}\n<b>{esc(subsection)}</b>",
        f"<b>1. What it is</b>\n{fmt(ex.what)}",
        f"<b>2. Why it exists</b>\n{fmt(ex.why)}",
        f"<b>3. How it works</b>\n{fmt(ex.how)}",
        f"<b>4. Where it lives</b>\n{fmt(ex.where)}",
        f"<b>5. Real example</b>\n{fmt(ex.example)}",
        f"<b>6. Common mistakes</b>\n{mistakes}",
        question(ex.question),
    ])


# ─────────────── Kunlik dars ───────────────

_lesson_lock = asyncio.Lock()


async def get_lesson(topic: str) -> claude.Lesson:
    """Bugungi darsni bir marta yaratadi va DB da saqlaydi."""
    day = storage.today()
    async with _lesson_lock:
        saved = db.get_lesson(day, topic)
        if saved:
            return claude.Lesson.model_validate_json(saved)
        lesson = await claude.make_lesson(topic)
        words = [(w.word, w.uz, w.example) for w in lesson.words]
        db.save_lesson(day, topic, lesson.model_dump_json(), words)
        return lesson


async def send_lesson(bot: Bot, chat_id: int, morning: bool = False) -> None:
    topic = storage.todays_topic()
    if topic is None:
        await bot.send_message(chat_id, "🎉 topics.md dagi barcha mavzular tugadi! Yangi mavzular qo'shing.")
        return
    try:
        async with thinking(bot, chat_id):
            lesson = await get_lesson(topic)
    except Exception:
        log.exception("Dars yaratilmadi")
        await bot.send_message(chat_id, "⚠️ Darsni tayyorlab bo'lmadi. Birozdan keyin 📚 Bugungi dars ni bosing.",
                               reply_markup=kb.main_menu())
        return

    topics = storage.read_topics()
    number = topics.index(topic) + 1 if topic in topics else 0
    png = await asyncio.to_thread(render_card, lesson, number, len(topics), storage.today())
    caption = ("☀️ Xayrli tong! " if morning else "📚 ") + f"Bugungi mavzu: {esc(lesson.title)}"
    await bot.send_photo(chat_id, BufferedInputFile(png, filename="lesson.png"), caption=caption)

    await send_text(bot, chat_id, f"📘 <b>1. Grammar</b>\n\n{fmt(lesson.grammar)}")
    await send_text(bot, chat_id, f"📖 <b>2. {esc(lesson.story_title)}</b>\n\n{fmt(lesson.story)}")
    words = "\n".join(
        f"{n}. <b>{esc(w.word)}</b> — {esc(w.uz)}\n    <i>{esc(w.example)}</i>"
        for n, w in enumerate(lesson.words, start=1)
    )
    await send_text(bot, chat_id, f"🔤 <b>3. {len(lesson.words)} words of the day</b>\n\n{words}", kb.lesson_end())


# ─────────────── /start va menyu ───────────────

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(GREETING)
    sent = await message.answer(menu_text(), reply_markup=kb.main_menu())
    await state.update_data(nav_id=sent.message_id)


@router.callback_query(kb.MenuCb.filter(F.action == "home"))
async def open_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(None)
    await show_nav(callback, state, menu_text(), kb.main_menu())


@router.callback_query(kb.MenuCb.filter(F.action == "today"))
async def today_lesson(callback: CallbackQuery, state: FSMContext) -> None:
    async with exclusive(callback.from_user.id) as free:
        if not free:
            await callback.answer(BUSY_TEXT)
            return
        await callback.answer()
        await state.set_state(None)
        await send_lesson(callback.bot, callback.from_user.id)


def today_words() -> list[str]:
    return [w.word for w in db.day_words(storage.today())]


def review_mistakes() -> list[str]:
    since = storage.today() - timedelta(days=REVIEW_DAYS)
    return [f"{m.wrong} -> {m.right}" for m in db.recent_mistakes(30, since)]


async def start_mode(bot: Bot, chat_id: int, state: FSMContext, mode: str) -> None:
    await state.set_state(None)
    mistakes = review_mistakes() if mode == "review" else []
    if mode == "review" and not mistakes:
        await bot.send_message(chat_id, "📝 Oxirgi 2 haftada xato topilmadi. Zo'r! 🎉", reply_markup=kb.main_menu())
        return
    try:
        async with thinking(bot, chat_id):
            opening = await claude.opening(mode, topic_title(), today_words(), mistakes)
    except Exception:
        log.exception("Rejim boshlanmadi: %s", mode)
        await bot.send_message(chat_id, ERROR_TEXT)
        return
    await send_text(
        bot, chat_id,
        f"{MODE_ICONS[mode]} {fmt(opening.message)}\n\n{question(opening.question)}",
        kb.reply_nav(),
    )
    await state.update_data(
        mode=mode,
        history_day=storage.today().isoformat(),
        history=[
            {"role": "user", "content": "Let's start. Give me the first question or task."},
            {"role": "assistant", "content": f"{opening.message}\n{opening.question}"},
        ],
    )


@router.callback_query(kb.ModeCb.filter())
async def mode_chosen(callback: CallbackQuery, callback_data: kb.ModeCb, state: FSMContext) -> None:
    if callback_data.mode not in MODE_ICONS:
        await callback.answer()
        return
    async with exclusive(callback.from_user.id) as free:
        if not free:
            await callback.answer(BUSY_TEXT)
            return
        await callback.answer()
        await start_mode(callback.bot, callback.from_user.id, state, callback_data.mode)


@router.callback_query(kb.MenuCb.filter(F.action == "mistakes"))
async def show_mistakes(callback: CallbackQuery) -> None:
    await callback.answer()
    mistakes = db.recent_mistakes(15)
    await send_text(callback.bot, callback.from_user.id, mistakes_text(mistakes), kb.mistakes_kb(bool(mistakes)))


@router.callback_query(kb.MenuCb.filter(F.action == "words"))
async def show_words(callback: CallbackQuery) -> None:
    await callback.answer()
    words = db.day_words(storage.today())
    await callback.bot.send_message(callback.from_user.id, words_text(words), reply_markup=kb.words_kb())


@router.callback_query(kb.MenuCb.filter(F.action == "done"))
async def mark_done(callback: CallbackQuery) -> None:
    topic = storage.todays_topic()
    if topic is None:
        await callback.answer("Barcha mavzular tugagan")
        return
    if not storage.mark_done(topic):
        await callback.answer("Bugungi mavzu allaqachon belgilangan")
        return
    await callback.answer("✅ Belgilandi")
    done = {entry.topic for entry in storage.read_process()}
    upcoming = next((t for t in storage.read_topics() if t not in done), None)
    tomorrow = f"📅 Ertaga: {esc(short(upcoming))}" if upcoming else "🎉 Bu oxirgi mavzu edi!"
    await callback.bot.send_message(
        callback.from_user.id,
        f"✅ <b>Zo'r! Mavzu yakunlandi.</b>\n\n\"{esc(short(topic))}\" progressga yozildi.\n{tomorrow}",
        reply_markup=kb.after_done(),
    )


@router.callback_query(kb.MenuCb.filter(F.action == "progress"))
async def show_progress(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.bot.send_message(callback.from_user.id, progress_text(), reply_markup=kb.progress_kb())


# ─────────────── Tech bo'limi ───────────────

async def tech_list_changed(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer("tech.md o'zgargan, qaytadan tanlang")
    await state.set_state(Tech.sections)
    await show_nav(callback, state, "🧠 <b>Tech bilimlar</b>\n\nBo'limni tanlang:", kb.tech_sections(storage.read_tech()))


@router.callback_query(kb.TechCb.filter(F.level == "root"))
async def tech_root(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(Tech.sections)
    await show_nav(
        callback, state,
        "🧠 <b>Tech bilimlar</b>\n\nBo'limni tanlang. Bu qism grammatika progressiga kirmaydi.",
        kb.tech_sections(storage.read_tech()),
    )


@router.callback_query(kb.TechCb.filter(F.level == "section"))
async def tech_section(callback: CallbackQuery, callback_data: kb.TechCb, state: FSMContext) -> None:
    sections = storage.read_tech()
    if callback_data.s >= len(sections):
        await tech_list_changed(callback, state)
        return
    await callback.answer()
    await state.set_state(Tech.topics)
    text = f"🧠 <b>{esc(sections[callback_data.s].name)}</b>\n\nMavzuni tanlang:"
    await show_nav(callback, state, text, kb.tech_topics(sections, callback_data.s))


@router.callback_query(kb.TechCb.filter(F.level == "topic"))
async def tech_topic(callback: CallbackQuery, callback_data: kb.TechCb, state: FSMContext) -> None:
    sections = storage.read_tech()
    s, t = callback_data.s, callback_data.t
    if s >= len(sections) or t >= len(sections[s].topics):
        await tech_list_changed(callback, state)
        return
    await callback.answer()
    await state.set_state(Tech.subsections)
    text = f"🧠 {esc(sections[s].name)} › <b>{esc(sections[s].topics[t].name)}</b>\n\nQismni tanlang:"
    await show_nav(callback, state, text, kb.tech_subsections(sections, s, t))


def tech_next_name(s: int, t: int, u: int) -> str | None:
    subsections = storage.read_tech()[s].topics[t].subsections
    return subsections[u + 1] if u + 1 < len(subsections) else None


@router.callback_query(kb.TechCb.filter(F.level == "sub"))
async def tech_subsection(callback: CallbackQuery, callback_data: kb.TechCb, state: FSMContext) -> None:
    s, t, u = callback_data.s, callback_data.t, callback_data.u
    try:
        names = storage.tech_item(s, t, u)
    except LookupError:
        await tech_list_changed(callback, state)
        return
    chat_id = callback.from_user.id
    async with exclusive(chat_id) as free:
        if not free:
            await callback.answer(BUSY_TEXT)
            return
        await callback.answer()
        await explain(callback.bot, chat_id, state, names, (s, t, u))


async def explain(
    bot: Bot, chat_id: int, state: FSMContext, names: tuple[str, str, str], nav: tuple[int, int, int]
) -> None:
    s, t, u = nav
    try:
        async with thinking(bot, chat_id):
            ex = await claude.explain_subsection(*names)
    except Exception:
        log.exception("Tushuntirish yaratilmadi")
        await bot.send_message(chat_id, ERROR_TEXT)
        return
    await send_text(
        bot, chat_id,
        explanation_text(names, ex),
        kb.reply_nav(tech=(s, t, u), next_name=tech_next_name(s, t, u)),
    )
    summary = f"{ex.what}\n{ex.how}\n{ex.where}\n{ex.question}"
    await state.set_state(Tech.chat)
    await state.update_data(
        scope=[s, t, u],
        tech_history=[
            {"role": "user", "content": f"Explain: {names[2]}"},
            {"role": "assistant", "content": summary},
        ],
    )


# ─────────────── Suhbat: matn va ovoz ───────────────

async def respond(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
    text: str,
    *,
    reply_to: int | None = None,
    seconds: int | None = None,
) -> None:
    """Holatga qarab mashq yoki tech javobini oladi, natijani DB ga yozadi va yuboradi."""
    current = await state.get_state()
    data = await state.get_data()
    in_tech = current in TECH_STATES

    scope_names: tuple[str, str, str] | None = None
    tech_nav: tuple[int, int, int] | None = None
    next_name: str | None = None
    if current == Tech.chat.state and data.get("scope"):
        s, t, u = data["scope"]
        try:
            scope_names = storage.tech_item(s, t, u)
            tech_nav, next_name = (s, t, u), tech_next_name(s, t, u)
        except LookupError:
            pass

    day = storage.today()
    if in_tech:
        mode, history_key = "tech", "tech_history"
        history = data.get(history_key, [])
    else:
        mode, history_key = data.get("mode", "chat"), "history"
        history = data.get(history_key, []) if data.get("history_day") == day.isoformat() else []

    try:
        async with thinking(bot, chat_id):
            if in_tech:
                reply = await claude.tech_reply(text, history, scope_names, seconds)
            else:
                mistakes = review_mistakes() if mode == "review" else []
                reply = await claude.practice_reply(
                    text, history, mode, topic_title(), today_words(), mistakes, seconds
                )
    except Exception:
        log.exception("Javob olinmadi")
        await bot.send_message(chat_id, ERROR_TEXT)
        return

    words = db.day_words(day)
    used = storage.find_used_words(text, [w.word for w in words if not w.used])
    if used:
        db.mark_words_used(day, used)
        words = db.day_words(day)
    db.add_answer(mode, text, len(text.split()), seconds, len(reply.fixes))
    db.add_mistakes([(fix.wrong, fix.right, fix.note) for fix in reply.fixes])

    speak = MARKUP.sub("", reply.improved or reply.corrected or "").strip()
    body = reply_text(
        reply,
        transcript=text if seconds is not None else None,
        seconds=seconds,
        used=used,
        words=words,
    )
    sent = await send_text(
        bot, chat_id, body,
        kb.reply_nav(tech=tech_nav, next_name=next_name, speak=bool(speak)),
        reply_to,
    )

    history = [
        *history,
        {"role": "user", "content": text},
        {"role": "assistant", "content": f"{reply.reply}\n{reply.question}"},
    ][-settings.history_limit * 2:]
    update: dict = {history_key: history, "history_day": day.isoformat()}
    if speak:
        stored = data.get("speak", {})
        stored[str(sent.message_id)] = speak
        update["speak"] = dict(list(stored.items())[-SPEAK_KEEP:])
    await state.update_data(update)


@router.callback_query(kb.MenuCb.filter(F.action == "speak"))
async def speak_reply(callback: CallbackQuery, state: FSMContext) -> None:
    message_id = callback.message.message_id if callback.message else 0
    text = (await state.get_data()).get("speak", {}).get(str(message_id))
    if not text:
        await callback.answer("Bu xabar eskirgan")
        return
    chat_id = callback.from_user.id
    async with exclusive(chat_id) as free:
        if not free:
            await callback.answer(BUSY_TEXT)
            return
        await callback.answer()
        try:
            async with ChatActionSender.record_voice(bot=callback.bot, chat_id=chat_id):
                audio = await voice.speak(text)
        except Exception:
            log.exception("Ovoz yaratilmadi")
            await callback.bot.send_message(chat_id, "⚠️ Ovozni yaratib bo'lmadi. Birozdan keyin qayta urinib ko'ring.")
            return
    await callback.bot.send_voice(
        chat_id,
        BufferedInputFile(audio, filename="speech.ogg"),
        caption=f"🔊 <i>{esc(text)}</i>"[:1000],
        reply_parameters=ReplyParameters(message_id=message_id, allow_sending_without_reply=True),
    )


@router.message(F.text & ~F.text.startswith("/"))
async def on_text(message: Message, state: FSMContext) -> None:
    async with exclusive(message.chat.id) as free:
        if not free:
            await message.reply(BUSY_TEXT)
            return
        await respond(message.bot, message.chat.id, state, message.text, reply_to=message.message_id)


async def voice_prompt(state: FSMContext) -> str:
    """Whisper'ga mavzu nomini beradi: atamalar to'g'riroq taniladi."""
    if await state.get_state() == Tech.chat.state:
        scope = (await state.get_data()).get("scope")
        if scope:
            try:
                _, topic, subsection = storage.tech_item(*scope)
                return f"{topic}. {subsection}."
            except LookupError:
                pass
    topic = storage.todays_topic()
    return f"{short(topic)}." if topic else ""


@router.message(F.voice | F.audio | F.video_note)
async def on_voice(message: Message, state: FSMContext) -> None:
    media = message.voice or message.audio or message.video_note
    if media.duration and media.duration > MAX_VOICE_SECONDS:
        await message.reply(f"⏱ Ovozli xabar {MAX_VOICE_SECONDS // 60} daqiqadan oshmasin.")
        return
    async with exclusive(message.chat.id) as free:
        if not free:
            await message.reply(BUSY_TEXT)
            return
        try:
            async with thinking(message.bot, message.chat.id):
                audio = await message.bot.download(media)
                text = await voice.transcribe(audio.read(), prompt=await voice_prompt(state))
        except Exception:
            log.exception("Ovoz matnga o'girilmadi")
            await message.reply("⚠️ Ovozni matnga o'girib bo'lmadi. Qaytadan yuboring.")
            return
        if not text:
            await message.reply("🤔 Hech narsa eshitilmadi. Telefonni og'zingizga yaqinroq tutib qayta yuboring.")
            return
        await respond(message.bot, message.chat.id, state, text, reply_to=message.message_id, seconds=media.duration or 0)


# ─────────────── Rejali xabarlar ───────────────

async def evening_summary(bot: Bot, chat_id: int) -> None:
    today = storage.today()
    stats = db.stats(today)
    words = db.day_words(today)
    if not stats.answers:
        await bot.send_message(
            chat_id,
            "🌙 <b>Bugun hali mashq qilmadingiz.</b>\n\n10 daqiqa ajrating: bir nechta gap yozing "
            "yoki ovozli xabar yuboring.",
            reply_markup=kb.reminder_kb(),
        )
        return
    lines = [
        "🌙 <b>Bugungi natija</b>",
        "",
        f"✍️ Javoblar: {stats.answers} ta, {stats.words} so'z",
        f"📝 Xatolar: {stats.mistakes} ta",
    ]
    if stats.wpm:
        lines.append(f"🗣 Gapirish tezligi: {stats.wpm} so'z/daqiqa")
    if words:
        lines.append(words_line(words))
        unused = [w.word for w in words if not w.used]
        if unused:
            lines += ["", "Ishlatilmagan so'zlar: " + ", ".join(esc(word) for word in unused[:10])]
    await bot.send_message(chat_id, "\n".join(lines), reply_markup=kb.words_kb())


async def weekly_review(bot: Bot, chat_id: int, state: FSMContext) -> None:
    if not db.mistakes_count(storage.today() - timedelta(days=6)):
        return
    await bot.send_message(chat_id, "📝 <b>Haftalik takrorlash</b>\n\nShu haftadagi xatolaringiz ustida ishlaymiz.")
    await start_mode(bot, chat_id, state, "review")
