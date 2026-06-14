from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Callable

from ouri.persona.day_state import DayState
from ouri.wellness.models import TimeOfDay, WellnessReminder, WellnessSnapshot
from ouri.wellness.trends import TrendSummary, headline_reminder


class Clock:
    """Wall clock with an adjustable offset, for dev time-jumping."""

    def __init__(self) -> None:
        self.offset = timedelta(0)

    def now(self) -> datetime:
        return datetime.now() + self.offset

    def advance(self, **kwargs) -> None:
        self.offset += timedelta(**kwargs)


@dataclass
class SchedulerOutput:
    asleep: bool
    time_of_day: TimeOfDay
    should_refresh: bool = False
    cards: list[WellnessReminder] = field(default_factory=list)
    briefing: list[WellnessReminder] | None = None


def _parse_hhmm(value: str) -> time:
    hh, mm = value.split(":")
    return time(int(hh), int(mm))


def _in_window(now: time, start: time, end: time) -> bool:
    if start <= end:
        return start <= now < end
    # wraps past midnight (e.g. 22:30 -> 06:30)
    return now >= start or now < end


class Scheduler:
    """Drives the daily arc: quiet hours, morning briefing, scheduled nudges."""

    def __init__(
        self,
        schedule: dict,
        day_state: DayState | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._cfg = schedule
        self._day = day_state if day_state is not None else DayState()
        self._now = clock or datetime.now
        self._last_refresh: datetime | None = None

    def tick(
        self,
        snapshot: WellnessSnapshot | None,
        trends: TrendSummary | None = None,
    ) -> SchedulerOutput:
        now = self._now()
        today = now.date().isoformat()
        tod = WellnessSnapshot.time_of_day_from_hour(now.hour)
        asleep = self._in_quiet_hours(now)
        out = SchedulerOutput(asleep=asleep, time_of_day=tod)

        if self._last_refresh is None:
            self._last_refresh = now
        elif (now - self._last_refresh) >= timedelta(minutes=self._cfg["refresh_minutes"]):
            out.should_refresh = True
            self._last_refresh = now

        if asleep:
            return out

        if self._morning_due(now, today):
            briefing = self._build_briefing(snapshot, trends)
            if briefing:
                out.briefing = briefing
                self._day.mark("briefing", today)

        out.cards = self._due_beats(now, today, snapshot)
        return out

    # -- quiet hours / windows ------------------------------------------- #
    def _in_quiet_hours(self, now: datetime) -> bool:
        q = self._cfg["quiet_hours"]
        return _in_window(now.time(), _parse_hhmm(q["start"]), _parse_hhmm(q["end"]))

    def _morning_due(self, now: datetime, today: str) -> bool:
        if self._day.is_done("briefing", today):
            return False
        start, end = self._cfg["morning_window"]
        return _in_window(now.time(), _parse_hhmm(start), _parse_hhmm(end))

    # -- card builders --------------------------------------------------- #
    def _build_briefing(
        self,
        snapshot: WellnessSnapshot | None,
        trends: TrendSummary | None = None,
    ) -> list[WellnessReminder]:
        cards: list[WellnessReminder] = [
            WellnessReminder(text="Hi! Ready for the day?", category="greeting")
        ]
        if snapshot is None:
            return cards
        if snapshot.sleep_score is not None:
            cards.append(
                WellnessReminder(text=f"Sleep score {snapshot.sleep_score}", category="sleep_recap")
            )
        if trends is not None and trends.has_data:
            cards.append(WellnessReminder(text="Sleep this week", category="trend_chart"))
        if snapshot.readiness_score is not None:
            cards.append(
                WellnessReminder(
                    text=f"Readiness {snapshot.readiness_score}", category="readiness"
                )
            )
        if snapshot.activity_score is not None:
            cards.append(
                WellnessReminder(text=f"Activity {snapshot.activity_score}", category="activity")
            )
        if trends is not None:
            reaction = headline_reminder(trends)
            if reaction is not None:
                cards.append(reaction)
        return cards

    def _due_beats(
        self, now: datetime, today: str, snapshot: WellnessSnapshot | None
    ) -> list[WellnessReminder]:
        if snapshot is None:
            return []
        beats = self._cfg.get("beats", {})
        cards: list[WellnessReminder] = []

        bedtime = beats.get("bedtime_nudge")
        if bedtime and not self._day.is_done("bedtime_nudge", today):
            mins = snapshot.minutes_to_bedtime
            if mins is not None and 0 <= mins <= bedtime["near_optimal_bedtime_min"]:
                cards.append(
                    WellnessReminder(text=f"~{mins} min to optimal bedtime", category="bedtime")
                )
                self._day.mark("bedtime_nudge", today)

        return cards
