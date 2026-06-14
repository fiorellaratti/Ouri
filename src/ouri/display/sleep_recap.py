from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from ouri.wellness.models import WellnessSnapshot

try:
    _HEAD_FONT = ImageFont.load_default(size=9)
    _SMALL_FONT = ImageFont.load_default(size=8)
except TypeError:  # pragma: no cover - very old Pillow fallback
    _HEAD_FONT = ImageFont.load_default()
    _SMALL_FONT = _HEAD_FONT

_BASELINE = 50
_BAR_TOP = 24
_BAR_W = 16
_BARS = (("D", "sleep_deep_min"), ("R", "sleep_rem_min"), ("L", "sleep_light_min"))


def _fmt_duration(minutes: int) -> str:
    return f"{minutes // 60}h {minutes % 60:02d}m"


def _centered(draw: ImageDraw.ImageDraw, cx: int, y: int, text: str, font) -> None:
    w = draw.textlength(text, font=font)
    draw.text((cx - w / 2, y), text, font=font, fill=255)


def render_sleep_recap(
    width: int,
    height: int,
    snapshot: WellnessSnapshot,
    frame: int = 0,
) -> Image.Image:
    """A mini deep/REM/light bar chart for the morning briefing."""
    image = Image.new("1", (width, height), 0)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle([0, 0, width - 1, height - 1], radius=4, outline=255)

    _centered(draw, width // 2, 2, "LAST NIGHT", _HEAD_FONT)

    total = snapshot.total_sleep_min
    if total is None:
        total = sum(
            v for v in (snapshot.sleep_deep_min, snapshot.sleep_rem_min, snapshot.sleep_light_min)
            if v is not None
        )
    _centered(draw, width // 2, 12, _fmt_duration(total), _SMALL_FONT)

    values = [getattr(snapshot, attr) or 0 for _, attr in _BARS]
    peak = max(values + [1])
    centers = [30, 64, 98]
    max_px = _BASELINE - _BAR_TOP

    draw.line([(8, _BASELINE + 1), (width - 8, _BASELINE + 1)], fill=255, width=1)

    for (letter, _), value, cx in zip(_BARS, values, centers):
        bar_h = max(1, round(value / peak * max_px))
        top = _BASELINE - bar_h
        draw.rectangle([cx - _BAR_W // 2, top, cx + _BAR_W // 2, _BASELINE], fill=255)
        # minutes above the bar, letter below the baseline
        _centered(draw, cx, max(14, top - 9), str(value), _SMALL_FONT)
        _centered(draw, cx, _BASELINE + 2, letter, _SMALL_FONT)

    return image
