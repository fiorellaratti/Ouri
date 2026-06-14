from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class InputEventType(str, Enum):
    PET = "pet"
    NEXT_FIXTURE = "next_fixture"
    FORCE_STATE = "force_state"
    CLEAR_OVERRIDE = "clear_override"
    REFRESH = "refresh"
    JUMP_TIME = "jump_time"
    QUIT = "quit"


@dataclass
class InputEvent:
    type: InputEventType
    value: str | None = None


class InputProtocol(ABC):
    @abstractmethod
    def poll(self) -> list[InputEvent]:
        """Return pending input events since last poll."""
