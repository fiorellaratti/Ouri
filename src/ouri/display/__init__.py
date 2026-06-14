from ouri.config import DisplayMode, settings
from ouri.display.emulator import LumaEmulatorDisplay
from ouri.display.face import render_face
from ouri.display.hardware import LumaHardwareDisplay
from ouri.display.message import render_message
from ouri.display.protocol import DisplayProtocol
from ouri.display.heartrate import render_heartrate
from ouri.display.sleep_recap import render_sleep_recap
from ouri.display.trends import render_trend_card


def create_display() -> DisplayProtocol:
    if settings.ouri_display == DisplayMode.HARDWARE:
        return LumaHardwareDisplay(
            width=settings.display_width,
            height=settings.display_height,
        )
    return LumaEmulatorDisplay(
        width=settings.display_width,
        height=settings.display_height,
        scale=settings.display_scale,
    )


__all__ = [
    "DisplayProtocol",
    "LumaEmulatorDisplay",
    "LumaHardwareDisplay",
    "create_display",
    "render_face",
    "render_message",
    "render_sleep_recap",
    "render_trend_card",
    "render_heartrate",
]
