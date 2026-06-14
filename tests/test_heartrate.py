from ouri.display.heartrate import _pulse_scale, render_heartrate
from ouri.persona import PersonaFSM
from ouri.wellness.models import WellnessSnapshot


def test_render_heartrate_size():
    img = render_heartrate(128, 64, 72, frame=0)
    assert img.size == (128, 64)
    assert img.mode == "1"


def test_pulse_thumps_on_beat():
    # At 60 bpm and 12 fps, a beat lands every 12 frames.
    assert _pulse_scale(0, 60) > 1.0  # the thump frame
    assert _pulse_scale(6, 60) == 1.0  # mid-beat rest


def test_pet_shows_live_heart_rate():
    snap = WellnessSnapshot(sleep_score=80, current_heart_rate=77, resting_heart_rate=55)
    persona = PersonaFSM(snapshot=snap)
    persona.pet()
    note = persona.current_notification()
    assert note is not None
    assert note.category == "heartrate"
    assert persona.current_bpm() == 77  # prefers live over resting


def test_pet_falls_back_to_resting_hr():
    snap = WellnessSnapshot(sleep_score=80, resting_heart_rate=58)
    persona = PersonaFSM(snapshot=snap)
    persona.pet()
    note = persona.current_notification()
    assert note is not None
    assert note.category == "heartrate"
    assert persona.current_bpm() == 58


def test_pet_without_hr_uses_text_card():
    snap = WellnessSnapshot(sleep_score=80)
    persona = PersonaFSM(snapshot=snap)
    persona.pet()
    assert persona.current_bpm() is None
    note = persona.current_notification()
    # No HR -> either the gentle pet text or nothing, but never a heartrate card.
    assert note is None or note.category != "heartrate"
