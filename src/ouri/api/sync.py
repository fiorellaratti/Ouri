from __future__ import annotations

import asyncio

from ouri.api.cache import load_snapshot, save_snapshot
from ouri.api.client import OuraClient
from ouri.api.fixtures import load_fixture
from ouri.config import DataSource, settings
from ouri.wellness.models import WellnessSnapshot

__all__ = [
    "fetch_wellness_snapshot",
    "get_wellness_snapshot",
    "refresh_wellness_snapshot",
    "fetch_and_cache_history",
]


async def fetch_wellness_snapshot() -> WellnessSnapshot:
    if settings.ouri_data_source == DataSource.FIXTURE:
        return load_fixture()

    client = OuraClient()
    snapshot = await client.fetch_snapshot()
    save_snapshot(snapshot)
    return snapshot


def get_wellness_snapshot(use_cache: bool = True) -> WellnessSnapshot:
    if settings.ouri_data_source == DataSource.FIXTURE:
        return load_fixture()

    if use_cache:
        cached = load_snapshot()
        if cached:
            return cached

    return asyncio.run(fetch_wellness_snapshot())


async def refresh_wellness_snapshot() -> WellnessSnapshot:
    return await fetch_wellness_snapshot()


async def fetch_and_cache_history(days: int = 7) -> list[WellnessSnapshot]:
    """Fetch recent daily scores from Oura and cache them for trends."""
    client = OuraClient()
    snapshots = await client.fetch_history(days)
    for snap in snapshots:
        save_snapshot(snap)
    return snapshots
