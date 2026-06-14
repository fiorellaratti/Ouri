from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image


class DisplayProtocol(ABC):
    width: int
    height: int

    @abstractmethod
    def show(self, image: Image.Image) -> None:
        """Render a PIL image to the display."""

    @abstractmethod
    def close(self) -> None:
        """Release display resources."""
