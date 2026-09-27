"""content/ papkasidan o'qilgan ma'lumotlar: fanlar, grammatika bloklari va bilim daraxti."""

from collections.abc import Iterator
from dataclasses import dataclass, field


@dataclass(eq=False)
class Node:
    """Bilim daraxtidagi tugun: subject -> group (papka) -> topic (fayl) -> subsection (qator)."""

    id: str
    kind: str  # subject, group, topic, subsection
    title: str
    parent: "Node | None" = None
    children: list["Node"] = field(default_factory=list)

    def path(self) -> list["Node"]:
        """Ildizdan (fan) shu tugungacha bo'lgan tugunlar."""
        nodes: list[Node] = []
        node: Node | None = self
        while node is not None:
            nodes.append(node)
            node = node.parent
        return nodes[::-1]

    def count(self, kind: str) -> int:
        return sum(1 for node in walk(self) if node.kind == kind)

    def next_sibling(self) -> "Node | None":
        if self.parent is None:
            return None
        siblings = self.parent.children
        index = siblings.index(self)
        return siblings[index + 1] if index + 1 < len(siblings) else None

    def scope_names(self) -> tuple[str, str, str]:
        """Qism uchun (bo'lim, mavzu, qism): bo'lim — mavzu fayli turgan papka nomi."""
        topic = self.parent
        assert topic is not None and topic.parent is not None
        return topic.parent.title, topic.title, self.title


def walk(node: Node) -> Iterator[Node]:
    """Tugunning o'zi va barcha avlodlari, tartib bilan."""
    yield node
    for child in node.children:
        yield from walk(child)


@dataclass(frozen=True)
class GrammarBlock:
    title: str
    topics: tuple[str, ...]


@dataclass
class Subject:
    key: str  # papka nomi: english, programming
    title: str
    icon: str
    type: str  # language, knowledge
    order: int
    prompt: str
    root: Node
    code: str = ""
    scheduled: bool = False
    grammar: tuple[GrammarBlock, ...] = ()

    @property
    def label(self) -> str:
        return f"{self.icon} {self.title}".strip()


@dataclass
class Library:
    profile: str
    style: str
    subjects: list[Subject]
    nodes: dict[str, Node]

    def subject(self, key: str) -> Subject:
        return next(subject for subject in self.subjects if subject.key == key)

    def subject_of(self, node: Node) -> Subject:
        return self.subject_by_root(node.path()[0])

    def subject_by_root(self, root: Node) -> Subject:
        return next(subject for subject in self.subjects if subject.root is root)

    @property
    def language(self) -> Subject | None:
        """Kunlik dars yuboriladigan til (scheduled=true)."""
        return next((s for s in self.subjects if s.type == "language" and s.scheduled), None)

    def grammar_topics(self) -> list[str]:
        language = self.language
        return [topic for block in language.grammar for topic in block.topics] if language else []

    @staticmethod
    def walk(node: Node) -> Iterator[Node]:
        return walk(node)
