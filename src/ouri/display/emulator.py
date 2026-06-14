from __future__ import annotations

from PIL import Image
from luma.emulator.device import pygame as pygame_device

from ouri.display.protocol import DisplayProtocol


class LumaEmulatorDisplay(DisplayProtocol):
    """Scaled pygame window that mirrors a 128x64 OLED."""

    def __init__(self, width: int = 128, height: int = 64, scale: int = 4) -> None:
        self.width = width
        self.height = height
        # luma scale2x only supports scale=2; use identity for other scales
        transform = "scale2x" if scale == 2 else "identity"
        self._device = pygame_device(
            width=width, height=height, scale=scale, transform=transform
        )

    def show(self, image: Image.Image) -> None:
        if image.mode != "1":
            image = image.convert("1")
        if image.size != (self.width, self.height):
            image = image.resize((self.width, self.height))
        self._device.display(image)

    def close(self) -> None:
        if hasattr(self._device, "_screen") and self._device._screen is not None:
            import pygame

            pygame.quit()
