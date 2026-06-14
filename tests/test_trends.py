from ouri.api.history import get_recent_snapshots
from ouri.config import load_thresholds
from ouri.display.trends import render_trend_card
from ouri.wellness.models import WellnessSnapshot
from ouri.wellness.trends import (
    TrendDirection,
    compute_trends,
    headline_reminder,
)

THRESHOLDS = load_thresholds()


def _snaps(scores: list[int]) -> list[WellnessSnapshot]:
    return [WellnessSnapshot(sleep_score=s, readiness_score=s, activity_score=s) for s in scores]


def test_direction_up_down_flat():
    up = compute_trends(_snaps([60, 64, 70, 78, 85]), THRESHOLDS)
    assert up.sleep_dir == TrendDirection.UP
    down = compute_trends(_snaps([85, 80, 74, 68, 60]), THRESHOLDS)
    assert down.sleep_dir == TrendDirection.DOWN
    flat = compute_trends(_snaps([80, 81, 80, 79, 80]), THRESHOLDS)
    assert flat.sleep_dir == TrendDirection.FLAT


def test_sleep_streak():
    # good threshold for sleep is 85; trailing 3 are >= 85
    summary = compute_trends(_snaps([70, 80, 86, 88, 90]), THRESHOLDS)
    assert summary.sleep_streak == 3


def test_headline_prefers_streak():
    summary = compute_trends(_snaps([86, 87, 88, 89, 90]), THRESHOLDS)
    reminder = headline_reminder(summary)
    assert reminder is not None
    assert reminder.category == "proud"
    assert "streak" in reminder.text


def test_headline_declining_sleep():
    summary = compute_trends(_snaps([84, 80, 74, 68, 60]), THRESHOLDS)
    reminder = headline_reminder(summary)
    assert reminder is not None
    assert reminder.category == "sleep"


def test_headline_none_when_flat():
    summary = compute_trends(_snaps([78, 79, 78, 79, 78]), THRESHOLDS)
    assert headline_reminder(summary) is None


def test_history_fixture_loads():
    snaps = get_recent_snapshots(7)
    assert len(snaps) == 7
    assert snaps[0].day.isoformat() == "2026-06-04"
    assert snaps[-1].sleep_score == 90


def test_render_trend_card_size():
    img = render_trend_card(128, 64, "SLEEP THIS WEEK", [70, 75, 80, 85, 90], TrendDirection.UP)
    assert img.size == (128, 64)
    assert img.mode == "1"


def test_render_trend_card_empty_series():
    img = render_trend_card(128, 64, "SLEEP THIS WEEK", [], TrendDirection.FLAT)
    assert img.size == (128, 64)
