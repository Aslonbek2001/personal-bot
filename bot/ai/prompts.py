"""System prompt va rejim vazifalari.

Tartib: shared/style.md -> fan prompt.md -> profile.md (o'zgarmas, keshlanadi) -> rejim vazifasi.
"""

from bot.content.models import Library, Subject

VOICE_NOTE = (
    "[This message was sent as a voice message in a noisy place and converted to text "
    "automatically. Do not treat speech recognition errors (similar-sounding words, missing "
    "or extra words, punctuation) as my mistakes. Understand what I meant from the context "
    "and correct only my real grammar and word-choice mistakes.]\n\n"
)

MODES = {
    "chat": "Mode: chat practice (see 'Chat practice').",
    "translate": "Mode: translation practice (see 'Translation practice').",
    "task": "Mode: work writing task (see 'Work writing tasks').",
    "standup": "Mode: stand-up speaking practice (see 'Stand-up speaking practice').",
    "review": "Mode: mistakes review (see 'Mistakes review').",
}

LESSON_TASK = "Create today's lesson. Follow 'Lesson structure' from the context exactly."
EXPLAIN_TASK = "Mode: tech subsection explanation (see 'When I choose a subsection from my tech list')."
TECH_QUESTION_TASK = "Mode: tech question in chat (see 'When I ask a tech question in chat')."


def system(library: Library, subject: Subject, task: str) -> list[dict]:
    """O'zgarmas qism bitta keshlanadigan prefiks, rejim vazifasi — alohida blok."""
    stable = "\n\n".join(part.strip() for part in (library.style, subject.prompt, library.profile) if part.strip())
    return [
        {"type": "text", "text": stable, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": task},
    ]


def mode_task(mode: str, topic: str, words: list[str], mistakes: list[str]) -> str:
    lines = [MODES[mode], f"Today's grammar topic: {topic}"]
    if words and mode in ("chat", "task"):
        lines.append("Today's words: " + ", ".join(words))
    if mistakes:
        lines.append("My recent mistakes (wrong -> right):\n" + "\n".join(mistakes))
    return "\n".join(lines)


def scope_task(section: str, topic: str, subsection: str) -> str:
    return (
        "Mode: tech chat inside a subsection. Keep the conversation about it.\n"
        f"Section: {section}\nTopic: {topic}\nSubsection: {subsection}"
    )


def user_message(text: str, seconds: int | None) -> dict:
    if seconds is None:
        return {"role": "user", "content": text}
    note = VOICE_NOTE
    if seconds:
        words = len(text.split())
        note += f"[Voice message: {words} words in {seconds} seconds, {round(words * 60 / seconds)} words per minute.]\n\n"
    return {"role": "user", "content": note + text}
