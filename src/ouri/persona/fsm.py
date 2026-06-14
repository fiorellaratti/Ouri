from __future__ import annotations

import time

from ouri.engine.rules import evaluate
from ouri.persona.notifications import NotificationQueue
from ouri.wellness.models import (
    PersonaDecision,
    RobotState,
    TimeOfDay,
    WellnessReminder,
    WellnessSnapshot,
)
from ouri.wellness.trends import TrendSummary

STATE_KEYS: dict[str, RobotState] = {
    "1": RobotState.IDLE,
    "2": RobotState.TIRED,
    "3": RobotState.MOTIVATE,
    "4": RobotState.SICK,
    "5": RobotState.HAPPY,
    "6": RobotState.SLEEPY_NIGHT,
    "7": RobotState.PROUD,
    "8": RobotState.STRESSED,
    "9": RobotState.RECOVERING,
}

PET_DURATION_SEC = 2.0


class PersonaFSM:
    """Drives robot mood from wellness data with optional manual overrides."""

    def __init__(self, snapshot: WellnessSnapshot | None = None) -> None:
        self._snapshot = snapshot
        self._override: RobotState | None = None
        self._pet_until: float = 0.0
        self._frame = 0
        self._decision = PersonaDecision(state=RobotState.IDLE)
        self._notifications = NotificationQueue()
        self._last_state: RobotState | None = None
        self._trends: TrendSummary | None = None

        if snapshot:
            self._apply_snapshot(snapshot, notify=True)

    @property
    def frame(self) -> int:
        return self._frame

    @property
    def decision(self) -> PersonaDecision:
        return self._decision

    @property
    def snapshot(self) -> WellnessSnapshot | None:
        return self._snapshot

    @property
    def trends(self) -> TrendSummary | None:
        return self._trends

    def set_trends(self, trends: TrendSummary | None) -> None:
        self._trends = trends

    def set_snapshot(self, snapshot: WellnessSnapshot) -> None:
        self._apply_snapshot(snapshot, notify=True)

    def update_time_of_day(self, tod: TimeOfDay) -> None:
        """Advance the day phase live without re-pushing mood cards."""
        if self._snapshot and self._snapshot.time_of_day != tod:
            self._snapshot = self._snapshot.model_copy(update={"time_of_day": tod})

    def notify(self, reminder: WellnessReminder | None) -> None:
        """Show a single reminder card (e.g. a scheduled nudge)."""
        self._notifications.push(reminder)

    def push_sequence(
        self, reminders: list[WellnessReminder | None], seconds_each: float
    ) -> None:
        """Play an auto-advancing sequence of cards (e.g. morning briefing)."""
        self._notifications.push_sequence(reminders, seconds_each)

    def _apply_snapshot(self, snapshot: WellnessSnapshot, *, notify: bool) -> None:
        self._snapshot = snapshot
        if self._override is not None or time.time() < self._pet_until:
            return

        decision = evaluate(snapshot)
        state_changed = decision.state != self._decision.state
        self._decision = decision

        if notify and (state_changed or self._last_state is None):
            self._notifications.push(decision.reminder)
        self._last_state = decision.state

    def force_state(self, state: RobotState) -> None:
        self._override = state
        self._notifications.clear()

    def clear_override(self) -> None:
        self._override = None
        if self._snapshot:
            self._apply_snapshot(self._snapshot, notify=True)

    def pet(self) -> None:
        self._pet_until = time.time() + PET_DURATION_SEC
        self._override = None
        self._decision = PersonaDecision(
            state=RobotState.PET_REACTION,
            priority_reason="pet",
        )
        self._notifications.push(self._pet_notification())

    def _pet_notification(self) -> WellnessReminder | None:
        if self._snapshot and (
            self._last_state in (RobotState.SICK, RobotState.TIRED)
            or self._snapshot.rest_mode_active
        ):
            return WellnessReminder(
                text="Pets are nice — rest still helps",
                category="pet",
            )
        return None

    def tick(self) -> RobotState:
        self._frame += 1

        if time.time() < self._pet_until:
            return RobotState.PET_REACTION

        if self._override is not None:
            return self._override

        if self._snapshot:
            decision = evaluate(self._snapshot)
            if decision.state != self._decision.state:
                self._decision = decision
                self._notifications.push(decision.reminder)
                self._last_state = decision.state
            else:
                self._decision = decision

        return self._decision.state

    def current_notification(self) -> WellnessReminder | None:
        return self._notifications.current()
