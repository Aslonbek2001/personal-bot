"""Telegram handler'lari: menyu, dars, suhbat va tech bo'limi."""

import asyncio
import html
import logging
import re

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
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

from bot import claude, storage, voice
from bot import keyboards as kb
from bot.card import render_card
from bot.config import settings

log = logging.getLogger(__name__)

router = Router()
router.message.filter(F.from_user.id == settings.owner_id)
router.callback_query.filter(F.from_user.id == settings.owner_id)

MAX_LENGTH = 4000
BOLD = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
ERROR_TEXT = "⚠️ Claude bilan bog'lanib bo'lmadi. Birozdan keyin qayta urinib ko'ring."
MAX_VOICE_SECONDS = 300
GREETING = (
    "Salom! 👋 Men sizning shaxsiy ingliz tili va tech mentoringizman.\n\n"
    f"☀️ Har kuni {settings.lesson_hour:02d}:00 da yangi dars keladi.\n"
    "✍️ Inglizcha yozing yoki 🎙 ovozli xabar yuboring: xatolaringizni tuzataman.\n"
    "🧠 Tech bo'limida backend, RAG va ML mavzularini takrorlaymiz."
)


class Tech(StatesGroup):
    sections = State()
    topics = State()
    subsections = State()
    chat = State()


TECH_STATES = {Tech.sections.state, Tech.topics.state, Tech.subsections.state, Tech.chat.state}


# ─────────────── Formatlash va yuborish ───────────────

def esc(text: str) -> str:
    return html.escape(text, quote=False)


def fmt(text: str) -> str:
    """Claude matni: HTML'ni ekranlaydi, **qalin** ni <b> ga aylantiradi."""
    return BOLD.sub(r"<b>\1</b>", esc(text))


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


async def remember_options(state: FSMContext, message_id: int, options: list[str]) -> None:
    """Javob variantlarini xabar ID'si bo'yicha saqlaydi (oxirgi 20 ta xabar)."""
    data = await state.get_data()
    stored: dict[str, list[str]] = data.get("options", {})
    stored[str(message_id)] = options
    await state.update_data(options=dict(list(stored.items())[-20:]))


# ─────────────── Matnlar ───────────────

def menu_text() -> str:
    topic = storage.todays_topic()
    progress = storage.progress()
    if topic is None:
        today_line = "🎉 Barcha mavzular tugadi"
    else:
        today_line = f"📖 Bugun: {esc(short(topic))}" + (" ✅" if storage.is_done_today() else "")
    return f"🏠 <b>Asosiy menyu</b>\n\n{today_line}\n📊 Progress: {progress.count}/{progress.total}"


def progress_text() -> str:
    progress = storage.progress()
    filled = round(progress.percent / 10)
    bar = "▓" * filled + "░" * (10 - filled)
    lines = [
        "📊 <b>Progress</b>",
        "",
        f"Grammatika: {progress.count}/{progress.total}",
        f"{bar} {progress.percent}%",
    ]
    if progress.done:
        lines += ["", "<b>Oxirgi tugallangan mavzular:</b>"]
        lines += [f"• {entry.day:%d.%m} — {esc(short(entry.topic))}" for entry in progress.done[-10:]]
    topic = storage.todays_topic()
    if topic:
        lines += ["", f"📖 Bugun: {esc(short(topic))} {'✅' if storage.is_done_today() else '⏳'}"]
    return "\n".join(lines)


def reply_text(
    reply: claude.ChatReply,
    *,
    chosen: str | None = None,
    transcript: str | None = None,
) -> str:
    parts = []
    if transcript:
        parts.append(f"🎙 <b>Eshitildi:</b> <i>{esc(transcript)}</i>")
    if chosen:
        parts.append(f"➡️ <i>{esc(chosen)}</i>")
    if reply.corrected:
        parts.append(f"✏️ <b>Sizning gapingiz (to'g'rilangan):</b>\n{fmt(reply.corrected)}")
    if reply.improved:
        parts.append(f"🚀 <b>Kuchaytirilgan versiya:</b>\n{fmt(reply.improved)}")
    parts.append(f"💬 {fmt(reply.reply)}")
    parts.append(f"❓ <b>{esc(reply.question)}</b>")
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
        f"❓ <b>{esc(ex.question)}</b>",
    ])


# ─────────────── Kunlik dars ───────────────

_lessons: dict[tuple, claude.Lesson] = {}
_lesson_lock = asyncio.Lock()


async def get_lesson(topic: str) -> claude.Lesson:
    """Bugungi darsni bir marta yaratadi va kun davomida xotiradan beradi."""
    key = (storage.today(), topic)
    async with _lesson_lock:
        if key not in _lessons:
            lesson = await claude.make_lesson(topic)
            _lessons.clear()
            _lessons[key] = lesson
        return _lessons[key]


async def send_lesson(bot: Bot, chat_id: int, morning: bool = False) -> None:
    topic = storage.todays_topic()
    if topic is None:
        await bot.send_message(chat_id, "🎉 topics.md dagi barcha mavzular tugadi! Yangi mavzular qo'shing.")
        return
    try:
        async with ChatActionSender.upload_photo(bot=bot, chat_id=chat_id):
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
    await callback.answer()
    await state.set_state(None)
    await send_lesson(callback.bot, callback.from_user.id)


@router.callback_query(kb.MenuCb.filter(F.action == "chat"))
async def start_chat(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(None)
    chat_id = callback.from_user.id
    topic = storage.todays_topic()
    title = short(topic) if topic else "free practice"
    try:
        async with ChatActionSender.typing(bot=callback.bot, chat_id=chat_id):
            opening = await claude.opening_question(title)
    except Exception:
        log.exception("Suhbat boshlanmadi")
        await callback.bot.send_message(chat_id, ERROR_TEXT)
        return
    sent = await send_text(
        callback.bot, chat_id,
        f"💬 {fmt(opening.message)}\n\n❓ <b>{esc(opening.question)}</b>",
        kb.answer(opening.options),
    )
    await state.update_data(
        history_day=storage.today().isoformat(),
        practice_history=[
            {"role": "user", "content": "Let's start the chat practice."},
            {"role": "assistant", "content": f"{opening.message}\n{opening.question}"},
        ],
    )
    await remember_options(state, sent.message_id, opening.options)


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
        f"✅ <b>Zo'r! Mavzu yakunlandi.</b>\n\n\"{esc(short(topic))}\" process.md ga yozildi.\n{tomorrow}",
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
        "🧠 <b>Tech bilimlar</b>\n\nBo'limni tanlang. Bu qism process.md ga yozilmaydi.",
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
    await callback.answer()
    chat_id = callback.from_user.id
    try:
        async with ChatActionSender.typing(bot=callback.bot, chat_id=chat_id):
            ex = await claude.explain_subsection(*names)
    except Exception:
        log.exception("Tushuntirish yaratilmadi")
        await callback.bot.send_message(chat_id, ERROR_TEXT)
        return
    sent = await send_text(
        callback.bot, chat_id,
        explanation_text(names, ex),
        kb.answer(ex.options, tech=(s, t, u), next_name=tech_next_name(s, t, u)),
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
    await remember_options(state, sent.message_id, ex.options)


# ─────────────── Suhbat: matn va javob variantlari ───────────────

async def respond(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
    text: str,
    *,
    reply_to: int | None = None,
    chosen: bool = False,
    is_voice: bool = False,
) -> None:
    """Holatga qarab practice yoki tech javobini oladi va yuboradi."""
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

    today = storage.today().isoformat()
    if in_tech:
        history_key = "tech_history"
        history = data.get(history_key, [])
    else:
        history_key = "practice_history"
        history = data.get(history_key, []) if data.get("history_day") == today else []

    try:
        async with ChatActionSender.typing(bot=bot, chat_id=chat_id):
            if in_tech:
                reply = await claude.tech_reply(text, history, scope_names, is_voice)
            else:
                topic = storage.todays_topic()
                reply = await claude.practice_reply(text, history, short(topic) if topic else "free practice", is_voice)
    except Exception:
        log.exception("Javob olinmadi")
        await bot.send_message(chat_id, ERROR_TEXT)
        return

    body = reply_text(reply, chosen=text if chosen else None, transcript=text if is_voice else None)
    sent = await send_text(bot, chat_id, body, kb.answer(reply.options, tech=tech_nav, next_name=next_name), reply_to)

    history = [
        *history,
        {"role": "user", "content": text},
        {"role": "assistant", "content": f"{reply.reply}\n{reply.question}"},
    ][-settings.history_limit * 2:]
    await state.update_data({history_key: history, "history_day": today})
    await remember_options(state, sent.message_id, reply.options)


@router.callback_query(kb.OptionCb.filter())
async def option_chosen(callback: CallbackQuery, callback_data: kb.OptionCb, state: FSMContext) -> None:
    data = await state.get_data()
    message_id = callback.message.message_id if callback.message else 0
    options = data.get("options", {}).get(str(message_id), [])
    if callback_data.n >= len(options):
        await callback.answer("Bu variant eskirgan, javobni yozib yuboring")
        return
    await callback.answer()
    await respond(callback.bot, callback.from_user.id, state, options[callback_data.n],
                  reply_to=message_id, chosen=True)


@router.message(F.text & ~F.text.startswith("/"))
async def on_text(message: Message, state: FSMContext) -> None:
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
    try:
        async with ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id):
            audio = await message.bot.download(media)
            text = await voice.transcribe(audio.read(), prompt=await voice_prompt(state))
    except Exception:
        log.exception("Ovoz matnga o'girilmadi")
        await message.reply("⚠️ Ovozni matnga o'girib bo'lmadi. Qaytadan yuboring.")
        return
    if not text:
        await message.reply("🤔 Hech narsa eshitilmadi. Telefonni og'zingizga yaqinroq tutib qayta yuboring.")
        return
    await respond(message.bot, message.chat.id, state, text, reply_to=message.message_id, is_voice=True)