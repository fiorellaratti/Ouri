from ouri.config import DisplayMode, settings
from ouri.input.gpio_touch import GpioTouchInput
from ouri.input.keyboard import KeyboardMouseInput
from ouri.input.protocol import InputEvent, InputEventType, InputProtocol


def create_input() -> InputProtocol:
    if settings.ouri_display == DisplayMode.HARDWARE:
        return GpioTouchInput()
    return KeyboardMouseInput()


__all__ = [
    "InputEvent",
    "InputEventType",
    "InputProtocol",
    "KeyboardMouseInput",
    "GpioTouchInput",
    "create_input",
]
