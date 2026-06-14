from __future__ import annotations

from datetime import datetime

from ouri.config import load_thresholds
from ouri.wellness.models import (
    PersonaDecision,
    RobotState,
    StressSummary,
    TimeOfDay,
    WellnessReminder,
    WellnessSnapshot,
)


def _score(snapshot: WellnessSnapshot, attr: str) -> int | None:
    return getattr(snapshot, attr)


def _is_sick(snapshot: WellnessSnapshot, thresholds: dict) -> tuple[bool, str]:
    temp_cfg = thresholds["temperature"]
    body_temp_cfg = thresholds["body_temperature_contributor"]

    if snapshot.symptom_tags:
        return True, "symptom_tags"

    temp = snapshot.temperature_deviation
    if temp is not None and temp >= temp_cfg["elevated_celsius"]:
        return True, "temperature_elevated"

    contributor = snapshot.body_temperature_contributor
    if contributor is not None and contributor < body_temp_cfg["low"]:
        return True, "body_temperature_low"

    return False, ""


def _is_recovering(snapshot: WellnessSnapshot, sick: bool) -> bool:
    """Rest mode without acute illness signals — calm recovery, not sick."""
    return snapshot.rest_mode_active and not sick


def _is_tired(snapshot: WellnessSnapshot, thresholds: dict) -> bool:
    sleep = _score(snapshot, "sleep_score")
    readiness = _score(snapshot, "readiness_score")
    sleep_poor = thresholds["scores"]["sleep"]["poor"]
    readiness_low = thresholds["scores"]["readiness"]["low"]

    if snapshot.time_of_day == TimeOfDay.MORNING:
        if sleep is not None and sleep < sleep_poor:
            return True
        if readiness is not None and readiness < readiness_low:
            return True
    return False


def _needs_motivation(snapshot: WellnessSnapshot, thresholds: dict) -> bool:
    activity = _score(snapshot, "activity_score")
    activity_low = thresholds["scores"]["activity"]["low"]
    if activity is not None and activity < activity_low:
        return True
    if snapshot.meters_to_target is not None and snapshot.meters_to_target > 500:
        return True
    return False


def _is_stressed(snapshot: WellnessSnapshot) -> bool:
    return snapshot.stress_summary == StressSummary.STRESSFUL


def _is_sleepy_night(snapshot: WellnessSnapshot, thresholds: dict) -> bool:
    if snapshot.time_of_day != TimeOfDay.EVENING:
        return False
    window = thresholds["bedtime"]["window_minutes"]
    mins = snapshot.minutes_to_bedtime
    return mins is not None and mins <= window


def _is_proud(snapshot: WellnessSnapshot, thresholds: dict) -> tuple[bool, str]:
    proud_intensities = thresholds["workout"]["proud_intensities"]
    if snapshot.workout_intensity in proud_intensities:
        return True, "workout"

    proud_levels = thresholds["resilience"]["proud_levels"]
    if snapshot.resilience_level in proud_levels:
        return True, "resilience"

    return False, ""


def _is_happy(snapshot: WellnessSnapshot, thresholds: dict) -> bool:
    scores = thresholds["scores"]
    sleep = _score(snapshot, "sleep_score")
    readiness = _score(snapshot, "readiness_score")
    activity = _score(snapshot, "activity_score")

    if sleep is None or readiness is None or activity is None:
        return False

    return (
        sleep >= scores["sleep"]["good"]
        and readiness >= scores["readiness"]["good"]
        and activity >= scores["activity"]["good"]
        and snapshot.stress_summary != StressSummary.STRESSFUL
    )


def _reminder_for_state(
    state: RobotState, snapshot: WellnessSnapshot, reason: str
) -> WellnessReminder | None:
    if snapshot.data_stale:
        return WellnessReminder(
            text="Sync your Oura app for fresh data",
            category="sync",
        )

    if state == RobotState.SICK:
        if snapshot.rest_mode_active:
            return WellnessReminder(text="Rest mode on — take it easy today", category="sick")
        if snapshot.symptom_tags:
            return WellnessReminder(
                text="Listen to your body — rest if you need it",
                category="sick",
            )
        return WellnessReminder(
            text="Ring noticed changes — listen to your body",
            category="sick",
        )

    if state == RobotState.TIRED:
        if snapshot.sleep_score is not None and snapshot.sleep_score < 70:
            return WellnessReminder(text="Sleep was light — ease into today", category="sleep")
        return WellnessReminder(text="Readiness is low — go gently", category="readiness")

    if state == RobotState.MOTIVATE:
        if snapshot.meters_to_target and snapshot.meters_to_target > 0:
            return WellnessReminder(
                text=f"~{snapshot.meters_to_target}m to movement goal",
                category="activity",
            )
        return WellnessReminder(text="A short walk could feel great", category="activity")

    if state == RobotState.HAPPY:
        return WellnessReminder(text="Great balance today — keep it up", category="happy")

    if state == RobotState.RECOVERING:
        return WellnessReminder(
            text="Rest mode on — recovery is the work today",
            category="recovering",
        )

    if state == RobotState.STRESSED:
        return WellnessReminder(
            text="Stress was high — 2 min of calm breathing?",
            category="stress",
        )

    if state == RobotState.SLEEPY_NIGHT:
        if snapshot.minutes_to_bedtime is not None and snapshot.minutes_to_bedtime > 0:
            return WellnessReminder(
                text=f"~{snapshot.minutes_to_bedtime} min to optimal bedtime",
                category="bedtime",
            )
        return WellnessReminder(text="Past your optimal bedtime — wind down", category="bedtime")

    if state == RobotState.PROUD:
        if reason == "workout":
            return WellnessReminder(text="Strong workout logged — proud of you", category="proud")
        return WellnessReminder(text="Resilience is building — nicely done", category="proud")

    return None


def _weighted_pick(
    candidates: list[tuple[RobotState, float, str]],
) -> tuple[RobotState, str]:
    if not candidates:
        return RobotState.IDLE, "default"
    candidates.sort(key=lambda c: c[1], reverse=True)
    return candidates[0][0], candidates[0][2]


def evaluate(snapshot: WellnessSnapshot) -> PersonaDecision:
    thresholds = load_thresholds()
    weights = thresholds["priority"][snapshot.time_of_day.value]

    candidates: list[tuple[RobotState, float, str]] = []

    sick, sick_reason = _is_sick(snapshot, thresholds)
    if sick:
        candidates.append((RobotState.SICK, weights.get("sick", 5), sick_reason))

    if _is_recovering(snapshot, sick):
        candidates.append((RobotState.RECOVERING, weights.get("recovering", 4), "rest_mode"))

    if _is_tired(snapshot, thresholds):
        candidates.append((RobotState.TIRED, weights.get("sleep", 3), "poor_sleep_or_readiness"))

    if _needs_motivation(snapshot, thresholds):
        candidates.append((RobotState.MOTIVATE, weights.get("activity", 2), "low_activity"))

    if _is_stressed(snapshot):
        candidates.append((RobotState.STRESSED, weights.get("stress", 2), "stressful_day"))

    if _is_sleepy_night(snapshot, thresholds):
        candidates.append((RobotState.SLEEPY_NIGHT, weights.get("sleepy", 4), "near_bedtime"))

    proud, proud_reason = _is_proud(snapshot, thresholds)
    if proud:
        candidates.append((RobotState.PROUD, weights.get("proud", 2), proud_reason))

    if _is_happy(snapshot, thresholds):
        candidates.append((RobotState.HAPPY, 2.0, "balanced_day"))

    state, reason = _weighted_pick(candidates)
    reminder = _reminder_for_state(state, snapshot, reason)

    return PersonaDecision(state=state, reminder=reminder, priority_reason=reason)


def snapshot_with_time_of_day(snapshot: WellnessSnapshot) -> WellnessSnapshot:
    hour = snapshot.captured_at.hour if snapshot.captured_at else datetime.now().hour
    tod = WellnessSnapshot.time_of_day_from_hour(hour)
    return snapshot.model_copy(update={"time_of_day": tod})
