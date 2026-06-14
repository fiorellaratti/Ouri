from __future__ import annotations

import pygame

from ouri.input.protocol import InputEvent, InputEventType, InputProtocol
from ouri.persona.fsm import STATE_KEYS


class KeyboardMouseInput(InputProtocol):
    """Poll pygame events for keyboard and mouse pet interaction."""

    def __init__(self) -> None:
        if not pygame.get_init():
            pygame.init()

    def poll(self) -> list[InputEvent]:
        events: list[InputEvent] = []

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                events.append(InputEvent(InputEventType.QUIT))
            elif event.type == pygame.KEYDOWN:
                events.extend(self._handle_key(event.key))
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                events.append(InputEvent(InputEventType.PET))

        return events

    def _handle_key(self, key: int) -> list[InputEvent]:
        if key == pygame.K_q:
            return [InputEvent(InputEventType.QUIT)]
        if key == pygame.K_p:
            return [InputEvent(InputEventType.PET)]
        if key == pygame.K_n:
            return [InputEvent(InputEventType.NEXT_FIXTURE)]
        if key == pygame.K_r:
            return [InputEvent(InputEventType.REFRESH)]
        if key == pygame.K_t:
            return [InputEvent(InputEventType.JUMP_TIME)]
        if key == pygame.K_0:
            return [InputEvent(InputEventType.CLEAR_OVERRIDE)]

        name = pygame.key.name(key)
        if name in STATE_KEYS:
            return [
                InputEvent(
                    InputEventType.FORCE_STATE,
                    value=STATE_KEYS[name].value,
                )
            ]
        return []
