"""Claude bilan ishlash: kunlik dars, suhbat javobi va tech tushuntirish."""

import logging
from typing import TypeVar

from anthropic import AsyncAnthropic
from pydantic import BaseModel, Field, ValidationError

from bot.config import settings
from bot.storage import read_context

log = logging.getLogger(__name__)

client = AsyncAnthropic(api_key=settings.anthropic_api_key.get_secret_value())

T = TypeVar("T", bound=BaseModel)

MARKUP_RULE = (
    "Plain text with light markup: **double asterisks** for key words and grammar forms, "
    "*single asterisks* for whole English example sentences, `backticks` for technical names. "
    "Use markup only where it helps, not on every line. "
    "Use line breaks: one idea per line, and put each example or step on its own line "
    "starting with '• ' or '1.'. Put an Uzbek note on its own line. "
    "No Markdown headings or tables."
)

VOICE_NOTE = (
    "[This message was sent as a voice message in a noisy place and converted to text "
    "automatically. Do not treat speech recognition errors (similar-sounding words, missing "
    "or extra words, punctuation) as my mistakes. Understand what I meant from the context "
    "and correct only my real grammar and word-choice mistakes.]\n\n"
)


# ─────────────── Javob tuzilmalari ───────────────

class Word(BaseModel):
    word: str
    uz: str = Field(description="Uzbek translation")
    example: str = Field(description="A short example sentence from a developer's workday")


class Lesson(BaseModel):
    title: str = Field(description="Short name of the grammar topic, for example 'Past Simple'")
    summary: str = Field(description="The rule in one short sentence, for the image card")
    examples: list[str] = Field(description="Exactly 3 very short example sentences for the image card")
    grammar: str = Field(description=f"Part 1: Grammar. {MARKUP_RULE}")
    story_title: str = Field(description="A short title for the mini story")
    story: str = Field(description=f"Part 2: Mini story. {MARKUP_RULE} Mark today's grammar forms.")
    words: list[Word] = Field(description="Part 3: exactly 20 words of the day")


class Fix(BaseModel):
    wrong: str = Field(description="The wrong words exactly as I wrote them")
    right: str = Field(description="The correct words")
    note: str = Field(description="Why, in one short sentence in Uzbek")


class ChatReply(BaseModel):
    corrected: str | None = Field(
        description="My message with the mistakes fixed. Mark every changed word with "
        "**double asterisks**. null if there are no mistakes or my message is not in English."
    )
    fixes: list[Fix] = Field(
        description="Each real grammar or word-choice mistake in my message. Empty if there are none."
    )
    improved: str | None = Field(
        description="A more natural, professional version of my message, as a native developer "
        "would write it in a work chat. null if my message is already natural, is only a short "
        "greeting or phrase, or is not in English. Never just add filler words."
    )
    tip: str | None = Field(
        description="A short reminder of the rule behind my mistakes, 1-2 lines in Uzbek, "
        f"with English examples. null if there is no rule worth reminding. {MARKUP_RULE}"
    )
    reply: str = Field(
        description="Your answer or response. Do not put the follow-up question "
        f"or the rule reminder here. {MARKUP_RULE}"
    )
    question: str = Field(
        description="The next question or task for me, as the current mode defines it. "
        "I must answer it in my own words."
    )


class Opening(BaseModel):
    message: str = Field(
        description="One or two short lines: greet me and say what we practice today. "
        f"Do not put the question here. {MARKUP_RULE}"
    )
    question: str = Field(
        description="The first question or task for me, as the current mode defines it. "
        "I must answer it in my own words."
    )


class Explanation(BaseModel):
    what: str = Field(description=f"1. What it is. {MARKUP_RULE}")
    why: str = Field(description=f"2. Why it exists. {MARKUP_RULE}")
    how: str = Field(
        description="3. How it works, step by step in the correct order. Add a text flow with "
        f"arrows (A -> B -> C) when the order matters. {MARKUP_RULE}"
    )
    where: str = Field(description=f"4. Where it lives in a real system. {MARKUP_RULE}")
    example: str = Field(description=f"5. A real-world example from a backend, RAG or ML project. {MARKUP_RULE}")
    mistakes: list[str] = Field(description=f"6. Common mistakes, 2-4 short items. {MARKUP_RULE}")
    question: str = Field(description="One open follow-up question that I must answer in my own words")


# ─────────────── Umumiy chaqiruv ───────────────

class Truncated(Exception):
    pass


async def _request(model: type[T], task: str, messages: list[dict], max_tokens: int) -> T:
    response = await client.messages.parse(
        model=settings.claude_model,
        max_tokens=max_tokens,
        system=[
            {"type": "text", "text": read_context(), "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": task},
        ],
        messages=messages,
        output_format=model,
    )
    if response.stop_reason == "max_tokens":
        raise Truncated
    if response.parsed_output is None:
        raise RuntimeError(f"Claude tuzilmali javob qaytarmadi (stop_reason={response.stop_reason})")
    return response.parsed_output


async def _ask(model: type[T], task: str, messages: list[dict], max_tokens: int) -> T:
    """Javob max_tokens da kesilib, JSON buzilsa, ikki barobar limit bilan bir marta qayta so'raydi."""
    try:
        return await _request(model, task, messages, max_tokens)
    except (Truncated, ValidationError):
        log.warning("%s javobi kesildi (max_tokens=%d), qayta so'ralmoqda", model.__name__, max_tokens)
        return await _request(model, task, messages, max_tokens * 2)


def _user_message(text: str, seconds: int | None) -> dict:
    if seconds is None:
        return {"role": "user", "content": text}
    note = VOICE_NOTE
    if seconds:
        words = len(text.split())
        note += f"[Voice message: {words} words in {seconds} seconds, {round(words * 60 / seconds)} words per minute.]\n\n"
    return {"role": "user", "content": note + text}


MODES = {
    "chat": "Mode: chat practice (see 'Chat practice').",
    "translate": "Mode: translation practice (see 'Translation practice').",
    "task": "Mode: work writing task (see 'Work writing tasks').",
    "standup": "Mode: stand-up speaking practice (see 'Stand-up speaking practice').",
    "review": "Mode: mistakes review (see 'Mistakes review').",
}


def _mode_task(mode: str, topic: str, words: list[str], mistakes: list[str]) -> str:
    lines = [MODES[mode], f"Today's grammar topic: {topic}"]
    if words and mode in ("chat", "task"):
        lines.append("Today's words: " + ", ".join(words))
    if mistakes:
        lines.append("My recent mistakes (wrong -> right):\n" + "\n".join(mistakes))
    return "\n".join(lines)


async def make_lesson(topic: str) -> Lesson:
    task = "Create today's lesson. Follow 'Lesson structure' from the context exactly."
    messages = [{"role": "user", "content": f"Today's grammar topic: {topic}"}]
    return await _ask(Lesson, task, messages, max_tokens=8000)


async def opening(mode: str, topic: str, words: list[str], mistakes: list[str]) -> Opening:
    task = _mode_task(mode, topic, words, mistakes)
    messages = [{"role": "user", "content": "Let's start. Give me the first question or task."}]
    return await _ask(Opening, task, messages, max_tokens=2000)


async def practice_reply(
    text: str,
    history: list[dict],
    mode: str,
    topic: str,
    words: list[str],
    mistakes: list[str],
    seconds: int | None = None,
) -> ChatReply:
    task = _mode_task(mode, topic, words, mistakes)
    return await _ask(ChatReply, task, [*history, _user_message(text, seconds)], max_tokens=4000)


async def explain_subsection(section: str, topic: str, subsection: str) -> Explanation:
    task = "Mode: tech subsection explanation (see 'When I choose a subsection from my tech list')."
    content = f"Section: {section}\nTopic: {topic}\nSubsection: {subsection}"
    return await _ask(Explanation, task, [{"role": "user", "content": content}], max_tokens=6000)


async def tech_reply(
    text: str,
    history: list[dict],
    scope: tuple[str, str, str] | None,
    seconds: int | None = None,
) -> ChatReply:
    if scope:
        section, topic, subsection = scope
        task = (
            "Mode: tech chat inside a subsection. Keep the conversation about it.\n"
            f"Section: {section}\nTopic: {topic}\nSubsection: {subsection}"
        )
    else:
        task = "Mode: tech question in chat (see 'When I ask a tech question in chat')."
    return await _ask(ChatReply, task, [*history, _user_message(text, seconds)], max_tokens=6000)
