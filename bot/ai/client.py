"""Claude bilan ishlash: kunlik dars, suhbat javobi va tech tushuntirish."""

import logging
from typing import TypeVar

from anthropic import AsyncAnthropic
from pydantic import BaseModel, ValidationError

from bot.ai import prompts
from bot.ai.schemas import ChatReply, Explanation, Lesson, Opening
from bot.config import settings
from bot.content import loader
from bot.content.models import Subject

log = logging.getLogger(__name__)

client = AsyncAnthropic(api_key=settings.anthropic_api_key.get_secret_value())

T = TypeVar("T", bound=BaseModel)


class Truncated(Exception):
    pass


async def _request(model: type[T], system: list[dict], messages: list[dict], max_tokens: int) -> T:
    response = await client.messages.parse(
        model=settings.claude_model,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
        output_format=model,
    )
    if response.stop_reason == "max_tokens":
        raise Truncated
    if response.parsed_output is None:
        raise RuntimeError(f"Claude tuzilmali javob qaytarmadi (stop_reason={response.stop_reason})")
    return response.parsed_output


async def _ask(model: type[T], subject: Subject, task: str, messages: list[dict], max_tokens: int) -> T:
    """Javob max_tokens da kesilib, JSON buzilsa, ikki barobar limit bilan bir marta qayta so'raydi."""
    system = prompts.system(loader.current(), subject, task)
    try:
        return await _request(model, system, messages, max_tokens)
    except (Truncated, ValidationError):
        log.warning("%s javobi kesildi (max_tokens=%d), qayta so'ralmoqda", model.__name__, max_tokens)
        return await _request(model, system, messages, max_tokens * 2)


def _language() -> Subject:
    subject = loader.current().language
    if subject is None:
        raise LookupError("content/ da scheduled=true til topilmadi")
    return subject


async def make_lesson(topic: str) -> Lesson:
    messages = [{"role": "user", "content": f"Today's grammar topic: {topic}"}]
    return await _ask(Lesson, _language(), prompts.LESSON_TASK, messages, max_tokens=8000)


async def opening(mode: str, topic: str, words: list[str], mistakes: list[str]) -> Opening:
    task = prompts.mode_task(mode, topic, words, mistakes)
    messages = [{"role": "user", "content": "Let's start. Give me the first question or task."}]
    return await _ask(Opening, _language(), task, messages, max_tokens=2000)


async def practice_reply(
    text: str,
    history: list[dict],
    mode: str,
    topic: str,
    words: list[str],
    mistakes: list[str],
    seconds: int | None = None,
) -> ChatReply:
    task = prompts.mode_task(mode, topic, words, mistakes)
    messages = [*history, prompts.user_message(text, seconds)]
    return await _ask(ChatReply, _language(), task, messages, max_tokens=4000)


async def explain_subsection(subject: Subject, section: str, topic: str, subsection: str) -> Explanation:
    content = f"Section: {section}\nTopic: {topic}\nSubsection: {subsection}"
    messages = [{"role": "user", "content": content}]
    return await _ask(Explanation, subject, prompts.EXPLAIN_TASK, messages, max_tokens=6000)


async def tech_reply(
    subject: Subject,
    text: str,
    history: list[dict],
    scope: tuple[str, str, str] | None,
    seconds: int | None = None,
) -> ChatReply:
    task = prompts.scope_task(*scope) if scope else prompts.TECH_QUESTION_TASK
    messages = [*history, prompts.user_message(text, seconds)]
    return await _ask(ChatReply, subject, task, messages, max_tokens=6000)
