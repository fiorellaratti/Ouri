from __future__ import annotations

from PIL import ImageDraw

# 3x5 pixel glyphs (each char is list of 5 rows, bits per row)
_GLYPHS: dict[str, list[int]] = {
    " ": [0, 0, 0, 0, 0],
    "-": [0, 0, 7, 0, 0],
    ".": [0, 0, 0, 0, 2],
    "!": [2, 2, 2, 0, 2],
    "?": [6, 0, 2, 4, 2],
    "0": [6, 9, 9, 9, 6],
    "1": [2, 6, 2, 2, 7],
    "2": [6, 1, 6, 8, 7],
    "3": [7, 1, 6, 1, 6],
    "4": [9, 9, 7, 1, 1],
    "5": [7, 8, 6, 1, 6],
    "6": [6, 8, 6, 9, 6],
    "7": [7, 1, 2, 4, 4],
    "8": [6, 9, 6, 9, 6],
    "9": [6, 9, 7, 1, 6],
    "a": [0, 0, 6, 9, 7],
    "b": [8, 8, 6, 9, 6],
    "c": [0, 0, 6, 8, 6],
    "d": [1, 1, 7, 9, 7],
    "e": [0, 0, 6, 7, 6],
    "f": [3, 4, 7, 4, 4],
    "g": [0, 0, 7, 9, 6],
    "h": [8, 8, 6, 9, 9],
    "i": [2, 0, 6, 2, 7],
    "l": [6, 2, 2, 2, 7],
    "m": [0, 0, 10, 15, 9],
    "n": [0, 0, 6, 9, 9],
    "o": [0, 0, 6, 9, 6],
    "p": [0, 0, 6, 9, 6],
    "r": [0, 0, 6, 8, 8],
    "s": [0, 0, 7, 6, 7],
    "t": [4, 6, 7, 4, 4],
    "u": [0, 0, 9, 9, 7],
    "v": [0, 0, 9, 9, 6],
    "w": [0, 0, 9, 15, 9],
    "x": [0, 0, 9, 6, 9],
    "y": [0, 0, 9, 7, 1],
    "z": [0, 0, 7, 2, 7],
}


def draw_tiny_text(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    text: str,
    *,
    max_width: int = 120,
) -> None:
    """Draw 3x5 pixel text (4px wide per char incl. spacing)."""
    cx = x
    for ch in text.lower():
        if cx > x + max_width:
            break
        glyph = _GLYPHS.get(ch, _GLYPHS["?"])
        for row, bits in enumerate(glyph):
            for col in range(3):
                if bits & (1 << (2 - col)):
                    draw.point((cx + col, y + row), fill=255)
        cx += 4
