"""One-time converter: data/topics.md + data/tech.md -> content/, then a verification report.

    uv run python tools/convert_content.py            # generate and verify
    uv run python tools/convert_content.py --check    # verify only

Prompt files (profile.md, shared/style.md, */prompt.md) are split from data/context.md by hand;
this script checks that every line of context.md ends up in exactly one of them.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CONTENT = ROOT / "content"
NUMBER = re.compile(r"^\d+[.)]\s*")

# tech.md section -> (direction folder, direction title)
DIRECTIONS = {
    "Web and APIs": ("backend", "Backend"),
    "Clean code and design": ("backend", "Backend"),
    "Backend architecture": ("backend", "Backend"),
    "ML foundations": ("ml", "ML"),
    "RAG": ("rag", "RAG"),
    "LLM applications": ("rag", "RAG"),
}
PROMPT_FILES = ["profile.md", "shared/style.md", "english/prompt.md", "programming/prompt.md"]


def slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")


def read_topics() -> list[tuple[str, list[str]]]:
    blocks: list[tuple[str, list[str]]] = []
    for line in (DATA / "topics.md").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("## "):
            blocks.append((line[3:].split(":", 1)[-1].strip(), []))
        elif line and not line.startswith("#"):
            blocks[-1][1].append(NUMBER.sub("", line))
    return blocks


def read_tech() -> list[tuple[str, list[tuple[str, list[str]]]]]:
    sections: list[tuple[str, list[tuple[str, list[str]]]]] = []
    for line in (DATA / "tech.md").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("## "):
            sections[-1][1].append((line[3:].strip(), []))
        elif line.startswith("# "):
            sections.append((line[2:].strip(), []))
        elif line.startswith("- "):
            sections[-1][1][-1][1].append(line[2:].strip())
    return sections


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def generate() -> None:
    for n, (title, topics) in enumerate(read_topics(), start=1):
        body = "\n".join(f"- {topic}" for topic in topics)
        write(CONTENT / "english" / "grammar" / f"{n:02d}_{slug(title)}.md", f"# {title}\n\n{body}\n")

    counters: dict[str, int] = {}
    for section, topics in read_tech():
        folder, direction_title = DIRECTIONS[section]
        direction = CONTENT / "programming" / folder
        write(direction / "_index.md", f"# {direction_title}\n")
        counters[folder] = counters.get(folder, 0) + 1
        group = direction / f"{counters[folder]:02d}_{slug(section)}"
        write(group / "_index.md", f"# {section}\n")
        for n, (topic, subsections) in enumerate(topics, start=1):
            body = "\n".join(f"- {name}" for name in subsections)
            write(group / f"{n:02d}_{slug(topic)}.md", f"# {topic}\n\n{body}\n")


def read_generated() -> tuple[list[str], list[tuple[str, list[tuple[str, list[str]]]]]]:
    """Reads content/ back the simple way: sorted files, '# title' and '- item' lines."""
    def parse(path: Path) -> tuple[str, list[str]]:
        lines = path.read_text(encoding="utf-8").splitlines()
        return lines[0][2:].strip(), [x[2:].strip() for x in lines if x.startswith("- ")]

    topics = [t for f in sorted((CONTENT / "english" / "grammar").glob("*.md")) for t in parse(f)[1]]
    tree = []
    for direction in sorted(p for p in (CONTENT / "programming").iterdir() if p.is_dir()):
        for group in sorted(p for p in direction.iterdir() if p.is_dir()):
            title = parse(group / "_index.md")[0]
            tree.append((title, [parse(f) for f in sorted(group.glob("[0-9]*.md"))]))
    return topics, tree


def verify() -> bool:
    source_topics, source_tree = [t for _, ts in read_topics() for t in ts], read_tech()
    topics, tree = read_generated()
    same_tree = source_tree == tree
    rows = [
        ("grammar topics", len(source_topics), len(topics), source_topics == topics),
        ("tech sections", len(source_tree), len(tree), [s for s, _ in source_tree] == [s for s, _ in tree]),
        ("tech topics", sum(len(ts) for _, ts in source_tree), sum(len(ts) for _, ts in tree), same_tree),
        ("tech subsections", sum(len(s) for _, ts in source_tree for _, s in ts),
         sum(len(s) for _, ts in tree for _, s in ts), same_tree),
    ]
    ok = True
    print(f"{'':18}{'data/':>8}{'content/':>10}  same order and text")
    for name, before, after, same in rows:
        ok &= before == after and same
        print(f"{name:18}{before:>8}{after:>10}  {'yes' if same else 'NO'}")

    ok &= check_prompts()
    print("\nRESULT:", "OK" if ok else "MISMATCH")
    return ok


def check_prompts() -> bool:
    """Every line of context.md must appear in exactly one prompt file (or be listed as reworded)."""
    files = {name: (CONTENT / name).read_text(encoding="utf-8") for name in PROMPT_FILES}
    missing, repeated = [], []
    for raw in (DATA / "context.md").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        hits = [name for name, text in files.items() if line in text]
        if not hits:
            missing.append(line)
        elif len(hits) > 1:
            repeated.append((line, hits))
    print("\ncontext.md lines not found verbatim (reworded or merged, review by hand):")
    for line in missing:
        print(f"  - {line}")
    for line, hits in repeated:
        print(f"  DUPLICATE in {hits}: {line}")
    return not repeated


if __name__ == "__main__":
    if "--check" not in sys.argv:
        generate()
    sys.exit(0 if verify() else 1)
