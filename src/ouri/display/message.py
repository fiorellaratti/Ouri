from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from ouri.wellness.models import WellnessReminder

# Larger, legible fonts (Pillow >= 10.1 supports a sized built-in TrueType font).
try:
    _BODY_FONT = ImageFont.load_default(size=13)
    _HEAD_FONT = ImageFont.load_default(size=9)
except TypeError:  # pragma: no cover - very old Pillow fallback
    _BODY_FONT = ImageFont.load_default()
    _HEAD_FONT = _BODY_FONT

_CATEGORY_LABELS = {
    "sleep": "SLEEP",
    "readiness": "READINESS",
    "activity": "MOVE",
    "stress": "BREATHE",
    "sick": "REST",
    "happy": "NICE",
    "pet": "HELLO",
    "sync": "SYNC",
    "bedtime": "BEDTIME",
    "proud": "PROUD",
    "recovering": "RECOVER",
    "greeting": "GOOD MORNING",
    "sleep_recap": "LAST NIGHT",
    "trend_chart": "THIS WEEK",
    "heartrate": "HEART RATE",
}

_REPLACEMENTS = {
    "\u2014": "-",  # em dash
    "\u2013": "-",  # en dash
    "\u2019": "'",  # curly apostrophe
    "\u2018": "'",
    "\u201c": '"',
    "\u201d": '"',
}


def _sanitize(text: str) -> str:
    for bad, good in _REPLACEMENTS.items():
        text = text.replace(bad, good)
    return text


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _line_height(font) -> int:
    bbox = font.getbbox("Ag")
    return (bbox[3] - bbox[1]) + 3


def render_message(
    width: int,
    height: int,
    reminder: WellnessReminder,
    frame: int = 0,
) -> Image.Image:
    """Full-screen, word-wrapped reminder card — shown instead of the face."""
    image = Image.new("1", (width, height), 0)
    draw = ImageDraw.Draw(image)

    # Card border
    draw.rounded_rectangle([0, 0, width - 1, height - 1], radius=4, outline=255)

    # Category header
    label = _CATEGORY_LABELS.get(reminder.category, reminder.category.upper())
    header_w = draw.textlength(label, font=_HEAD_FONT)
    draw.text(((width - header_w) / 2, 3), label, font=_HEAD_FONT, fill=255)
    underline_w = min(width - 16, int(header_w) + 8)
    ux0 = (width - underline_w) // 2
    draw.line([(ux0, 15), (ux0 + underline_w, 15)], fill=255, width=1)

    # Body text, wrapped and centered in the remaining space
    text = _sanitize(reminder.text)
    margin = 8
    lines = _wrap(draw, text, _BODY_FONT, width - margin * 2)
    lh = _line_height(_BODY_FONT)

    top = 18
    block_h = len(lines) * lh
    start_y = top + max(0, (height - top - block_h) // 2)

    for i, line in enumerate(lines):
        lw = draw.textlength(line, font=_BODY_FONT)
        draw.text(((width - lw) / 2, start_y + i * lh), line, font=_BODY_FONT, fill=255)

    return image
