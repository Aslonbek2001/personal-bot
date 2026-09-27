"""Offline smoke test: haqiqiy Dispatcher va router'lar, soxta Telegram sessiyasi, Claude/Whisper mock."""

import io
import itertools
import shutil
from datetime import datetime

import pytest
from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.methods import AnswerCallbackQuery, EditMessageText, SendMessage, SendPhoto, TelegramMethod
from aiogram.types import CallbackQuery, Chat, InlineKeyboardMarkup, Message, Update, User, Voice

from bot.ai import client as ai
from bot.ai.schemas import ChatReply, Explanation, Fix, Lesson, Opening, Word
from bot.config import settings
from bot.content import loader
from bot.handlers import build_router
from bot.handlers.fsm import SQLiteStorage
from bot.ui import texts
from bot.voice import stt
from tests.conftest import OWNER_ID, ROOT

STRANGER_ID = 222
GROUP_ID = -100500


class FakeSession(BaseSession):
    """Har bir Bot API chaqiruvini yozib boradi va soxta javob qaytaradi."""

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[TelegramMethod] = []
        self.ids = itertools.count(1000)
        self.markups: dict[int, InlineKeyboardMarkup] = {}

    async def make_request(self, bot, method, timeout=None):
        self.calls.append(method)
        if isinstance(method, (SendMessage, SendPhoto, EditMessageText)):
            message_id = method.message_id if isinstance(method, EditMessageText) else next(self.ids)
            if isinstance(method.reply_markup, InlineKeyboardMarkup):
                self.markups[message_id] = method.reply_markup
            return Message(
                message_id=message_id,
                date=datetime.now(),
                chat=Chat(id=method.chat_id or OWNER_ID, type="private"),
                text=getattr(method, "text", None),
            )
        return True

    async def close(self) -> None:
        pass

    async def stream_content(self, *args, **kwargs):
        yield b""


class Harness:
    def __init__(self, dp: Dispatcher, bot: Bot, session: FakeSession) -> None:
        self.dp, self.bot, self.session = dp, bot, session
        self.updates = itertools.count(1)

    def user(self, user_id: int) -> User:
        return User(id=user_id, is_bot=False, first_name="U")

    def take(self) -> list[TelegramMethod]:
        calls, self.session.calls = self.session.calls, []
        return calls

    async def send(self, text: str | None = None, user_id: int = OWNER_ID, chat_id: int | None = None,
                   voice: Voice | None = None) -> list[TelegramMethod]:
        chat_id = chat_id or user_id
        chat = Chat(id=chat_id, type="private" if chat_id > 0 else "group")
        message = Message(message_id=next(self.session.ids), date=datetime.now(), chat=chat,
                          from_user=self.user(user_id), text=text, voice=voice)
        await self.dp.feed_update(self.bot, Update(update_id=next(self.updates), message=message))
        return self.take()

    async def press(self, label: str, user_id: int = OWNER_ID) -> list[TelegramMethod]:
        """Oxirgi ko'rsatilgan klaviaturalardan matni `label` bilan boshlanadigan tugmani bosadi."""
        for message_id, markup in reversed(self.session.markups.items()):
            for button in (b for row in markup.inline_keyboard for b in row):
                if button.text.startswith(label):
                    return await self.callback(button.callback_data, message_id, user_id)
        raise AssertionError(f"Tugma topilmadi: {label}")

    async def callback(self, data: str, message_id: int = 1, user_id: int = OWNER_ID) -> list[TelegramMethod]:
        message = Message(message_id=message_id, date=datetime.now(), chat=Chat(id=user_id, type="private"),
                          from_user=User(id=123456, is_bot=True, first_name="Ustoz"), text="menu")
        query = CallbackQuery(id=str(next(self.updates)), from_user=self.user(user_id), chat_instance="x",
                              message=message, data=data)
        await self.dp.feed_update(self.bot, Update(update_id=next(self.updates), callback_query=query))
        calls = self.take()
        if user_id == OWNER_ID:  # Telegram: har bir bosish aynan bir marta javob oladi
            assert sum(isinstance(c, AnswerCallbackQuery) for c in calls) == 1, calls
        return calls


def texts_of(calls: list[TelegramMethod]) -> str:
    return "\n".join(getattr(c, "text", None) or getattr(c, "caption", None) or "" for c in calls)


def answers(calls: list[TelegramMethod]) -> list[str | None]:
    return [c.text for c in calls if isinstance(c, AnswerCallbackQuery)]


REPLY = ChatReply(corrected="I **have** fixed it", fixes=[Fix(wrong="has", right="have", note="I bilan have")],
                  improved="I fixed the bug yesterday.", tip=None, reply="Great job", question="What was the cause?")
EXPLANATION = Explanation(what="w", why="y", how="A -> B", where="api", example="e", mistakes=["m"], question="q?")


@pytest.fixture
def mocks(monkeypatch):
    calls: dict[str, list] = {"lesson": [], "practice": [], "explain": [], "tech": [], "stt": []}

    async def make_lesson(topic):
        calls["lesson"].append(topic)
        words = [Word(word=f"to deploy{n}", uz="joylash", example="We deploy.") for n in range(20)]
        return Lesson(title="Present Simple", summary="s", examples=["a", "b", "c"], grammar="**rule**",
                      story_title="Story", story="text", words=words)

    async def opening(mode, topic, words, mistakes):
        return Opening(message="Hi", question="How was your day?")

    async def practice_reply(text, history, mode, topic, words, mistakes, seconds=None):
        calls["practice"].append((text, mode, seconds, len(history)))
        return REPLY

    async def explain_subsection(subject, section, topic, subsection):
        calls["explain"].append((subject.key, section, topic, subsection))
        return EXPLANATION

    async def tech_reply(subject, text, history, scope, seconds=None):
        calls["tech"].append((subject.key, text, scope))
        return REPLY

    async def transcribe(audio, prompt=""):
        calls["stt"].append(prompt)
        return "I has fixed the bug"

    for name, fake in [("make_lesson", make_lesson), ("opening", opening), ("practice_reply", practice_reply),
                       ("explain_subsection", explain_subsection), ("tech_reply", tech_reply)]:
        monkeypatch.setattr(ai, name, fake)
    monkeypatch.setattr(stt, "transcribe", transcribe)
    return calls


_router = build_router()


@pytest.fixture
async def harness(fresh_db, tmp_path, monkeypatch):
    content = tmp_path / "content"
    shutil.copytree(ROOT / "content", content)
    monkeypatch.setattr(settings, "content_dir", content)
    loader.reload()
    session = FakeSession()
    bot = Bot("123456:TEST", session=session)
    monkeypatch.setattr(bot, "download", _download)
    dp = Dispatcher(storage=SQLiteStorage())
    dp.include_router(_router)
    yield Harness(dp, bot, session)
    dp.sub_routers.remove(_router)
    _router._parent_router = None
    monkeypatch.undo()
    loader.reload()


async def _download(*args, **kwargs):
    return io.BytesIO(b"OggS")


async def test_full_flow(harness, mocks):
    h = harness
    calls = await h.send("/start")
    assert "Ustoz" in texts_of(calls) and "English teacher" not in texts_of(calls)

    calls = await h.press("🇬🇧 English")
    assert isinstance(calls[-1], EditMessageText) and "📖 Bugun:" in calls[-1].text

    calls = await h.press(texts.BTN_TODAY)
    assert any(isinstance(c, SendPhoto) for c in calls)
    assert "1. Grammar" in texts_of(calls) and "20 words of the day" in texts_of(calls)
    await h.press(texts.BTN_TODAY)
    assert len(mocks["lesson"]) == 1  # kunlik kesh

    calls = await h.press(texts.BTN_START_CHAT)
    assert "How was your day?" in texts_of(calls)
    calls = await h.send("I has fixed the bug")
    assert "To'g'rilangan" in texts_of(calls) and mocks["practice"][-1][:3] == ("I has fixed the bug", "chat", None)

    calls = await h.press(texts.BTN_DONE)
    assert answers(calls) == [texts.DONE_OK] and "Mavzu yakunlandi" in texts_of(calls)
    calls = await h.press(texts.BTN_DONE)
    assert answers(calls) == [texts.DONE_ALREADY]
    calls = await h.press(texts.BTN_PROGRESS)
    assert "Grammatika: 1/32" in texts_of(calls)

    calls = await h.send(voice=Voice(file_id="v", file_unique_id="v", duration=6))
    assert "Eshitildi" in texts_of(calls) and mocks["practice"][-1][2] == 6

    await h.send("/start")
    calls = await h.press("💻 Programming")
    assert "💻 <b>Programming</b>" in texts_of(calls)
    await h.press("Backend (")
    calls = await h.press("Backend architecture (")
    assert "Programming › Backend › <b>Backend architecture</b>" in texts_of(calls)
    calls = await h.press("▶️")
    assert "Scalability and reliability" in str(calls[-1].reply_markup)
    await h.press("◀️")
    await h.press(texts.BTN_BACK)
    await h.press("Web and APIs (")
    calls = await h.press("HTTP request lifecycle")
    assert "› <b>HTTP request lifecycle</b>" in texts_of(calls)

    calls = await h.press("DNS resolution")
    assert mocks["explain"][-1] == ("programming", "Web and APIs", "HTTP request lifecycle", "DNS resolution")
    assert "1. What it is" in texts_of(calls)
    await h.send("Why is DNS cached?")
    assert mocks["tech"][-1] == ("programming", "Why is DNS cached?",
                                 ("Web and APIs", "HTTP request lifecycle", "DNS resolution"))
    await h.send(voice=Voice(file_id="v", file_unique_id="v", duration=4))
    assert mocks["stt"][-1] == "HTTP request lifecycle. DNS resolution."

    await h.press("➡️ Keyingi qism: TCP and TLS handshake")
    assert mocks["explain"][-1][3] == "TCP and TLS handshake"

    calls = await h.callback("k:deadbeef:0")
    assert answers(calls) == [texts.LIST_CHANGED] and "Programming" in texts_of(calls)
    calls = await h.callback("tech:sub:0:0:0")
    assert answers(calls) == [texts.STALE]

    calls = await h.press(texts.BTN_HOME)
    assert "asosiy menyu" in texts_of(calls)


async def test_reload_picks_up_new_topic(harness, mocks):
    h = harness
    hooks = settings.content_dir / "programming" / "frontend" / "01_react" / "01_hooks.md"
    hooks.parent.mkdir(parents=True)
    hooks.write_text("# Hooks\n\n- useState\n", encoding="utf-8")
    await h.send("/start")
    calls = await h.press("💻 Programming")
    assert "Frontend" not in str(calls[-1].reply_markup)
    calls = await h.send("/reload")
    assert "Kontent yangilandi" in texts_of(calls)
    await h.send("/start")
    await h.press("💻 Programming")
    await h.press("Frontend (1)")
    await h.press("React (1)")
    await h.press("Hooks")
    await h.press("useState")
    assert mocks["explain"][-1] == ("programming", "React", "Hooks", "useState")


async def test_strangers_and_groups_get_nothing(harness, mocks):
    h = harness
    assert await h.send("/start", user_id=STRANGER_ID) == []
    assert await h.send("hello", user_id=STRANGER_ID) == []
    assert await h.send("/start", chat_id=GROUP_ID) == []
    assert await h.send("hello", chat_id=GROUP_ID) == []
    assert await h.callback("m:home", user_id=STRANGER_ID) == []
    assert mocks["practice"] == [] and mocks["tech"] == []
