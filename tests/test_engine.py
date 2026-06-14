from ouri.engine.rules import evaluate
from ouri.wellness.models import RobotState, StressSummary, TimeOfDay, WellnessSnapshot


def test_bad_night_tired():
    snap = WellnessSnapshot(
        sleep_score=58,
        readiness_score=62,
        time_of_day=TimeOfDay.MORNING,
    )
    decision = evaluate(snap)
    assert decision.state == RobotState.TIRED


def test_elevated_temp_sick():
    snap = WellnessSnapshot(
        temperature_deviation=1.2,
        body_temperature_contributor=55,
        time_of_day=TimeOfDay.MORNING,
    )
    decision = evaluate(snap)
    assert decision.state == RobotState.SICK


def test_sedentary_motivate():
    snap = WellnessSnapshot(
        activity_score=45,
        meters_to_target=3500,
        time_of_day=TimeOfDay.AFTERNOON,
    )
    decision = evaluate(snap)
    assert decision.state == RobotState.MOTIVATE


def test_good_day_happy():
    snap = WellnessSnapshot(
        sleep_score=88,
        readiness_score=90,
        activity_score=85,
        stress_summary=StressSummary.RESTORED,
        time_of_day=TimeOfDay.AFTERNOON,
    )
    decision = evaluate(snap)
    assert decision.state == RobotState.HAPPY


def test_rest_mode_sick():
    snap = WellnessSnapshot(
        rest_mode_active=True,
        symptom_tags=["feeling sick"],
        time_of_day=TimeOfDay.MORNING,
    )
    decision = evaluate(snap)
    assert decision.state == RobotState.SICK
    assert decision.reminder is not None
    assert "Rest mode" in decision.reminder.text


def test_rest_mode_without_symptoms_recovering():
    snap = WellnessSnapshot(
        sleep_score=74,
        readiness_score=68,
        activity_score=50,
        temperature_deviation=0.2,
        body_temperature_contributor=80,
        rest_mode_active=True,
        time_of_day=TimeOfDay.MORNING,
    )
    decision = evaluate(snap)
    assert decision.state == RobotState.RECOVERING


def test_stressful_day_stressed():
    snap = WellnessSnapshot(
        sleep_score=80,
        readiness_score=80,
        activity_score=80,
        meters_to_target=0,
        stress_summary=StressSummary.STRESSFUL,
        time_of_day=TimeOfDay.AFTERNOON,
    )
    decision = evaluate(snap)
    assert decision.state == RobotState.STRESSED


def test_evening_bedtime_sleepy():
    snap = WellnessSnapshot(
        sleep_score=80,
        readiness_score=78,
        activity_score=74,
        meters_to_target=0,
        minutes_to_bedtime=30,
        time_of_day=TimeOfDay.EVENING,
    )
    decision = evaluate(snap)
    assert decision.state == RobotState.SLEEPY_NIGHT


def test_hard_workout_proud():
    snap = WellnessSnapshot(
        sleep_score=82,
        readiness_score=80,
        activity_score=79,
        meters_to_target=0,
        workout_intensity="hard",
        time_of_day=TimeOfDay.AFTERNOON,
    )
    decision = evaluate(snap)
    assert decision.state == RobotState.PROUD
