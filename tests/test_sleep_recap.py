from ouri.display.sleep_recap import _fmt_duration, render_sleep_recap
from ouri.wellness.models import WellnessSnapshot


def test_has_sleep_stages():
    full = WellnessSnapshot(sleep_deep_min=90, sleep_rem_min=100, sleep_light_min=240)
    assert full.has_sleep_stages is True
    assert WellnessSnapshot(sleep_deep_min=90).has_sleep_stages is False
    assert WellnessSnapshot().has_sleep_stages is False


def test_fmt_duration():
    assert _fmt_duration(455) == "7h 35m"
    assert _fmt_duration(60) == "1h 00m"


def test_render_sleep_recap_size():
    snap = WellnessSnapshot(
        sleep_deep_min=95, sleep_rem_min=110, sleep_light_min=250, total_sleep_min=455
    )
    img = render_sleep_recap(128, 64, snap)
    assert img.size == (128, 64)
    assert img.mode == "1"


def test_render_sleep_recap_infers_total():
    snap = WellnessSnapshot(sleep_deep_min=40, sleep_rem_min=55, sleep_light_min=180)
    img = render_sleep_recap(128, 64, snap)
    assert img.size == (128, 64)
