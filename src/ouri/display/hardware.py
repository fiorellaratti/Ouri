from __future__ import annotations

from PIL import Image

from ouri.display.protocol import DisplayProtocol


class LumaHardwareDisplay(DisplayProtocol):
    """SSD1306 OLED on Raspberry Pi via I2C. Requires luma.oled + enabled I2C."""

    def __init__(
        self,
        width: int = 128,
        height: int = 64,
        i2c_port: int = 1,
        i2c_address: int = 0x3C,
    ) -> None:
        self.width = width
        self.height = height
        try:
            from luma.core.interface.serial import i2c
            from luma.oled.device import ssd1306

            serial = i2c(port=i2c_port, address=i2c_address)
            self._device = ssd1306(serial, width=width, height=height)
        except Exception as exc:  # pragma: no cover - hardware only
            raise RuntimeError(
                "Hardware display unavailable. Run with OURI_DISPLAY=emulator on your Mac, "
                "or enable I2C and connect an SSD1306 on the Pi."
            ) from exc

    def show(self, image: Image.Image) -> None:
        if image.mode != "1":
            image = image.convert("1")
        if image.size != (self.width, self.height):
            image = image.resize((self.width, self.height))
        self._device.display(image)

    def close(self) -> None:
        if hasattr(self._device, "cleanup"):
            self._device.cleanup()
