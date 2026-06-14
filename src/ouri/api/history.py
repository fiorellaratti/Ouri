from __future__ import annotations

import asyncio
import json

from ouri.api.cache import load_recent_snapshots
from ouri.config import DATA_DIR, DataSource, settings
from ouri.wellness.models import WellnessSnapshot

HISTORY_FIXTURE = DATA_DIR / "history.json"


def get_recent_snapshots(days: int = 7) -> list[WellnessSnapshot]:
    """Recent daily snapshots (oldest -> newest) for trend computation.

    Fixture mode reads ``data/history.json``; live/sandbox use the local cache
    and backfill from the Oura API the first time the cache is thin.
    """
    if settings.ouri_data_source == DataSource.FIXTURE:
        if not HISTORY_FIXTURE.exists():
            return []
        data = json.loads(HISTORY_FIXTURE.read_text())
        snapshots = [WellnessSnapshot.model_validate(d) for d in data]
        return snapshots[-days:]

    cached = load_recent_snapshots(days)
    if len(cached) >= 2:
        return cached

    # First live run: backfill the week so trends have something to show.
    from ouri.api.sync import fetch_and_cache_history

    try:
        asyncio.run(fetch_and_cache_history(days))
    except Exception:
        pass
    return load_recent_snapshots(days)
