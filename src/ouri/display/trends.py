from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from ouri.wellness.trends import TrendDirection

try:
    _HEAD_FONT = ImageFont.load_default(size=9)
    _SMALL_FONT = ImageFont.load_default(size=8)
except TypeError:  # pragma: no cover - very old Pillow fallback
    _HEAD_FONT = ImageFont.load_default()
    _SMALL_FONT = _HEAD_FONT

_CHART_LEFT = 10
_CHART_RIGHT = 104
_CHART_TOP = 24
_CHART_BOTTOM = 56


def _arrow(draw: ImageDraw.ImageDraw, x: int, y: int, direction: TrendDirection) -> None:
    if direction == TrendDirection.UP:
        draw.polygon([(x, y + 5), (x + 5, y + 5), (x + 2, y)], fill=255)
    elif direction == TrendDirection.DOWN:
        draw.polygon([(x, y), (x + 5, y), (x + 2, y + 5)], fill=255)
    else:
        draw.rectangle([x, y + 2, x + 5, y + 3], fill=255)


def render_trend_card(
    width: int,
    height: int,
    title: str,
    series: list[int],
    direction: TrendDirection = TrendDirection.FLAT,
    frame: int = 0,
) -> Image.Image:
    """A 7-day sparkline of one metric with a direction arrow and latest value."""
    image = Image.new("1", (width, height), 0)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle([0, 0, width - 1, height - 1], radius=4, outline=255)

    hw = draw.textlength(title, font=_HEAD_FONT)
    draw.text(((width - hw) / 2, 2), title, font=_HEAD_FONT, fill=255)

    if not series:
        return image

    lo, hi = min(series), max(series)
    span = max(1, hi - lo)
    n = len(series)
    step = (_CHART_RIGHT - _CHART_LEFT) / max(1, n - 1)

    points = []
    for i, value in enumerate(series):
        x = round(_CHART_LEFT + i * step)
        y = round(_CHART_BOTTOM - (value - lo) / span * (_CHART_BOTTOM - _CHART_TOP))
        points.append((x, y))

    if len(points) >= 2:
        draw.line(points, fill=255, width=1, joint="curve")
    for x, y in points:
        draw.point((x, y), fill=255)

    # Emphasize the latest point and show its value + direction.
    lx, ly = points[-1]
    draw.ellipse([lx - 2, ly - 2, lx + 2, ly + 2], fill=255)
    _arrow(draw, width - 16, 4, direction)

    label = str(series[-1])
    lw = draw.textlength(label, font=_SMALL_FONT)
    label_x = min(width - 6 - lw, lx - lw - 4)
    label_y = ly + 4 if ly < (_CHART_TOP + _CHART_BOTTOM) // 2 else ly - 12
    draw.text((label_x, label_y), label, font=_SMALL_FONT, fill=255)

    return image
