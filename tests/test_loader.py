from pathlib import Path

import pytest

from bot.content.loader import ContentError, load, node_id, sort_key, strip_prefix, title_from_name
from tests.conftest import ROOT


@pytest.fixture(scope="module")
def library():
    return load(ROOT / "content")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_content(root: Path) -> Path:
    write(root / "profile.md", "# About me\n")
    write(root / "lang" / "subject.toml", 'title = "Lang"\ntype = "language"\ncode = "xx"\norder = 2\n')
    write(root / "lang" / "grammar" / "02_second.md", "# Second\n- c\n")
    write(root / "lang" / "grammar" / "01_first.md", "# First\n- a\n- b\n")
    write(root / "know" / "subject.toml", 'title = "Know"\nicon = "K"\norder = 1\n')
    write(root / "know" / "prompt.md", "# Role\n")
    write(root / "know" / "10_later" / "01_x.md", "# X\n- one\n")
    write(root / "know" / "02_early" / "_index.md", "# Early Things\n")
    write(root / "know" / "02_early" / "01_y.md", "- no title\n")
    write(root / "know" / "plain_folder" / "z.md", "# Z\n")
    return root


def test_counts_match_converted_data(library):
    programming = library.subject("programming")
    groups = [n for n in library.walk(programming.root) if n.kind == "group"
              and any(c.kind == "topic" for c in n.children)]
    assert len(library.grammar_topics()) == 32
    assert len(library.default_language.grammar) == 5
    assert len(groups) == 6
    assert programming.root.count("topic") == 47
    assert programming.root.count("subsection") == 188


def test_subjects_sorted_by_order(library):
    assert [s.key for s in library.subjects] == ["english", "russian", "programming"]
    assert [s.code for s in library.languages] == ["en", "ru"]
    russian = library.subject("russian")
    assert (russian.scheduled, russian.level, russian.writing, russian.tts) == (False, "A2", "daily", False)
    assert len(library.grammar_topics(russian)) >= 24
    assert library.default_language.key == "english"
    assert library.language_by_code("en").key == "english"
    assert library.subject("english").label == "🇬🇧 English"


def test_grammar_keeps_exact_topic_strings(library):
    topics = library.grammar_topics()
    assert topics[0].startswith("Present Simple vs Present Continuous - describing")
    assert topics[-1] == "Writing documentation: README and API docs - imperative mood and clear instructions"


def test_prefix_helpers():
    assert strip_prefix("01_web_and_apis") == "web_and_apis"
    assert strip_prefix("frontend") == "frontend"
    assert title_from_name("01_react") == "React"
    assert title_from_name("02_web_and_apis.md") == "Web And Apis"
    names = ["b", "10_x", "02_y", "a"]
    assert [p.name for p in sorted(map(Path, names), key=sort_key)] == ["02_y", "10_x", "a", "b"]


def test_ordering_titles_and_prefix_stripping(tmp_path):
    lib = load(make_content(tmp_path))
    assert [s.key for s in lib.subjects] == ["know", "lang"]
    know = lib.subject("know").root
    assert [c.title for c in know.children] == ["Early Things", "Later", "Plain Folder"]
    early = know.children[0]
    assert early.children[0].title == "Y"  # sarlavhasiz fayl: nomidan
    assert [c.title for c in know.children[1].children[0].children] == ["one"]
    assert all("0" not in n.title for n in lib.walk(know))
    assert [b.title for b in lib.subject("lang").grammar] == ["First", "Second"]
    assert lib.grammar_topics() == ["a", "b", "c"]
    assert lib.subject("lang").root.children == []


def test_ids_are_stable_when_files_are_renumbered(tmp_path):
    first = load(make_content(tmp_path / "a"))
    root = make_content(tmp_path / "b")
    (root / "know" / "10_later").rename(root / "know" / "01_later")
    second = load(root)
    assert set(first.nodes) == set(second.nodes)
    assert node_id("know/later/x#one") in second.nodes
    assert [c.title for c in second.subject("know").root.children][:2] == ["Later", "Early Things"]


def test_ids_are_unique_and_short(library):
    ids = [n.id for s in library.subjects for n in library.walk(s.root)]
    assert len(ids) == len(set(ids)) == len(library.nodes)
    assert all(len(i) == 8 for i in ids)


def test_language_needs_unique_code(tmp_path):
    root = make_content(tmp_path)
    write(root / "lang2" / "subject.toml", 'type = "language"\ncode = "xx"\n')
    with pytest.raises(ContentError):
        load(root)


def test_collision_is_rejected(tmp_path, monkeypatch):
    root = make_content(tmp_path)
    monkeypatch.setattr("bot.content.loader.node_id", lambda key: "same")
    with pytest.raises(ContentError):
        load(root)


def test_new_topic_file_appears_without_code(tmp_path):
    root = make_content(tmp_path)
    write(root / "know" / "frontend" / "01_react" / "01_hooks.md", "# Hooks\n- useState\n")
    lib = load(root)
    hooks = lib.nodes[node_id("know/frontend/react/hooks")]
    assert [n.title for n in hooks.path()] == ["Know", "Frontend", "React", "Hooks"]
    assert lib.subject_of(hooks).key == "know"
