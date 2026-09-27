"""Claude javoblarining Pydantic tuzilmalari (messages.parse)."""

from pydantic import BaseModel, Field

MARKUP_RULE = (
    "Plain text with light markup: **double asterisks** for key words and grammar forms, "
    "*single asterisks* for whole example sentences in the language I am learning, `backticks` for technical names. "
    "Use markup only where it helps, not on every line. "
    "Use line breaks: one idea per line, and put each example or step on its own line "
    "starting with '• ' or '1.'. Put an Uzbek note on its own line. "
    "No Markdown headings or tables."
)

# ─────────────── Javob tuzilmalari ───────────────

class Word(BaseModel):
    word: str
    uz: str = Field(description="Uzbek translation")
    example: str = Field(description="A short example sentence, as 'Lesson structure' describes")


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
        "**double asterisks**. null if there are no mistakes or my message is not in the language I am practicing."
    )
    fixes: list[Fix] = Field(
        description="Each real grammar or word-choice mistake in my message. Empty if there are none."
    )
    improved: str | None = Field(
        description="A more natural version of my message, as a native speaker would say it "
        "(see 'Correcting my mistakes'). null if my message is already natural, is only a short "
        "greeting or phrase, or is not in the language I am practicing. Never just add filler words."
    )
    tip: str | None = Field(
        description="A short reminder of the rule behind my mistakes, 1-2 lines in Uzbek, "
        f"with examples in the language I am practicing. null if there is no rule worth reminding. {MARKUP_RULE}"
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
