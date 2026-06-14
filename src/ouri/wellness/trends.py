from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from ouri.wellness.models import WellnessReminder, WellnessSnapshot

# A metric must move at least this many points (recent vs earlier avg) to count.
_DELTA = 3.0
# How many trailing good days before we celebrate a streak.
_STREAK_MIN = 3


class TrendDirection(str, Enum):
    UP = "up"
    DOWN = "down"
    FLAT = "flat"


class TrendSummary(BaseModel):
    sleep_series: list[int] = Field(default_factory=list)
    readiness_series: list[int] = Field(default_factory=list)
    activity_series: list[int] = Field(default_factory=list)

    sleep_dir: TrendDirection = TrendDirection.FLAT
    readiness_dir: TrendDirection = TrendDirection.FLAT
    activity_dir: TrendDirection = TrendDirection.FLAT

    sleep_streak: int = 0
    readiness_streak: int = 0
    activity_streak: int = 0

    @property
    def has_data(self) -> bool:
        return len(self.sleep_series) >= 2


def _series(snapshots: list[WellnessSnapshot], attr: str) -> list[int]:
    return [getattr(s, attr) for s in snapshots if getattr(s, attr) is not None]


def _direction(series: list[int]) -> TrendDirection:
    if len(series) < 2:
        return TrendDirection.FLAT
    half = max(1, len(series) // 2)
    earlier = sum(series[:half]) / half
    recent = sum(series[-half:]) / half
    delta = recent - earlier
    if delta >= _DELTA:
        return TrendDirection.UP
    if delta <= -_DELTA:
        return TrendDirection.DOWN
    return TrendDirection.FLAT


def _streak(series: list[int], good: int) -> int:
    count = 0
    for value in reversed(series):
        if value >= good:
            count += 1
        else:
            break
    return count


def compute_trends(snapshots: list[WellnessSnapshot], thresholds: dict) -> TrendSummary:
    """Summarize the last several days. ``snapshots`` ordered oldest -> newest."""
    scores = thresholds["scores"]
    sleep = _series(snapshots, "sleep_score")
    readiness = _series(snapshots, "readiness_score")
    activity = _series(snapshots, "activity_score")

    return TrendSummary(
        sleep_series=sleep,
        readiness_series=readiness,
        activity_series=activity,
        sleep_dir=_direction(sleep),
        readiness_dir=_direction(readiness),
        activity_dir=_direction(activity),
        sleep_streak=_streak(sleep, scores["sleep"]["good"]),
        readiness_streak=_streak(readiness, scores["readiness"]["good"]),
        activity_streak=_streak(activity, scores["activity"]["good"]),
    )


def headline_reminder(summary: TrendSummary) -> WellnessReminder | None:
    """Pick the single most worthwhile weekly reaction, if any."""
    if summary.sleep_streak >= _STREAK_MIN:
        return WellnessReminder(
            text=f"{summary.sleep_streak}-night good sleep streak!", category="proud"
        )
    if summary.activity_streak >= _STREAK_MIN:
        return WellnessReminder(
            text=f"{summary.activity_streak}-day activity streak!", category="proud"
        )
    if summary.readiness_streak >= _STREAK_MIN:
        return WellnessReminder(
            text=f"{summary.readiness_streak}-day readiness streak!", category="proud"
        )
    if summary.sleep_dir == TrendDirection.DOWN:
        return WellnessReminder(text="Sleep's been dipping — rest up", category="sleep")
    if summary.readiness_dir == TrendDirection.DOWN:
        return WellnessReminder(text="Readiness sliding — go gentle", category="readiness")
    if summary.sleep_dir == TrendDirection.UP:
        return WellnessReminder(text="Sleep trending up this week", category="proud")
    return None
