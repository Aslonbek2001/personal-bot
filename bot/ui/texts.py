"""Foydalanuvchiga ko'rinadigan barcha o'zbekcha matnlar. Bot nomi — Ustoz."""

from collections.abc import Sequence

from bot.ai.schemas import ChatReply, Explanation, Lesson
from bot.ui.format import esc, fmt, question, quote, short

# ─────────────── Umumiy ───────────────

ERROR = "⚠️ Claude bilan bog'lanib bo'lmadi. Birozdan keyin qayta urinib ko'ring."
BUSY = "⏳ Oldingi javob tayyorlanmoqda, biroz kuting."
STALE = "Bu xabar eskirgan"
LIST_CHANGED = "Ro'yxat o'zgargan, qaytadan tanlang"
MODE_ICONS = {"chat": "💬", "translate": "🔁", "task": "💼", "standup": "🎙", "review": "📝"}

BTN_HOME = "🏠 Menyu"
BTN_BACK = "⬅️ Orqaga"
BTN_GRAMMAR = "📘 Grammatika"
BTN_SPEAKING = "🎙 Speaking"
BTN_WRITING = "✍️ Writing"
BTN_TODAY = "📚 Bugungi dars"
BTN_CHAT = "💬 Suhbat"
BTN_START_CHAT = "💬 Suhbatni boshlash"
BTN_TRANSLATE = "🔁 Tarjima"
BTN_TASK = "💼 Ish yozishmasi"
BTN_STANDUP = "🎙 Stand-up"
BTN_MISTAKES = "📝 Mistakes"
BTN_WORDS = "🔤 So'zlar"
BTN_PROGRESS = "📊 Progress"
BTN_DONE = "✅ Bajardim"
BTN_REVIEW = "🔁 Xatolar ustida ishlash"
BTN_SPEAK = "🔊 Talaffuz"
BTN_SUBSECTIONS = "⬅️ Qismlar"
BTN_PREV = "◀️"
BTN_NEXT = "▶️"


def btn_next_subsection(name: str) -> str:
    return f"➡️ Keyingi qism: {name}"


def greeting(lesson_hour: int, reminder_hour: int) -> str:
    return (
        "Salom! 👋 Men Ustoz — sizning shaxsiy mentoringizman.\n\n"
        f"☀️ Har kuni {lesson_hour:02d}:00 da yangi ingliz tili darsi keladi.\n"
        "✍️ Inglizcha yozing yoki 🎙 ovozli xabar yuboring: xatolaringizni tuzataman.\n"
        "🔁 Tarjima, 💼 ish yozishmasi va 🎙 stand-up rejimlarida yozish va gapirishni mashq qilamiz.\n"
        "📝 Xatolaringiz saqlanadi va haftada bir marta takrorlanadi.\n"
        f"🌙 {reminder_hour:02d}:00 da kunlik natija keladi.\n"
        "💻 Programming bo'limida backend, RAG va ML mavzularini takrorlaymiz."
    )


# ─────────────── Menyular ───────────────

def today_line(topic: str | None, done_today: bool) -> str:
    if topic is None:
        return "🎉 Barcha mavzular tugadi"
    return f"📖 Bugun: {esc(short(topic))}" + (" ✅" if done_today else "")


def today_lines(topic: str | None, done_today: bool, count: int, total: int, words: Sequence) -> list[str]:
    lines = [today_line(topic, done_today)]
    lines.append(f"📊 Progress: {count}/{total}")
    if words:
        lines.append(words_line(words))
    return lines


def main_menu(summary: list[str]) -> str:
    return "\n".join(["🏠 <b>Ustoz</b> — asosiy menyu", "", *summary])


def language_menu(label: str, summary: list[str]) -> str:
    return "\n".join([f"<b>{esc(label)}</b>", "", *summary])


def grammar_menu(topic: str | None, done_today: bool) -> str:
    return "\n".join(["📘 <b>Grammatika</b>", "", today_line(topic, done_today)])


WRITING_MENU = "✍️ <b>Writing</b>\n\nRejimni tanlang:"


def reloaded(subjects: int, topics: int, nodes: int) -> str:
    return f"🔄 Kontent yangilandi: {subjects} ta fan, {topics} ta grammatika mavzusi, {nodes} ta tugun."


def reload_failed(error: Exception) -> str:
    return f"⚠️ Kontentni yuklab bo'lmadi, eski nusxa qoldi:\n<code>{esc(str(error))[:500]}</code>"


# ─────────────── English: dars, progress, so'zlar, xatolar ───────────────

ALL_TOPICS_DONE = "🎉 Barcha grammatika mavzulari tugadi! content/ ga yangi mavzular qo'shing."
LESSON_FAILED = "⚠️ Darsni tayyorlab bo'lmadi. Birozdan keyin 📚 Bugungi dars ni bosing."
NO_REVIEW_MISTAKES = "📝 Oxirgi 2 haftada xato topilmadi. Zo'r! 🎉"
DONE_NOTHING = "Barcha mavzular tugagan"
DONE_ALREADY = "Bugungi mavzu allaqachon belgilangan"
DONE_OK = "✅ Belgilandi"


def lesson_caption(title: str, morning: bool) -> str:
    return ("☀️ Xayrli tong! " if morning else "📚 ") + f"Bugungi mavzu: {esc(title)}"


def lesson_parts(lesson: Lesson) -> list[str]:
    words = "\n".join(
        f"{n}. <b>{esc(w.word)}</b> — {esc(w.uz)}\n    <i>{esc(w.example)}</i>"
        for n, w in enumerate(lesson.words, start=1)
    )
    return [
        f"📘 <b>1. Grammar</b>\n\n{fmt(lesson.grammar)}",
        f"📖 <b>2. {esc(lesson.story_title)}</b>\n\n{fmt(lesson.story)}",
        f"🔤 <b>3. {len(lesson.words)} words of the day</b>\n\n{words}",
    ]


def done_text(topic: str, upcoming: str | None) -> str:
    tomorrow = f"📅 Ertaga: {esc(short(upcoming))}" if upcoming else "🎉 Bu oxirgi mavzu edi!"
    return f"✅ <b>Zo'r! Mavzu yakunlandi.</b>\n\n\"{esc(short(topic))}\" progressga yozildi.\n{tomorrow}"


def words_line(words: Sequence) -> str:
    return f"🔤 So'zlar: {sum(w.used for w in words)}/{len(words)}"


def progress_text(progress, week, topic: str | None, done_today: bool, words: Sequence) -> str:
    filled = round(progress.percent / 10)
    bar = "▓" * filled + "░" * (10 - filled)
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
    if topic:
        lines += ["", f"📖 Bugun: {esc(short(topic))} {'✅' if done_today else '⏳'}"]
        if words:
            lines.append(words_line(words))
    return "\n".join(lines)


def mistakes_text(mistakes: Sequence, week: int) -> str:
    lines = ["📝 <b>Xatolarim</b>", "", f"Oxirgi 7 kunda: {week} ta"]
    if not mistakes:
        return "\n".join([*lines, "", "Hali xatolar yo'q. Yozing yoki gapiring — xatolar shu yerda to'planadi."])
    lines.append("")
    lines += [f"• <s>{esc(m.wrong)}</s> → <b>{esc(m.right)}</b>\n   {fmt(m.note)}" for m in mistakes]
    return "\n".join(lines)


def words_text(words: Sequence) -> str:
    if not words:
        return "🔤 Bugungi so'zlar hali yo'q. Avval 📚 Bugungi dars ni oching."
    lines = [f"🔤 <b>Bugungi so'zlar: {sum(w.used for w in words)}/{len(words)}</b>", ""]
    lines += [f"{'✅' if w.used else '▫️'} <b>{esc(w.word)}</b> — {esc(w.uz)}" for w in words]
    lines += ["", "Suhbatda ishlatgan so'zlaringiz ✅ bilan belgilanadi."]
    return "\n".join(lines)


def opening_text(mode: str, message: str, first_question: str) -> str:
    return f"{MODE_ICONS[mode]} {fmt(message)}\n\n{question(first_question)}"


def reply_text(
    reply: ChatReply,
    *,
    transcript: str | None = None,
    seconds: int | None = None,
    used: list[str] | None = None,
    words: Sequence | None = None,
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
        lines += [f"• <s>{esc(fix.wrong)}</s> → <b>{esc(fix.right)}</b>\n   {fmt(fix.note)}" for fix in reply.fixes]
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


# ─────────────── Bilim daraxti (Programming) ───────────────

CHOOSE = {"group": "Bo'limni tanlang:", "topic": "Mavzuni tanlang:", "subsection": "Qismni tanlang:"}
ROOT_NOTE = "Bu qism grammatika progressiga kirmaydi."


def breadcrumb(icon: str, titles: list[str]) -> str:
    """'💻 Programming › Backend › <b>Web and APIs</b>'."""
    *head, last = titles
    return f"{icon} " + " › ".join([*map(esc, head), f"<b>{esc(last)}</b>"])


def knowledge_page(icon: str, titles: list[str], child_kind: str | None, is_root: bool) -> str:
    choose = CHOOSE.get(child_kind or "", "Bu yerda hali mavzu yo'q.")
    note = f"{choose} {ROOT_NOTE}" if is_root else choose
    return f"{breadcrumb(icon, titles)}\n\n{note}"


def explanation_text(names: tuple[str, str, str], ex: Explanation) -> str:
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


# ─────────────── Ovoz ───────────────

def voice_too_long(max_seconds: int) -> str:
    return f"⏱ Ovozli xabar {max_seconds // 60} daqiqadan oshmasin."


VOICE_FAILED = "⚠️ Ovozni matnga o'girib bo'lmadi. Qaytadan yuboring."
VOICE_EMPTY = "🤔 Hech narsa eshitilmadi. Telefonni og'zingizga yaqinroq tutib qayta yuboring."
SPEAK_FAILED = "⚠️ Ovozni yaratib bo'lmadi. Birozdan keyin qayta urinib ko'ring."


def speak_caption(text: str) -> str:
    return f"🔊 <i>{esc(text)}</i>"[:1000]


# ─────────────── Rejali xabarlar ───────────────

EVENING_EMPTY = (
    "🌙 <b>Bugun hali mashq qilmadingiz.</b>\n\n10 daqiqa ajrating: bir nechta gap yozing "
    "yoki ovozli xabar yuboring."
)
WEEKLY_REVIEW = "📝 <b>Haftalik takrorlash</b>\n\nShu haftadagi xatolaringiz ustida ishlaymiz."


def evening_text(stats, words: Sequence) -> str:
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
    return "\n".join(lines)
