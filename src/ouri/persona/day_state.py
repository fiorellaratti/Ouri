from __future__ import annotations

import json
from pathlib import Path

from ouri.config import DAY_STATE_PATH


class DayState:
    """Tracks which once-per-day events already fired, persisted across runs.

    Pass ``path=None`` for an in-memory instance (useful for tests). The state
    auto-resets whenever the calendar day changes.
    """

    def __init__(self, path: Path | None = DAY_STATE_PATH) -> None:
        self._path = path
        self._day: str = ""
        self._fired: set[str] = set()
        self._load()

    def _load(self) -> None:
        if not self._path or not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text())
            self._day = data.get("day", "")
            self._fired = set(data.get("fired", []))
        except (json.JSONDecodeError, OSError):
            self._day = ""
            self._fired = set()

    def _save(self) -> None:
        if not self._path:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps({"day": self._day, "fired": sorted(self._fired)}))

    def _roll(self, today: str) -> None:
        if today != self._day:
            self._day = today
            self._fired = set()

    def is_done(self, key: str, today: str) -> bool:
        self._roll(today)
        return key in self._fired

    def mark(self, key: str, today: str) -> None:
        self._roll(today)
        self._fired.add(key)
        self._save()
