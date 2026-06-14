from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

# Match the emulator/hardware frame rate so the pulse lands at the real BPM.
HEARTBEAT_FPS = 12

try:
    _LABEL_FONT = ImageFont.load_default(size=9)
    _BPM_FONT = ImageFont.load_default(size=26)
    _UNIT_FONT = ImageFont.load_default(size=10)
except TypeError:  # pragma: no cover - very old Pillow fallback
    _LABEL_FONT = ImageFont.load_default()
    _BPM_FONT = _LABEL_FONT
    _UNIT_FONT = _LABEL_FONT


def _heart(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: float) -> None:
    """Draw a filled heart centered horizontally on cx, top near cy."""
    lobe_r = size * 0.30
    lobe_y = cy
    left = (cx - lobe_r, lobe_y)
    right = (cx + lobe_r, lobe_y)
    for c in (left, right):
        draw.ellipse(
            [c[0] - lobe_r, c[1] - lobe_r, c[0] + lobe_r, c[1] + lobe_r], fill=255
        )
    half_w = lobe_r * 2
    draw.polygon(
        [
            (cx - half_w, lobe_y),
            (cx + half_w, lobe_y),
            (cx, cy + size * 0.78),
        ],
        fill=255,
    )


def _pulse_scale(frame: int, bpm: int) -> float:
    """A quick 'thump' once per beat, easing back down."""
    fpb = max(4, round(HEARTBEAT_FPS * 60 / max(30, min(200, bpm))))
    phase = frame % fpb
    if phase == 0:
        return 1.28
    if phase == 1:
        return 1.16
    if phase == 2:
        return 1.06
    return 1.0


def render_heartrate(width: int, height: int, bpm: int, frame: int = 0) -> Image.Image:
    """A card with a heart pulsing at the user's current BPM, plus the number."""
    image = Image.new("1", (width, height), 0)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle([0, 0, width - 1, height - 1], radius=4, outline=255)

    label = "HEART RATE"
    lw = draw.textlength(label, font=_LABEL_FONT)
    draw.text(((width - lw) / 2, 3), label, font=_LABEL_FONT, fill=255)

    base = 13
    size = base * _pulse_scale(frame, bpm)
    _heart(draw, 34, 28, size)

    bpm_text = str(bpm)
    bw = draw.textlength(bpm_text, font=_BPM_FONT)
    draw.text((84 - bw / 2, 22), bpm_text, font=_BPM_FONT, fill=255)
    uw = draw.textlength("BPM", font=_UNIT_FONT)
    draw.text((84 - uw / 2, 48), "BPM", font=_UNIT_FONT, fill=255)

    return image
