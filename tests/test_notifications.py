import time

from ouri.persona.notifications import NotificationQueue
from ouri.persona.fsm import PersonaFSM
from ouri.wellness.models import RobotState, TimeOfDay, WellnessReminder, WellnessSnapshot


def test_notification_expires():
    q = NotificationQueue(duration_sec=0.1)
    q.push(WellnessReminder(text="hello", category="sleep"))
    assert q.current() is not None
    time.sleep(0.15)
    assert q.current() is None


def test_face_only_after_notification_expires():
    snap = WellnessSnapshot(sleep_score=58, readiness_score=62, time_of_day=TimeOfDay.MORNING)
    fsm = PersonaFSM(snap)
    assert fsm.current_notification() is not None
    time.sleep(5.1)
    fsm.tick()
    assert fsm.current_notification() is None


def test_force_state_clears_notification():
    snap = WellnessSnapshot(sleep_score=58, time_of_day=TimeOfDay.MORNING)
    fsm = PersonaFSM(snap)
    assert fsm.current_notification() is not None
    fsm.force_state(RobotState.HAPPY)
    assert fsm.current_notification() is None
