from datetime import datetime

from ouri.config import load_schedule
from ouri.persona import DayState, Scheduler
from ouri.persona.notifications import NotificationQueue
from ouri.wellness.models import TimeOfDay, WellnessReminder, WellnessSnapshot


def _clock(hour: int, minute: int = 0):
    return lambda: datetime(2026, 6, 14, hour, minute)


def _scheduler(hour: int, minute: int = 0) -> Scheduler:
    return Scheduler(load_schedule(), day_state=DayState(path=None), clock=_clock(hour, minute))


def _snapshot(**kwargs) -> WellnessSnapshot:
    base = dict(sleep_score=82, readiness_score=79, activity_score=70)
    base.update(kwargs)
    return WellnessSnapshot(**base)


def test_quiet_hours_asleep():
    assert _scheduler(23, 0).tick(_snapshot()).asleep is True
    assert _scheduler(3, 0).tick(_snapshot()).asleep is True
    assert _scheduler(9, 0).tick(_snapshot()).asleep is False


def test_time_of_day_phases():
    assert _scheduler(9).tick(_snapshot()).time_of_day == TimeOfDay.MORNING
    assert _scheduler(13).tick(_snapshot()).time_of_day == TimeOfDay.AFTERNOON
    assert _scheduler(19).tick(_snapshot()).time_of_day == TimeOfDay.EVENING


def test_morning_briefing_fires_once():
    sched = _scheduler(7, 30)
    out = sched.tick(_snapshot())
    assert out.briefing is not None
    assert out.briefing[0].category == "greeting"
    categories = [c.category for c in out.briefing]
    assert "sleep_recap" in categories and "readiness" in categories and "activity" in categories
    # Already played today -> no repeat.
    assert sched.tick(_snapshot()).briefing is None


def test_no_briefing_outside_window():
    assert _scheduler(14, 0).tick(_snapshot()).briefing is None


def test_bedtime_nudge_once():
    sched = _scheduler(21, 0)
    out = sched.tick(_snapshot(minutes_to_bedtime=30))
    assert any(c.category == "bedtime" for c in out.cards)
    assert sched.tick(_snapshot(minutes_to_bedtime=30)).cards == []


def test_bedtime_nudge_not_when_far():
    out = _scheduler(15, 0).tick(_snapshot(minutes_to_bedtime=300))
    assert out.cards == []


def test_refresh_cadence():
    clock = _clock(9, 0)
    sched = Scheduler(load_schedule(), day_state=DayState(path=None), clock=clock)
    # First tick anchors last_refresh; no immediate refresh.
    assert sched.tick(_snapshot()).should_refresh is False
    # Same minute -> still no refresh.
    assert sched.tick(_snapshot()).should_refresh is False


class _FakeClock:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


def test_notification_sequence_auto_advances():
    fc = _FakeClock()
    q = NotificationQueue(duration_sec=5.0, clock=fc)
    cards = [
        WellnessReminder(text="Hi", category="greeting"),
        WellnessReminder(text="Sleep 82", category="sleep_recap"),
    ]
    q.push_sequence(cards, seconds_each=2.0)
    assert q.current().text == "Hi"
    fc.t += 2.1
    assert q.current().text == "Sleep 82"
    fc.t += 2.1
    assert q.current() is None
