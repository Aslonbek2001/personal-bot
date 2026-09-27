"""content/ ni o'qiydi: fanlar (subject.toml), grammatika va bilim daraxti.

Tartib `NN_` prefiksi bilan belgilanadi, prefiks hech qayerda ko'rsatilmaydi.
Tugun ID si — prefikslarsiz yo'lning 8 belgili xeshi: fayllarni qayta tartiblash ID ni o'zgartirmaydi.
"""

import hashlib
import re
import tomllib
from pathlib import Path

from bot.config import settings
from bot.content.models import GrammarBlock, Library, Node, Subject

PREFIX = re.compile(r"^(\d+)_")
SPECIAL = {"prompt.md", "_index.md"}


def strip_prefix(name: str) -> str:
    return PREFIX.sub("", name)


def sort_key(path: Path) -> tuple[int, int, str]:
    """Prefiksli fayllar raqam bo'yicha birinchi, prefikssizlar nom bo'yicha keyin."""
    match = PREFIX.match(path.name)
    return (0, int(match.group(1)), path.name) if match else (1, 0, path.name)


def node_id(key: str) -> str:
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:8]


def title_from_name(name: str) -> str:
    """'01_web_and_apis' -> 'Web And Apis'."""
    words = strip_prefix(Path(name).stem).replace("_", " ").replace("-", " ").split()
    return " ".join(words).title() if words else name


def parse_md(path: Path) -> tuple[str | None, list[str]]:
    """Birinchi '# ' qator — sarlavha, '- ' qatorlar — elementlar."""
    title: str | None = None
    items: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("# ") and title is None:
            title = line[2:].strip()
        elif line.startswith("- "):
            items.append(line[2:].strip())
    return title, items


class ContentError(ValueError):
    pass


class _Builder:
    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.keys: dict[str, str] = {}

    def add(self, key: str, kind: str, title: str, parent: Node | None) -> Node:
        ident = node_id(key)
        if ident in self.nodes:
            raise ContentError(f"Takroriy tugun ID {ident}: '{key}' va '{self.keys[ident]}'")
        node = Node(id=ident, kind=kind, title=title, parent=parent)
        self.nodes[ident], self.keys[ident] = node, key
        if parent is not None:
            parent.children.append(node)
        return node

    def tree(self, folder: Path, key: str, parent: Node) -> None:
        for path in sorted(folder.iterdir(), key=sort_key):
            name = strip_prefix(path.stem if path.is_file() else path.name)
            child_key = f"{key}/{name}"
            if path.is_dir():
                index = path / "_index.md"
                title = (parse_md(index)[0] if index.exists() else None) or title_from_name(path.name)
                self.tree(path, child_key, self.add(child_key, "group", title, parent))
            elif path.suffix == ".md" and path.name not in SPECIAL:
                title, subsections = parse_md(path)
                topic = self.add(child_key, "topic", title or title_from_name(path.name), parent)
                for subsection in subsections:
                    self.add(f"{child_key}#{subsection}", "subsection", subsection, topic)


def read_grammar(folder: Path) -> tuple[GrammarBlock, ...]:
    if not folder.is_dir():
        return ()
    blocks = []
    for path in sorted(folder.glob("*.md"), key=sort_key):
        title, topics = parse_md(path)
        blocks.append(GrammarBlock(title=title or title_from_name(path.name), topics=tuple(topics)))
    return tuple(blocks)


def load(root: Path) -> Library:
    builder = _Builder()
    subjects: list[Subject] = []
    for folder in sorted(p for p in root.iterdir() if (p / "subject.toml").is_file()):
        meta = tomllib.loads((folder / "subject.toml").read_text(encoding="utf-8"))
        key = folder.name
        title = meta.get("title", title_from_name(key))
        node = builder.add(key, "subject", title, None)
        kind = meta.get("type", "knowledge")
        if kind == "knowledge":
            builder.tree(folder, key, node)
        prompt = folder / "prompt.md"
        subjects.append(Subject(
            key=key,
            title=title,
            icon=meta.get("icon", ""),
            type=kind,
            order=int(meta.get("order", 100)),
            code=meta.get("code", ""),
            scheduled=bool(meta.get("scheduled", False)),
            level=meta.get("default_level", ""),
            writing=meta.get("writing", "work"),
            tts=bool(meta.get("tts", False)),
            prompt=prompt.read_text(encoding="utf-8") if prompt.exists() else "",
            root=node,
            grammar=read_grammar(folder / "grammar") if kind == "language" else (),
        ))
    subjects.sort(key=lambda s: (s.order, s.key))
    codes = [s.code for s in subjects if s.type == "language"]
    if not all(codes) or len(codes) != len(set(codes)):
        raise ContentError(f"Har bir til subject.toml da noyob code ga ega bo'lishi kerak: {codes}")
    style = root / "shared" / "style.md"
    return Library(
        profile=(root / "profile.md").read_text(encoding="utf-8"),
        style=style.read_text(encoding="utf-8") if style.exists() else "",
        subjects=subjects,
        nodes=builder.nodes,
    )


# ─────────────── Xotiradagi nusxa ───────────────

_library: Library | None = None


def current() -> Library:
    """Ishga tushganda bir marta yuklanadi; /reload bilan yangilanadi."""
    global _library
    if _library is None:
        _library = load(settings.content_dir)
    return _library


def reload() -> Library:
    """Yangi nusxani yuklaydi; xato bo'lsa eski nusxa saqlanib qoladi."""
    global _library
    _library = load(settings.content_dir)
    return _library
