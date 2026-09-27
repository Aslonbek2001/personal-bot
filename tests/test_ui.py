from aiogram.types import InlineKeyboardMarkup

from bot.ai import prompts
from bot.content import loader
from bot.ui import keyboards as kb
from bot.ui import texts


def buttons(markup: InlineKeyboardMarkup) -> list:
    return [button for row in markup.inline_keyboard for button in row]


def test_callback_data_fits_for_every_node():
    library = loader.current()
    markups = [kb.main_menu(library.subjects), kb.language_menu(), kb.grammar_menu(), kb.writing_menu(), kb.lesson_end(), kb.reply_nav(speak=True)]
    for subject in library.subjects:
        for node in library.walk(subject.root):
            if node.children:
                markups += [kb.knowledge(node, page) for page in range(kb.page_count(node))]
            if node.kind == "subsection":
                markups.append(kb.reply_nav(topic=node.parent, next_node=node.next_sibling(), speak=True))
    data = [b.callback_data for m in markups for b in buttons(m)]
    assert len(data) > 400
    assert max(len(d.encode("utf-8")) for d in data) < 64


def test_knowledge_pagination_has_at_most_eight_items():
    library = loader.current()
    big = max((n for n in library.nodes.values() if n.children), key=lambda n: len(n.children))
    assert len(big.children) > kb.PAGE_SIZE
    first = buttons(kb.knowledge(big, 0))
    last = buttons(kb.knowledge(big, kb.page_count(big) - 1))
    items = [b for b in first if b.callback_data.startswith("k:") and not b.text.startswith(("◀️", "▶️", "⬅️"))]
    assert len(items) == kb.PAGE_SIZE
    assert "▶️" in [b.text for b in first] and "◀️" not in [b.text for b in first]
    assert "◀️" in [b.text for b in last] and "▶️" not in [b.text for b in last]
    assert [b.text for b in first][-2:] == [texts.BTN_BACK, texts.BTN_HOME]


def test_breadcrumb_text():
    text = texts.knowledge_page("💻", ["Programming", "Backend", "Web & APIs"], "topic", False)
    assert text.startswith("💻 Programming › Backend › <b>Web &amp; APIs</b>")


def test_system_prompt_order_and_cache():
    library = loader.current()
    subject = library.subject("programming")
    system = prompts.system(library, subject, "TASK")
    stable = system[0]["text"]
    assert system[0]["cache_control"] == {"type": "ephemeral"}
    assert system[1] == {"type": "text", "text": "TASK"}
    assert stable.index("# Style") < stable.index("# Technical explanations") < stable.index("# About me")
    assert "Lesson structure" not in stable


def test_texts_never_call_the_bot_an_english_teacher():
    greeting = texts.greeting(5, 20)
    assert "Ustoz" in greeting and "English teacher" not in greeting and "ingliz tili o'qituvchi" not in greeting
