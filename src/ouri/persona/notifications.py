from __future__ import annotations

import time
from collections import deque
from typing import Callable

from ouri.wellness.models import WellnessReminder

NOTIFICATION_DURATION_SEC = 5.0


class NotificationQueue:
    """Brief on-screen reminders shown as text cards.

    Supports a single reminder (mood changes) or an auto-advancing sequence
    (the morning briefing). The face shows the rest of the time.
    """

    def __init__(
        self,
        duration_sec: float = NOTIFICATION_DURATION_SEC,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._duration = duration_sec
        self._clock = clock
        self._active: WellnessReminder | None = None
        self._until: float = 0.0
        self._queue: deque[tuple[WellnessReminder, float]] = deque()

    def _activate(self, reminder: WellnessReminder, duration: float) -> None:
        self._active = reminder
        self._until = self._clock() + duration

    def push(self, reminder: WellnessReminder | None, duration: float | None = None) -> None:
        if not reminder or not reminder.text.strip():
            return
        self._queue.clear()
        self._activate(reminder, duration or self._duration)

    def push_sequence(
        self, reminders: list[WellnessReminder | None], seconds_each: float
    ) -> None:
        valid = [r for r in reminders if r and r.text.strip()]
        if not valid:
            return
        self._activate(valid[0], seconds_each)
        self._queue = deque((r, seconds_each) for r in valid[1:])

    def current(self) -> WellnessReminder | None:
        if self._active and self._clock() >= self._until:
            if self._queue:
                reminder, duration = self._queue.popleft()
                self._activate(reminder, duration)
            else:
                self._active = None
        if self._active and self._clock() < self._until:
            return self._active
        return None

    def clear(self) -> None:
        self._active = None
        self._until = 0.0
        self._queue.clear()
