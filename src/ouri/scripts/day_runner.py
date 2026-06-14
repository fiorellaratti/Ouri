"""Fast-forward a simulated day in the OLED emulator to preview the daily arc.

Watch Ouri sleep overnight, wake with a morning briefing, move through the day,
and get evening nudges -- all in about a minute, with no hardware or real data.
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, time as dtime, timedelta

from ouri.api.fixtures import load_fixture_by_index
from ouri.api.history import get_recent_snapshots
from ouri.api.sync import get_wellness_snapshot
from ouri.config import DataSource, load_schedule, load_thresholds, settings
from ouri.display import (
    create_display,
    render_face,
    render_message,
    render_sleep_recap,
    render_trend_card,
)
from ouri.input import InputEventType, create_input
from ouri.persona import DayState, PersonaFSM, Scheduler
from ouri.wellness.models import RobotState
from ouri.wellness.trends import compute_trends

SIM_DAY_SECONDS = 80.0  # real seconds to play a full 24h
OPTIMAL_BEDTIME = dtime(22, 30)


class FastClock:
    """Maps real elapsed time to a fast-moving simulated clock."""

    def __init__(self, start: datetime, speed: float) -> None:
        self._start_sim = start
        self._speed = speed
        self._start_real = time.monotonic()

    def now(self) -> datetime:
        elapsed = time.monotonic() - self._start_real
        return self._start_sim + timedelta(seconds=elapsed * self._speed)


def _minutes_to_bedtime(now: datetime) -> int:
    bedtime = now.replace(
        hour=OPTIMAL_BEDTIME.hour, minute=OPTIMAL_BEDTIME.minute, second=0, microsecond=0
    )
    if now > bedtime:
        bedtime += timedelta(days=1)
    return int((bedtime - now).total_seconds() // 60)


def main() -> None:
    schedule = load_schedule()
    briefing_seconds = float(schedule.get("briefing_card_seconds", 2.5))

    start = datetime.now().replace(hour=5, minute=45, second=0, microsecond=0)
    speed = 86400 / SIM_DAY_SECONDS
    clock = FastClock(start, speed)

    # Fresh in-memory day-state so the briefing always plays in the demo.
    scheduler = Scheduler(schedule, day_state=DayState(path=None), clock=clock.now)

    display = create_display()
    input_handler = create_input()
    persona = PersonaFSM()

    if settings.ouri_data_source == DataSource.FIXTURE:
        snapshot = load_fixture_by_index(0)
    else:
        try:
            snapshot = get_wellness_snapshot()
            print(f"Loaded your wellness data ({settings.ouri_data_source.value})")
        except Exception as exc:
            print(f"Could not load live data ({exc}); falling back to a fixture.")
            snapshot = load_fixture_by_index(0)
    persona.set_snapshot(snapshot)
    persona.set_trends(compute_trends(get_recent_snapshots(7), load_thresholds()))

    print(f"Simulating a full day in ~{SIM_DAY_SECONDS:.0f}s. Close window or press q to exit.")
    frame_interval = 1.0 / settings.fps
    last_label = ""
    running = True

    try:
        while running:
            loop_start = time.monotonic()
            now = clock.now()

            for event in input_handler.poll():
                if event.type == InputEventType.QUIT:
                    running = False
                elif event.type == InputEventType.PET:
                    persona.pet()

            if persona.snapshot:
                persona.snapshot.minutes_to_bedtime = _minutes_to_bedtime(now)

            sched = scheduler.tick(persona.snapshot, persona.trends)
            persona.update_time_of_day(sched.time_of_day)
            if sched.briefing:
                persona.push_sequence(sched.briefing, briefing_seconds)
            for card in sched.cards:
                persona.notify(card)

            mood = persona.tick()

            if sched.asleep:
                label = "asleep"
                image = render_face(display.width, display.height, RobotState.ASLEEP, persona.frame)
            else:
                note = persona.current_notification()
                snap = persona.snapshot
                trends = persona.trends
                if note and note.category == "sleep_recap" and snap and snap.has_sleep_stages:
                    label = "card: sleep recap"
                    image = render_sleep_recap(display.width, display.height, snap, persona.frame)
                elif note and note.category == "trend_chart" and trends and trends.has_data:
                    label = "card: sleep trend"
                    image = render_trend_card(
                        display.width,
                        display.height,
                        "SLEEP THIS WEEK",
                        trends.sleep_series,
                        trends.sleep_dir,
                        persona.frame,
                    )
                elif note:
                    label = f"card: {note.text}"
                    image = render_message(display.width, display.height, note, persona.frame)
                else:
                    label = mood.value
                    image = render_face(
                        display.width,
                        display.height,
                        mood,
                        persona.frame,
                        heartbeat_bpm=persona.snapshot.resting_heart_rate
                        if persona.snapshot
                        else None,
                    )
            display.show(image)

            if label != last_label:
                print(f"{now:%H:%M}  {label}")
                last_label = label

            if clock.now() >= start + timedelta(hours=24):
                running = False

            elapsed = time.monotonic() - loop_start
            time.sleep(max(0.0, frame_interval - elapsed))
    finally:
        display.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
