from __future__ import annotations

import asyncio
import sys
import time

from ouri.api.fixtures import load_fixture_by_index
from ouri.api.history import get_recent_snapshots
from ouri.api.sync import get_wellness_snapshot, refresh_wellness_snapshot
from ouri.config import load_schedule, load_thresholds, settings
from ouri.display import (
    create_display,
    render_face,
    render_heartrate,
    render_message,
    render_sleep_recap,
    render_trend_card,
)
from ouri.input import InputEventType, create_input
from ouri.persona import Clock, PersonaFSM, Scheduler
from ouri.wellness.models import RobotState
from ouri.wellness.trends import compute_trends


def _print_controls() -> None:
    print(
        "\nOuri controls:\n"
        "  1-5  force state (idle/tired/motivate/sick/happy)\n"
        "  6-9  force state (sleepy/proud/stressed/recovering)\n"
        "  0    clear override\n"
        "  p    pet (or click the window)\n"
        "  n    next fixture scenario\n"
        "  r    refresh wellness data\n"
        "  t    jump simulated clock +1h (test the daily arc)\n"
        "  q    quit\n"
    )


def main() -> None:
    display = create_display()
    input_handler = create_input()
    persona = PersonaFSM()

    schedule = load_schedule()
    thresholds = load_thresholds()
    clock = Clock()
    scheduler = Scheduler(schedule, clock=clock.now)
    briefing_seconds = float(schedule.get("briefing_card_seconds", 2.5))

    def refresh_trends() -> None:
        try:
            persona.set_trends(compute_trends(get_recent_snapshots(7), thresholds))
        except Exception as exc:
            print(f"Trend load failed: {exc}")

    fixture_index = 0
    try:
        snapshot = get_wellness_snapshot()
        persona.set_snapshot(snapshot)
        print(f"Loaded wellness data ({settings.ouri_data_source.value})")
    except Exception as exc:
        print(f"Warning: could not load wellness data: {exc}")
        snapshot = load_fixture_by_index(0)
        persona.set_snapshot(snapshot)
    refresh_trends()

    _print_controls()
    frame_interval = 1.0 / settings.fps
    running = True

    try:
        while running:
            loop_start = time.monotonic()

            for event in input_handler.poll():
                if event.type == InputEventType.QUIT:
                    running = False
                elif event.type == InputEventType.PET:
                    persona.pet()
                elif event.type == InputEventType.NEXT_FIXTURE:
                    fixture_index += 1
                    snap = load_fixture_by_index(fixture_index)
                    persona.set_snapshot(snap)
                    print(f"Scenario: {snap.day} ({persona.tick().value})")
                elif event.type == InputEventType.FORCE_STATE and event.value:
                    persona.force_state(RobotState(event.value))
                elif event.type == InputEventType.CLEAR_OVERRIDE:
                    persona.clear_override()
                elif event.type == InputEventType.JUMP_TIME:
                    clock.advance(hours=1)
                    print(f"Clock jumped to {clock.now():%H:%M}")
                elif event.type == InputEventType.REFRESH:
                    try:
                        snap = asyncio.run(refresh_wellness_snapshot())
                        persona.set_snapshot(snap)
                        refresh_trends()
                        print("Wellness data refreshed.")
                    except Exception as exc:
                        print(f"Refresh failed: {exc}")

            sched = scheduler.tick(persona.snapshot, persona.trends)
            persona.update_time_of_day(sched.time_of_day)
            if sched.should_refresh:
                try:
                    persona.set_snapshot(asyncio.run(refresh_wellness_snapshot()))
                    refresh_trends()
                except Exception as exc:
                    print(f"Scheduled refresh failed: {exc}")
            if sched.briefing:
                persona.push_sequence(sched.briefing, briefing_seconds)
            for card in sched.cards:
                persona.notify(card)

            mood = persona.tick()
            snap = persona.snapshot

            if sched.asleep:
                image = render_face(display.width, display.height, RobotState.ASLEEP, persona.frame)
            else:
                note = persona.current_notification()
                trends = persona.trends
                if note and note.category == "heartrate" and persona.current_bpm():
                    image = render_heartrate(
                        display.width, display.height, persona.current_bpm(), persona.frame
                    )
                elif note and note.category == "sleep_recap" and snap and snap.has_sleep_stages:
                    image = render_sleep_recap(display.width, display.height, snap, persona.frame)
                elif note and note.category == "trend_chart" and trends and trends.has_data:
                    image = render_trend_card(
                        display.width,
                        display.height,
                        "SLEEP THIS WEEK",
                        trends.sleep_series,
                        trends.sleep_dir,
                        persona.frame,
                    )
                elif note:
                    image = render_message(display.width, display.height, note, persona.frame)
                else:
                    image = render_face(
                        display.width,
                        display.height,
                        mood,
                        persona.frame,
                        heartbeat_bpm=snap.resting_heart_rate if snap else None,
                    )
            display.show(image)

            elapsed = time.monotonic() - loop_start
            sleep_time = max(0.0, frame_interval - elapsed)
            time.sleep(sleep_time)
    finally:
        display.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
