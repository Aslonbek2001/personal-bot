from bot.ui.format import esc, fmt, plain, question, quote, short, split_text


def test_fmt_escapes_html_and_converts_markup():
    assert fmt("a < b & **bold** and *it* and `x<y>`") == (
        "a &lt; b &amp; <b>bold</b> and <i>it</i> and <code>x&lt;y&gt;</code>"
    )


def test_fmt_keeps_lone_asterisks():
    assert fmt("2 * 3 * 4") == "2 * 3 * 4"
    assert fmt("**not closed") == "**not closed"


def test_quote_removes_blank_lines():
    assert quote("one\n\n two") == "<blockquote>one\n two</blockquote>"


def test_question_strips_markup():
    assert question("What **is** `this`?") == "❓ <b>What is this?</b>"


def test_helpers():
    assert esc("<b>") == "&lt;b&gt;"
    assert plain("**a** *b* `c`") == "a b c"
    assert short("Past Simple - reporting what you did yesterday") == "Past Simple"


def test_split_text_keeps_short_text():
    assert split_text("hello\n\nworld") == ["hello\n\nworld"]


def test_split_text_by_paragraphs():
    parts = split_text("a" * 30 + "\n\n" + "b" * 30, limit=40)
    assert parts == ["a" * 30, "b" * 30]


def test_split_text_cuts_long_paragraph_and_respects_limit():
    text = "x" * 95 + "\n\n" + "y" * 10
    parts = split_text(text, limit=40)
    assert all(len(p) <= 40 for p in parts)
    assert "".join(parts).replace("\n", "") == text.replace("\n", "")


def test_split_text_default_limit():
    parts = split_text("\n\n".join(["z" * 1500] * 6))
    assert all(len(p) <= 4000 for p in parts) and len(parts) == 3
