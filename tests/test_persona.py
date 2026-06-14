from ouri.persona.fsm import PersonaFSM
from ouri.wellness.models import RobotState, TimeOfDay, WellnessSnapshot


def test_pet_reaction():
    snap = WellnessSnapshot(
        sleep_score=58,
        readiness_score=62,
        time_of_day=TimeOfDay.MORNING,
    )
    fsm = PersonaFSM(snap)
    fsm.pet()
    assert fsm.tick() == RobotState.PET_REACTION


def test_force_state_override():
    snap = WellnessSnapshot(activity_score=45, time_of_day=TimeOfDay.AFTERNOON)
    fsm = PersonaFSM(snap)
    fsm.force_state(RobotState.HAPPY)
    assert fsm.tick() == RobotState.HAPPY
