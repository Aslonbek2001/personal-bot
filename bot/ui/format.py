"""Claude matnini Telegram HTML ga aylantirish va uzun matnni bo'lish."""

import html
import re

MAX_LENGTH = 4000
CODE = re.compile(r"`([^`\n]+)`")
BOLD = re.compile(r"\*\*([^\n]+?)\*\*")
ITALIC = re.compile(r"(?<![\w*])\*(?=\S)([^*\n]+?)(?<=\S)\*(?![\w*])")
BLANK_LINES = re.compile(r"\n\s*\n")
MARKUP = re.compile(r"[*`]")


def esc(text: str) -> str:
    return html.escape(text, quote=False)


def fmt(text: str) -> str:
    """Claude matni: HTML'ni ekranlaydi; `kod`, **qalin**, *kursiv* ni teglarga aylantiradi."""
    text = CODE.sub(r"<code>\1</code>", esc(text))
    text = BOLD.sub(r"<b>\1</b>", text)
    return ITALIC.sub(r"<i>\1</i>", text)


def plain(text: str) -> str:
    """Belgilarsiz matn: **, *, ` olib tashlanadi."""
    return MARKUP.sub("", text)


def quote(text: str) -> str:
    """Blockquote; bo'sh qatorlar olib tashlanadi, aks holda split_text blokni bo'lib yuboradi."""
    return f"<blockquote>{BLANK_LINES.sub(chr(10), fmt(text).strip())}</blockquote>"


def question(text: str) -> str:
    return f"❓ <b>{esc(plain(text))}</b>"


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
