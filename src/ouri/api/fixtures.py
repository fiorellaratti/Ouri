from __future__ import annotations

import json
from pathlib import Path

from ouri.config import FIXTURES_DIR, settings
from ouri.wellness.models import WellnessSnapshot

FIXTURE_FILES = sorted(FIXTURES_DIR.glob("*.json"))


def load_fixture(path: Path | str | None = None) -> WellnessSnapshot:
    if path:
        fixture_path = Path(path)
    elif settings.ouri_fixture:
        fixture_path = Path(settings.ouri_fixture)
    elif FIXTURE_FILES:
        fixture_path = FIXTURE_FILES[0]
    else:
        raise FileNotFoundError("No fixtures found in data/fixtures/")

    data = json.loads(fixture_path.read_text())
    return WellnessSnapshot.model_validate(data)


def list_fixtures() -> list[Path]:
    return FIXTURE_FILES


def load_fixture_by_index(index: int) -> WellnessSnapshot:
    files = list_fixtures()
    if not files:
        raise FileNotFoundError("No fixtures found")
    return load_fixture(files[index % len(files)])
