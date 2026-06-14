from __future__ import annotations

import math

from PIL import Image, ImageDraw

from ouri.display.tiny_font import draw_tiny_text
from ouri.wellness.models import RobotState

# Frame rate the heartbeat cadence is computed against (matches default app fps).
HEARTBEAT_FPS = 12

# Big, glossy "desk-bot" eyes carry most of the emotion (Cozmo/Vector inspired).
EYE_W = 20
EYE_H = 22
EYE_R = 7
LEFT_EYE_X = 43
RIGHT_EYE_X = 85

# States calm enough to show the ambient "alive" heartbeat.
_HEARTBEAT_STATES = {
    RobotState.IDLE,
    RobotState.HAPPY,
    RobotState.RECOVERING,
    RobotState.SLEEPY_NIGHT,
    RobotState.PROUD,
}

_BLUSH_STATES = {RobotState.HAPPY, RobotState.PET_REACTION, RobotState.PROUD}


def _layout(bob: int) -> dict[str, int]:
    """Vertical placement of the centered face."""
    return {
        "bob": bob,
        "eye_cy": 32 + bob,
        "mouth_y": 50 + bob,
        "antenna_y": 9 + bob,
    }


def _bob_offset(state: RobotState, frame: int) -> int:
    if state == RobotState.MOTIVATE:
        return int(2 * math.sin(frame * 0.35))
    if state in (RobotState.HAPPY, RobotState.PET_REACTION, RobotState.PROUD):
        return int(1 * math.sin(frame * 0.25))
    if state == RobotState.TIRED:
        return 1 if (frame // 30) % 2 else 0
    if state in (RobotState.SLEEPY_NIGHT, RobotState.RECOVERING, RobotState.ASLEEP):
        return int(1 * math.sin(frame * 0.07))
    return 0


# --------------------------------------------------------------------------- #
# Antenna
# --------------------------------------------------------------------------- #
def _draw_antenna(draw: ImageDraw.ImageDraw, layout: dict[str, int]) -> None:
    by = layout["antenna_y"]
    for ax in (54, 74):
        draw.line([(ax, by + 2), (ax, by + 6)], fill=255, width=1)
        draw.ellipse([ax - 2, by - 2, ax + 2, by + 2], outline=255, fill=255)


# --------------------------------------------------------------------------- #
# Eyes
# --------------------------------------------------------------------------- #
def _eye_box(cx: int, cy: int, w: int = EYE_W, h: int = EYE_H) -> list[int]:
    return [cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2]


def _draw_open_eye(draw: ImageDraw.ImageDraw, cx: int, cy: int, look: int = 0) -> None:
    box = _eye_box(cx + look, cy)
    draw.rounded_rectangle(box, radius=EYE_R, fill=255)
    # glossy highlight (carved out) — top-left big, plus a tiny shine dot
    draw.ellipse([box[0] + 3, box[1] + 3, box[0] + 8, box[1] + 9], fill=0)
    draw.ellipse([box[0] + 10, box[1] + 4, box[0] + 12, box[1] + 6], fill=0)


def _draw_blink_eye(draw: ImageDraw.ImageDraw, cx: int, cy: int) -> None:
    draw.rounded_rectangle([cx - EYE_W // 2, cy - 2, cx + EYE_W // 2, cy + 2], radius=2, fill=255)


def _draw_curve_eye(
    draw: ImageDraw.ImageDraw, cx: int, cy: int, amp: int, width: int
) -> None:
    """An upward dome (∩) — used for happy / content closed eyes."""
    pts = []
    for deg in range(0, 181, 15):
        a = math.radians(deg)
        x = cx - (EYE_W // 2) * math.cos(a)
        y = cy + 3 - amp * math.sin(a)
        pts.append((x, y))
    draw.line(pts, fill=255, width=width, joint="curve")


def _draw_tired_eye(draw: ImageDraw.ImageDraw, cx: int, cy: int, frac: float) -> None:
    """Heavy lid: only the lower fraction of the eye shows."""
    box = _eye_box(cx, cy)
    draw.rounded_rectangle(box, radius=EYE_R, fill=255)
    cover_bottom = box[1] + int(EYE_H * frac)
    draw.rectangle([box[0] - 1, box[1] - 1, box[2] + 1, cover_bottom], fill=0)
    draw.line([(box[0] + 1, cover_bottom), (box[2] - 1, cover_bottom)], fill=255, width=1)


def _draw_stressed_eye(draw: ImageDraw.ImageDraw, cx: int, cy: int, left: bool) -> None:
    box = [cx - EYE_W // 2, cy - 2, cx + EYE_W // 2, cy + 6]
    draw.rounded_rectangle(box, radius=4, fill=255)
    # worried brow slanting toward the center
    if left:
        draw.line([(box[0], cy - 8), (box[2], cy - 4)], fill=255, width=2)
    else:
        draw.line([(box[0], cy - 4), (box[2], cy - 8)], fill=255, width=2)


def _draw_x_eye(draw: ImageDraw.ImageDraw, cx: int, cy: int) -> None:
    r = 7
    draw.line([(cx - r, cy - r), (cx + r, cy + r)], fill=255, width=2)
    draw.line([(cx + r, cy - r), (cx - r, cy + r)], fill=255, width=2)


def _eye_look(frame: int) -> int:
    """Occasional gentle saccade for lifelike open eyes."""
    cycle = frame % 200
    if 70 <= cycle < 86:
        return -2
    if 110 <= cycle < 126:
        return 2
    return 0


def _draw_closed_eye(draw: ImageDraw.ImageDraw, cx: int, cy: int) -> None:
    """Peaceful sleeping eye — a gentle downward arc."""
    pts = []
    for deg in range(0, 181, 30):
        a = math.radians(deg)
        x = cx - 6 * math.cos(a)
        y = cy + 2 * math.sin(a)
        pts.append((x, y))
    draw.line(pts, fill=255, width=2, joint="curve")


def _draw_eyes(draw: ImageDraw.ImageDraw, style: str, frame: int, layout: dict[str, int]) -> None:
    cy = layout["eye_cy"]
    lx, rx = LEFT_EYE_X, RIGHT_EYE_X

    if style == "closed":
        _draw_closed_eye(draw, lx, cy)
        _draw_closed_eye(draw, rx, cy)
        return

    if style == "open":
        if frame % 70 < 3:  # blink
            _draw_blink_eye(draw, lx, cy)
            _draw_blink_eye(draw, rx, cy)
        else:
            look = _eye_look(frame)
            _draw_open_eye(draw, lx, cy, look)
            _draw_open_eye(draw, rx, cy, look)
        return

    if style == "happy":
        _draw_curve_eye(draw, lx, cy, amp=9, width=3)
        _draw_curve_eye(draw, rx, cy, amp=9, width=3)
        return

    if style == "soft":
        _draw_curve_eye(draw, lx, cy, amp=6, width=2)
        _draw_curve_eye(draw, rx, cy, amp=6, width=2)
        return

    if style == "tired":
        _draw_tired_eye(draw, lx, cy, frac=0.5)
        _draw_tired_eye(draw, rx, cy, frac=0.5)
        return

    if style == "sleepy":
        droop = 0.66 + (0.06 if frame % 80 > 40 else 0)
        _draw_tired_eye(draw, lx, cy, frac=droop)
        _draw_tired_eye(draw, rx, cy, frac=droop)
        return

    if style == "stressed":
        _draw_stressed_eye(draw, lx, cy, left=True)
        _draw_stressed_eye(draw, rx, cy, left=False)
        return

    if style == "sick":
        _draw_x_eye(draw, lx, cy)
        _draw_x_eye(draw, rx, cy)
        return

    _draw_open_eye(draw, lx, cy)
    _draw_open_eye(draw, rx, cy)


def _draw_blush(draw: ImageDraw.ImageDraw, layout: dict[str, int]) -> None:
    cy = layout["eye_cy"] + 9
    for cx in (30, 98):
        draw.ellipse([cx - 3, cy - 2, cx + 3, cy + 2], outline=255)
        draw.point((cx, cy), fill=255)


# --------------------------------------------------------------------------- #
# Mouth — kept small and soft so the eyes lead
# --------------------------------------------------------------------------- #
def _draw_arc_mouth(draw: ImageDraw.ImageDraw, cx: int, cy: int, smile: int) -> None:
    """smile > 0 curves up (happy), < 0 curves down (sad), 0 is flat."""
    pts = []
    for dx in range(-6, 7, 2):
        t = dx / 6.0
        y = cy - smile * (1 - t * t)
        pts.append((cx + dx, y))
    draw.line(pts, fill=255, width=1, joint="curve")


def _draw_mouth(draw: ImageDraw.ImageDraw, style: str, frame: int, layout: dict[str, int]) -> None:
    cx, my = 64, layout["mouth_y"]

    if style == "smile":
        _draw_arc_mouth(draw, cx, my, smile=3)
        return
    if style == "pet":
        _draw_arc_mouth(draw, cx, my, smile=4)
        return
    if style == "motivate":
        _draw_arc_mouth(draw, cx, my + int(math.sin(frame * 0.5)), smile=3)
        return
    if style == "frown":
        _draw_arc_mouth(draw, cx, my + 2, smile=-3)
        return
    if style == "yawn":
        phase = frame % 60
        if phase < 12:
            r = 2 + phase // 4
            draw.ellipse([cx - 4, my - r, cx + 4, my + r], outline=255)
        else:
            _draw_arc_mouth(draw, cx, my, smile=0)
        return
    if style == "wavy":
        pts = [(cx - 6 + i, my + (1 if i % 2 == 0 else -1)) for i in range(13)]
        draw.line(pts, fill=255, width=1, joint="curve")
        return

    _draw_arc_mouth(draw, cx, my, smile=0)  # flat


# --------------------------------------------------------------------------- #
# Decorative extras
# --------------------------------------------------------------------------- #
def _draw_heart(draw: ImageDraw.ImageDraw, hx: int, hy: int) -> None:
    rows = [" # # ", "#####", " ### ", "  #  "]
    for row_i, row in enumerate(rows):
        for col_i, ch in enumerate(row):
            if ch == "#":
                draw.point((hx + col_i, hy + row_i), fill=255)


def _draw_moon(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int = 6) -> None:
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    off = r - 2
    draw.ellipse([cx - r + off, cy - r, cx + r + off, cy + r], fill=0)


def _draw_star(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int = 2) -> None:
    draw.line([(cx - size, cy), (cx + size, cy)], fill=255, width=1)
    draw.line([(cx, cy - size), (cx, cy + size)], fill=255, width=1)
    draw.point((cx - size + 1, cy - size + 1), fill=255)


def _draw_breathing_ring(
    draw: ImageDraw.ImageDraw, cx: int, cy: int, frame: int, period: float
) -> None:
    phase = (math.sin(frame * period) + 1) / 2
    r = int(3 + phase * 5)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=255)


def _draw_extras(
    draw: ImageDraw.ImageDraw,
    state: RobotState,
    frame: int,
    layout: dict[str, int],
) -> None:
    bob = layout["bob"]

    if state in _BLUSH_STATES:
        _draw_blush(draw, layout)

    if state == RobotState.SICK:
        tx, ty = 110, 14 + bob
        draw.rounded_rectangle([tx, ty, tx + 3, ty + 10], radius=1, outline=255)
        draw.ellipse([tx - 1, ty + 9, tx + 4, ty + 14], outline=255)
        if frame % 24 < 12:
            draw.line([(tx + 1, ty + 3), (tx + 1, ty + 9)], fill=255, width=1)

    if state == RobotState.MOTIVATE:
        for i in range(3):
            bx = 8 + i * 6
            by = 50 - int(2 * abs(math.sin((frame + i * 5) * 0.35)))
            draw.rectangle([bx, by, bx + 2, by + 2], fill=255)

    if state == RobotState.PET_REACTION and frame % 28 < 20:
        _draw_heart(draw, 110, 28 + bob)

    if state == RobotState.TIRED and frame % 50 > 32:
        draw_tiny_text(draw, 102, 8 + bob, "zz")

    if state == RobotState.SLEEPY_NIGHT:
        _draw_moon(draw, 114, 14 + bob)
        drift = (frame // 8) % 6
        draw_tiny_text(draw, 100, 30 - drift + bob, "z")

    if state == RobotState.PROUD:
        for i, (sx, sy) in enumerate(((12, 12), (114, 12), (16, 34), (112, 34))):
            if (frame + i * 7) % 28 < 16:
                _draw_star(draw, sx, sy + bob)

    if state == RobotState.STRESSED:
        _draw_breathing_ring(draw, 112, 30 + bob, frame, 0.18)
        sy = 12 + (frame // 4) % 6
        draw.point((24, sy + bob), fill=255)
        draw.point((24, sy + 1 + bob), fill=255)

    if state == RobotState.RECOVERING:
        _draw_breathing_ring(draw, 112, 30 + bob, frame, 0.08)

    if state == RobotState.ASLEEP:
        # Minimal drifting "z" — keep the night screen mostly dark (OLED-friendly).
        cycle = (frame // 12) % 4
        if cycle < 3:
            draw_tiny_text(draw, 74 + cycle * 4, 18 - cycle * 3 + bob, "z")


def _styles_for_state(state: RobotState, frame: int) -> tuple[str, str]:
    if state == RobotState.TIRED:
        return "tired", "yawn" if frame % 60 < 12 else "flat"
    if state == RobotState.MOTIVATE:
        return "open", "motivate"
    if state == RobotState.SICK:
        return "sick", "frown"
    if state == RobotState.HAPPY:
        return "happy", "smile"
    if state == RobotState.PET_REACTION:
        return "happy", "pet"
    if state == RobotState.SLEEPY_NIGHT:
        return "sleepy", "flat"
    if state == RobotState.PROUD:
        return "happy", "smile"
    if state == RobotState.STRESSED:
        return "stressed", "wavy"
    if state == RobotState.RECOVERING:
        return "soft", "smile"
    if state == RobotState.ASLEEP:
        return "closed", "flat"
    return "open", "flat"


def _draw_heartbeat(draw: ImageDraw.ImageDraw, frame: int, bpm: int, layout: dict[str, int]) -> None:
    """Tiny heart between the antennae pulsing at the user's resting heart rate."""
    bpm = max(30, min(180, bpm))
    frames_per_beat = max(4, round(HEARTBEAT_FPS * 60 / bpm))
    phase = frame % frames_per_beat
    hx, hy = 62, max(0, layout["antenna_y"] - 5)
    if phase < 2:
        _draw_heart(draw, hx, hy)
    elif phase < 4:
        draw.point((hx + 1, hy + 1), fill=255)
        draw.point((hx + 2, hy + 1), fill=255)


def render_face(
    width: int,
    height: int,
    state: RobotState,
    frame: int,
    heartbeat_bpm: int | None = None,
) -> Image.Image:
    """Render the expression only. Reminders are shown separately as text cards.

    heartbeat_bpm: optional resting heart rate that drives an ambient pulse.
    """
    image = Image.new("1", (width, height), 0)
    draw = ImageDraw.Draw(image)

    bob = _bob_offset(state, frame)
    layout = _layout(bob)

    _draw_antenna(draw, layout)
    eye_style, mouth_style = _styles_for_state(state, frame)
    _draw_eyes(draw, eye_style, frame, layout)
    _draw_mouth(draw, mouth_style, frame, layout)
    _draw_extras(draw, state, frame, layout)

    if heartbeat_bpm and state in _HEARTBEAT_STATES:
        _draw_heartbeat(draw, frame, heartbeat_bpm, layout)

    return image
