"""Kunlik dars uchun rasm-karta (PNG)."""

import io
from datetime import date
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from bot.claude import Lesson

WIDTH = 1080
PADDING = 72
INNER = WIDTH - 2 * PADDING
BULLET_INDENT = 40
LINE_HEIGHT = 1.35

BACKGROUND = (17, 24, 39)
ACCENT = (93, 178, 207)
TITLE = (245, 247, 250)
BODY = (203, 213, 225)
EXAMPLE = (245, 196, 81)
MUTED = (140, 153, 166)
DIVIDER = (36, 49, 64)

FONT_FILES = {
    False: [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",        # Docker (Debian)
        "/System/Library/Fonts/Supplemental/Arial.ttf",           # macOS
    ],
    True: [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ],
}


@lru_cache
def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for path in FONT_FILES[bold]:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size)


def _plain(text: str) -> str:
    """Claude'ning **belgilarini** rasmdan olib tashlaydi."""
    return text.replace("**", "")


def _wrap(text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    """Matnni piksel kengligi bo'yicha qatorlarga bo'ladi."""
    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        current = ""
        for word in paragraph.split():
            candidate = f"{current} {word}".strip()
            if not current or measure.textlength(candidate, font=font) <= width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def render_card(lesson: Lesson, number: int, total: int, day: date) -> bytes:
    """Dars kartasini chizadi va PNG baytlarini qaytaradi."""
    meta_font, title_font = _font(30), _font(60, bold=True)
    body_font, example_font, foot_font = _font(36), _font(36, bold=True), _font(28)

    # (qatorlar, shrift, rang, keyingi bo'shliq, chekinish)
    blocks = [
        (_wrap(f"{day:%d.%m.%Y}  ·  Mavzu {number}/{total}", meta_font, INNER), meta_font, ACCENT, 22, 0),
        (_wrap(_plain(lesson.title), title_font, INNER), title_font, TITLE, 30, 0),
        (_wrap(_plain(lesson.summary), body_font, INNER), body_font, BODY, 40, 0),
    ]
    for example in lesson.examples[:3]:
        lines = _wrap(_plain(example), example_font, INNER - BULLET_INDENT)
        blocks.append((lines, example_font, EXAMPLE, 18, BULLET_INDENT))

    def line_height(font: ImageFont.FreeTypeFont) -> int:
        return int(font.size * LINE_HEIGHT)

    body_height = sum(len(lines) * line_height(font) + gap for lines, font, _, gap, _ in blocks)
    footer_height = 40 + line_height(foot_font)
    height = 14 + PADDING + body_height + footer_height + PADDING

    image = Image.new("RGB", (WIDTH, height), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, WIDTH, 14], fill=ACCENT)

    y = 14 + PADDING
    for lines, font, color, gap, indent in blocks:
        if indent:
            draw.text((PADDING, y), "•", font=font, fill=color)
        for line in lines:
            draw.text((PADDING + indent, y), line, font=font, fill=color)
            y += line_height(font)
        y += gap

    draw.line([PADDING, y + 10, WIDTH - PADDING, y + 10], fill=DIVIDER, width=2)
    draw.text((PADDING, y + 36), "Mini hikoya va 20 ta so'z — pastdagi xabarlarda", font=foot_font, fill=MUTED)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()