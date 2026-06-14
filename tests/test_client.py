from __future__ import annotations

import asyncio
from datetime import date

from ouri.api.client import OuraClient
from ouri.config import DataSource


def _client(payloads: dict) -> OuraClient:
    client = OuraClient(data_source=DataSource.LIVE)

    async def fake_get(endpoint: str, params: dict | None = None) -> dict:
        return payloads.get(endpoint, {"data": []})

    client._get = fake_get  # bypass network + auth
    return client


def test_fetch_snapshot_enriched():
    payloads = {
        "daily_sleep": {"data": [{"day": "2026-06-14", "score": 82}]},
        "daily_readiness": {
            "data": [
                {
                    "day": "2026-06-14",
                    "score": 78,
                    "temperature_deviation": 0.1,
                    "contributors": {"body_temperature": 90},
                }
            ]
        },
        "daily_activity": {
            "data": [{"day": "2026-06-14", "score": 75, "steps": 8000, "meters_to_target": 0}]
        },
        "daily_stress": {"data": [{"day": "2026-06-14", "day_summary": "normal"}]},
        "sleep": {
            "data": [
                {
                    "day": "2026-06-14",
                    "deep_sleep_duration": 3600,
                    "rem_sleep_duration": 5400,
                    "light_sleep_duration": 12600,
                    "total_sleep_duration": 21600,
                    "lowest_heart_rate": 52,
                }
            ]
        },
        "daily_resilience": {"data": [{"day": "2026-06-14", "level": "strong"}]},
        "workout": {"data": [{"day": "2026-06-14", "intensity": "moderate"}]},
    }
    snap = asyncio.run(_client(payloads).fetch_snapshot(date(2026, 6, 14)))

    assert snap.sleep_score == 82
    assert snap.readiness_score == 78
    assert snap.sleep_deep_min == 60
    assert snap.sleep_rem_min == 90
    assert snap.sleep_light_min == 210
    assert snap.total_sleep_min == 360
    assert snap.has_sleep_stages
    assert snap.resting_heart_rate == 52
    assert snap.resilience_level == "strong"
    assert snap.workout_intensity == "moderate"


def test_fetch_snapshot_survives_missing_detail():
    # Only the core summaries available (e.g. missing scopes / no data).
    payloads = {
        "daily_sleep": {"data": [{"day": "2026-06-14", "score": 60}]},
        "daily_readiness": {"data": [{"day": "2026-06-14", "score": 65}]},
        "daily_activity": {"data": [{"day": "2026-06-14", "score": 70}]},
    }
    snap = asyncio.run(_client(payloads).fetch_snapshot(date(2026, 6, 14)))
    assert snap.sleep_score == 60
    assert not snap.has_sleep_stages
    assert snap.resting_heart_rate is None


def test_main_sleep_period_picks_longest():
    payloads = {
        "sleep": {
            "data": [
                {"day": "2026-06-14", "total_sleep_duration": 1800, "lowest_heart_rate": 70},
                {"day": "2026-06-14", "total_sleep_duration": 25200, "lowest_heart_rate": 50},
            ]
        },
    }
    snap = asyncio.run(_client(payloads).fetch_snapshot(date(2026, 6, 14)))
    assert snap.resting_heart_rate == 50  # from the longer (night) period


def test_fetch_history_builds_series():
    payloads = {
        "daily_sleep": {
            "data": [
                {"day": "2026-06-12", "score": 70},
                {"day": "2026-06-13", "score": 80},
                {"day": "2026-06-14", "score": 85},
            ]
        },
        "daily_readiness": {
            "data": [
                {"day": "2026-06-12", "score": 72},
                {"day": "2026-06-13", "score": 78},
                {"day": "2026-06-14", "score": 80},
            ]
        },
        "daily_activity": {
            "data": [
                {"day": "2026-06-12", "score": 60},
                {"day": "2026-06-13", "score": 70},
                {"day": "2026-06-14", "score": 75},
            ]
        },
    }
    snaps = asyncio.run(_client(payloads).fetch_history(3, end=date(2026, 6, 14)))
    assert [s.sleep_score for s in snaps] == [70, 80, 85]
    assert snaps[0].day == date(2026, 6, 12)
    assert snaps[-1].day == date(2026, 6, 14)
