"""Claude bilan ishlash: kunlik dars, suhbat javobi va tech tushuntirish."""

from typing import TypeVar

from anthropic import AsyncAnthropic
from pydantic import BaseModel, Field

from bot.config import settings
from bot.storage import read_context

client = AsyncAnthropic(api_key=settings.anthropic_api_key.get_secret_value())

T = TypeVar("T", bound=BaseModel)

MARKUP_RULE = (
    "Plain text only. Mark important words with **double asterisks**. "
    "Use line breaks: one idea per line, and put each example or step on its own line "
    "starting with '• ' or '1.'. Put an Uzbek note on its own line. "
    "No Markdown headings, tables or backticks."
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


class ChatReply(BaseModel):
    corrected: str | None = Field(
        description="My message with the mistakes fixed. Mark every changed word with "
        "**double asterisks**. null if there are no mistakes or my message is not in English."
    )
    improved: str | None = Field(
        description="A slightly more natural and professional version of my message. "
        "null if my message is not in English."
    )
    reply: str = Field(description=f"Your answer or response. {MARKUP_RULE}")
    question: str = Field(description="One follow-up question to continue the conversation")
    options: list[str] = Field(
        description="2-3 short possible answers to the follow-up question, written as I would say them"
    )


class Opening(BaseModel):
    message: str = Field(description=f"One or two short lines: greet me and say what we practice today. {MARKUP_RULE}")
    question: str = Field(description="The first question about today's grammar topic")
    options: list[str] = Field(description="2-3 short possible answers, written as I would say them")


class Explanation(BaseModel):
    what: str = Field(description=f"1. What it is. {MARKUP_RULE}")
    why: str = Field(description=f"2. Why it exists. {MARKUP_RULE}")
    how: str = Field(
        description="3. How it works, step by step in the correct order. Add a text flow with "
        f"arrows (A -> B -> C) when the order matters. {MARKUP_RULE}"
    )
    where: str = Field(description=f"4. Where it lives in a real system. {MARKUP_RULE}")
    example: str = Field(description=f"5. A real-world example from a backend, RAG or ML project. {MARKUP_RULE}")
    mistakes: list[str] = Field(description="6. Common mistakes, 2-4 short items")
    question: str = Field(description="One follow-up question")
    options: list[str] = Field(description="2-3 short possible answers, written as I would say them")


# ─────────────── Umumiy chaqiruv ───────────────

async def _ask(model: type[T], task: str, messages: list[dict], max_tokens: int) -> T:
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
    if response.parsed_output is None:
        raise RuntimeError(f"Claude tuzilmali javob qaytarmadi (stop_reason={response.stop_reason})")
    return response.parsed_output


def _user_message(text: str, is_voice: bool) -> dict:
    return {"role": "user", "content": (VOICE_NOTE if is_voice else "") + text}


# ─────────────── Ochiq funksiyalar ───────────────

async def make_lesson(topic: str) -> Lesson:
    task = "Create today's lesson. Follow 'Lesson structure' from the context exactly."
    messages = [{"role": "user", "content": f"Today's grammar topic: {topic}"}]
    return await _ask(Lesson, task, messages, max_tokens=4000)


async def opening_question(topic: str) -> Opening:
    task = f"Mode: chat practice (see 'Chat practice'). Today's grammar topic: {topic}"
    messages = [{"role": "user", "content": "I pressed 'Start chat'. Start the practice with your first question."}]
    return await _ask(Opening, task, messages, max_tokens=600)


async def practice_reply(
    text: str, history: list[dict], topic: str, is_voice: bool = False
) -> ChatReply:
    task = f"Mode: chat practice (see 'Chat practice'). Today's grammar topic: {topic}"
    return await _ask(ChatReply, task, [*history, _user_message(text, is_voice)], max_tokens=1500)


async def explain_subsection(section: str, topic: str, subsection: str) -> Explanation:
    task = "Mode: tech subsection explanation (see 'When I choose a subsection from my tech list')."
    content = f"Section: {section}\nTopic: {topic}\nSubsection: {subsection}"
    return await _ask(Explanation, task, [{"role": "user", "content": content}], max_tokens=3000)


async def tech_reply(
    text: str,
    history: list[dict],
    scope: tuple[str, str, str] | None,
    is_voice: bool = False,
) -> ChatReply:
    if scope:
        section, topic, subsection = scope
        task = (
            "Mode: tech chat inside a subsection. Keep the conversation about it.\n"
            f"Section: {section}\nTopic: {topic}\nSubsection: {subsection}"
        )
    else:
        task = "Mode: tech question in chat (see 'When I ask a tech question in chat')."
    return await _ask(ChatReply, task, [*history, _user_message(text, is_voice)], max_tokens=2500)