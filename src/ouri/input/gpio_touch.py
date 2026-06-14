from __future__ import annotations

from ouri.input.protocol import InputEvent, InputEventType, InputProtocol


class GpioTouchInput(InputProtocol):
    """Capacitive touch via TTP223 on Raspberry Pi GPIO. Stub until hardware arrives."""

    def __init__(self, pins: list[int] | None = None) -> None:
        self.pins = pins or [17, 27]
        self._gpio = None
        self._last_states: dict[int, bool] = {}

    def _setup(self) -> None:
        if self._gpio is not None:
            return
        try:
            import RPi.GPIO as GPIO  # type: ignore[import-untyped]

            self._gpio = GPIO
            GPIO.setmode(GPIO.BCM)
            for pin in self.pins:
                GPIO.setup(pin, GPIO.IN)
                self._last_states[pin] = False
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "RPi.GPIO not available. Use OURI_DISPLAY=emulator with keyboard input on your Mac."
            ) from exc

    def poll(self) -> list[InputEvent]:
        self._setup()
        events: list[InputEvent] = []
        assert self._gpio is not None
        GPIO = self._gpio

        for pin in self.pins:
            pressed = GPIO.input(pin) == GPIO.HIGH
            was_pressed = self._last_states.get(pin, False)
            if pressed and not was_pressed:
                events.append(InputEvent(InputEventType.PET, value=str(pin)))
            self._last_states[pin] = pressed

        return events
