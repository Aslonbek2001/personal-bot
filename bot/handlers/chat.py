"""Suhbat: matnli xabarga mashq yoki bilim qismi bo'yicha javob."""

import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.ai import client as ai
from bot.config import settings
from bot.content import loader
from bot.content.models import Subject
from bot.handlers.common import Tech, exclusive, is_tech, send_text, thinking
from bot.handlers.knowledge import scope_node
from bot.handlers.practice import review_mistakes, topic_title
from bot.services import journal, lessons, progress
from bot.ui import keyboards as kb
from bot.ui import texts
from bot.ui.format import plain

log = logging.getLogger(__name__)

router = Router(name="chat")

SPEAK_KEEP = 20


def knowledge_subject(data: dict) -> Subject | None:
    library = loader.current()
    root = library.nodes.get(data.get("subject", ""))
    if root is not None and root.kind == "subject":
        return library.subject_by_root(root)
    return next((s for s in library.subjects if s.type == "knowledge"), None)


def practice_language(data: dict) -> Subject | None:
    """Tanlangan til (FSM dagi lang); tanlanmagan bo'lsa — birinchi til."""
    library = loader.current()
    return library.language_by_code(data.get("lang", "")) or library.default_language


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
    knowledge = knowledge_subject(data) if is_tech(current) else None
    in_tech = knowledge is not None
    subject = knowledge or practice_language(data)
    if subject is None:
        return
    lang = subject.code or settings.stt_language  # suhbat tili: jurnal va so'zlar shu kod bilan
    scope = scope_node(data) if current == Tech.chat.state else None

    day = progress.today()
    if in_tech:
        mode, history_key = "tech", "tech_history"
        history = data.get(history_key, [])
    else:
        mode, history_key = data.get("mode", "chat"), "history"
        history = data.get(history_key, []) if data.get("history_day") == day.isoformat() else []

    try:
        async with thinking(bot, chat_id):
            if in_tech:
                names = scope.scope_names() if scope else None
                reply = await ai.tech_reply(subject, text, history, names, seconds)
            else:
                mistakes = review_mistakes(subject) if mode == "review" else []
                reply = await ai.practice_reply(
                    subject, text, history, mode, topic_title(subject), lessons.today_words(lang), mistakes, seconds
                )
    except Exception:
        log.exception("Javob olinmadi")
        await bot.send_message(chat_id, texts.ERROR)
        return

    words = lessons.day_words(lang, day)
    used = lessons.find_used_words(text, [w.word for w in words if not w.used])
    if used:
        lessons.mark_words_used(lang, day, used)
        words = lessons.day_words(lang, day)
    journal.add_answer(lang, mode, text, len(text.split()), seconds, len(reply.fixes))
    journal.add_mistakes(lang, [(fix.wrong, fix.right, fix.note) for fix in reply.fixes])

    speak = plain(reply.improved or reply.corrected or "").strip() if subject.tts else ""
    body = texts.reply_text(
        reply,
        transcript=text if seconds is not None else None,
        seconds=seconds,
        used=used,
        words=words,
    )
    markup = kb.reply_nav(
        topic=scope.parent if scope else None,
        next_node=scope.next_sibling() if scope else None,
        speak=bool(speak),
        lang=None if in_tech else subject.code,
    )
    sent = await send_text(bot, chat_id, body, markup, reply_to)

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


@router.message(F.text & ~F.text.startswith("/"))
async def on_text(message: Message, state: FSMContext) -> None:
    async with exclusive(message.chat.id) as free:
        if not free:
            await message.reply(texts.BUSY)
            return
        await respond(message.bot, message.chat.id, state, message.text, reply_to=message.message_id)
