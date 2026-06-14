"""Cycle through wellness fixtures in the OLED emulator."""

from __future__ import annotations

import sys
import time

from ouri.api.fixtures import list_fixtures, load_fixture
from ouri.config import settings
from ouri.display import create_display, render_face, render_message
from ouri.engine.rules import evaluate
from ouri.persona import PersonaFSM


def main() -> None:
    fixtures = list_fixtures()
    if not fixtures:
        print("No fixtures in data/fixtures/")
        sys.exit(1)

    display = create_display()
    interval = 4.0

    print(f"Cycling {len(fixtures)} scenarios ({interval}s each). Close window to exit.")

    try:
        while True:
            for path in fixtures:
                snapshot = load_fixture(path)
                persona = PersonaFSM(snapshot)
                decision = evaluate(snapshot)
                print(f"{path.name}: {decision.state.value} — {decision.reminder}")

                frames = int(interval * settings.fps)
                for frame_i in range(frames):
                    state = persona.tick()
                    note = persona.current_notification()
                    if note:
                        image = render_message(display.width, display.height, note, persona.frame)
                    else:
                        image = render_face(
                            display.width,
                            display.height,
                            state,
                            persona.frame,
                            heartbeat_bpm=snapshot.resting_heart_rate,
                        )
                    display.show(image)
                    time.sleep(1.0 / settings.fps)
    except KeyboardInterrupt:
        pass
    finally:
        display.close()


if __name__ == "__main__":
    main()
