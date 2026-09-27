"""Bilim daraxti (Programming): istalgan chuqurlik, breadcrumb, sahifalash va qism tushuntirishi."""

import logging

from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.ai import client as ai
from bot.content import loader
from bot.content.models import Node
from bot.handlers.common import Tech, exclusive, send_text, show_nav, thinking
from bot.handlers.menu import show_home
from bot.ui import keyboards as kb
from bot.ui import texts
from bot.ui.callbacks import KnowCb

log = logging.getLogger(__name__)

router = Router(name="knowledge")


async def open_node(callback: CallbackQuery, state: FSMContext, node: Node, page: int) -> None:
    await callback.answer()
    await show_node(callback, state, node, page)


async def show_node(callback: CallbackQuery, state: FSMContext, node: Node, page: int) -> None:
    """Papka, fan yoki mavzu ro'yxatini menyu xabarida ko'rsatadi."""
    library = loader.current()
    subject = library.subject_of(node)
    path = node.path()
    child_kind = node.children[0].kind if node.children else None
    text = texts.knowledge_page(subject.icon, [n.title for n in path], child_kind, node.parent is None)
    await state.set_state(Tech.browse)
    await state.update_data(subject=subject.root.id)
    await show_nav(callback, state, text, kb.knowledge(node, page))


async def list_changed(callback: CallbackQuery, state: FSMContext) -> None:
    """Tugun endi yo'q (content/ o'zgargan): fan ildiziga yoki asosiy menyuga qaytaradi."""
    await callback.answer(texts.LIST_CHANGED)
    root = loader.current().nodes.get((await state.get_data()).get("subject", ""))
    if root is not None:
        await show_node(callback, state, root, 0)
        return
    await show_home(callback, state)


@router.callback_query(KnowCb.filter())
async def on_node(callback: CallbackQuery, callback_data: KnowCb, state: FSMContext) -> None:
    node = loader.current().nodes.get(callback_data.id)
    if node is None:
        await list_changed(callback, state)
        return
    if node.kind != "subsection":
        await open_node(callback, state, node, callback_data.page)
        return
    chat_id = callback.from_user.id
    async with exclusive(chat_id) as free:
        if not free:
            await callback.answer(texts.BUSY)
            return
        await callback.answer()
        await explain(callback.bot, chat_id, state, node)


async def explain(bot: Bot, chat_id: int, state: FSMContext, node: Node) -> None:
    subject = loader.current().subject_of(node)
    names = node.scope_names()
    try:
        async with thinking(bot, chat_id):
            ex = await ai.explain_subsection(subject, *names)
    except Exception:
        log.exception("Tushuntirish yaratilmadi")
        await bot.send_message(chat_id, texts.ERROR)
        return
    await send_text(
        bot, chat_id,
        texts.explanation_text(names, ex),
        kb.reply_nav(topic=node.parent, next_node=node.next_sibling()),
    )
    summary = f"{ex.what}\n{ex.how}\n{ex.where}\n{ex.question}"
    await state.set_state(Tech.chat)
    await state.update_data(
        scope=node.id,
        subject=subject.root.id,
        tech_history=[
            {"role": "user", "content": f"Explain: {names[2]}"},
            {"role": "assistant", "content": summary},
        ],
    )


def scope_node(data: dict) -> Node | None:
    """Joriy suhbat qismi; eski format (indekslar) yoki o'chirilgan qism bo'lsa None."""
    scope = data.get("scope")
    node = loader.current().nodes.get(scope) if isinstance(scope, str) else None
    return node if node is not None and node.kind == "subsection" else None
