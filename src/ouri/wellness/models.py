from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class StressSummary(str, Enum):
    RESTORED = "restored"
    NORMAL = "normal"
    STRESSFUL = "stressful"
    UNKNOWN = "unknown"


class TimeOfDay(str, Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"


class WellnessSnapshot(BaseModel):
    """Normalized daily wellness view for persona decisions."""

    day: date = Field(default_factory=date.today)
    captured_at: datetime = Field(default_factory=datetime.now)

    sleep_score: int | None = None
    readiness_score: int | None = None
    activity_score: int | None = None
    stress_summary: StressSummary = StressSummary.UNKNOWN

    temperature_deviation: float | None = None
    body_temperature_contributor: int | None = None
    steps: int | None = None
    meters_to_target: int | None = None

    # Extended Oura signals (optional — fixtures/live may omit them)
    resting_heart_rate: int | None = None  # bpm, drives the "alive" heartbeat pulse
    resilience_level: str | None = None  # limited|adequate|solid|strong|exceptional
    vo2_max: float | None = None
    workout_intensity: str | None = None  # easy|moderate|hard
    minutes_to_bedtime: int | None = None  # minutes until optimal bedtime (neg = past)
    sleep_time_recommendation: str | None = None

    # Sleep stage breakdown in minutes (from the detailed `sleep` endpoint)
    sleep_deep_min: int | None = None
    sleep_rem_min: int | None = None
    sleep_light_min: int | None = None
    total_sleep_min: int | None = None

    rest_mode_active: bool = False
    symptom_tags: list[str] = Field(default_factory=list)

    time_of_day: TimeOfDay = TimeOfDay.MORNING
    data_stale: bool = False

    @classmethod
    def time_of_day_from_hour(cls, hour: int) -> TimeOfDay:
        if hour < 11:
            return TimeOfDay.MORNING
        if hour < 17:
            return TimeOfDay.AFTERNOON
        return TimeOfDay.EVENING

    @property
    def has_sleep_stages(self) -> bool:
        return None not in (self.sleep_deep_min, self.sleep_rem_min, self.sleep_light_min)


class RobotState(str, Enum):
    IDLE = "idle"
    TIRED = "tired"
    MOTIVATE = "motivate"
    SICK = "sick"
    HAPPY = "happy"
    PET_REACTION = "pet_reaction"
    SLEEPY_NIGHT = "sleepy_night"
    PROUD = "proud"
    STRESSED = "stressed"
    RECOVERING = "recovering"
    ASLEEP = "asleep"


class WellnessReminder(BaseModel):
    text: str
    category: Literal[
        "sleep",
        "readiness",
        "activity",
        "stress",
        "sick",
        "happy",
        "pet",
        "sync",
        "bedtime",
        "proud",
        "recovering",
        "greeting",
        "sleep_recap",
        "trend_chart",
    ] = "sleep"


class PersonaDecision(BaseModel):
    state: RobotState
    reminder: WellnessReminder | None = None
    priority_reason: str = ""
