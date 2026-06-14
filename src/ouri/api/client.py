from __future__ import annotations

from datetime import date, datetime, timedelta

import httpx

from ouri.api.oauth import OAuthClient
from ouri.config import DataSource, settings
from ouri.engine.rules import snapshot_with_time_of_day
from ouri.wellness.models import StressSummary, WellnessSnapshot

LIVE_BASE = "https://api.ouraring.com/v2/usercollection"
SANDBOX_BASE = "https://api.ouraring.com/v2/sandbox/usercollection"


class OuraClient:
    def __init__(
        self,
        data_source: DataSource | None = None,
        oauth: OAuthClient | None = None,
    ) -> None:
        self.data_source = data_source or settings.ouri_data_source
        self.oauth = oauth or OAuthClient()
        self._base = SANDBOX_BASE if self.data_source == DataSource.SANDBOX else LIVE_BASE

    def _headers(self) -> dict[str, str]:
        token = self.oauth.get_access_token()
        return {"Authorization": f"Bearer {token}"}

    async def _get(self, endpoint: str, params: dict | None = None) -> dict:
        url = f"{self._base}/{endpoint}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self._headers(), params=params or {})
            if response.status_code == 401 and self.data_source == DataSource.LIVE:
                self.oauth.refresh()
                response = await client.get(
                    url, headers=self._headers(), params=params or {}
                )
            response.raise_for_status()
            return response.json()

    def _latest_item(self, payload: dict) -> dict | None:
        items = payload.get("data", [])
        if not items:
            return None
        return items[-1]

    def _active_rest_mode(self, payload: dict) -> bool:
        today = date.today()
        for period in payload.get("data", []):
            start = period.get("start_day")
            end = period.get("end_day")
            if start and start <= str(today) and (end is None or end >= str(today)):
                return True
        return False

    def _symptom_tags(self, payload: dict) -> list[str]:
        keywords = ("sick", "ill", "fever", "cold", "flu", "symptom", "headache", "cough")
        tags: list[str] = []
        for item in payload.get("data", []):
            tag_text = (item.get("tag") or item.get("name") or "").lower()
            if any(k in tag_text for k in keywords):
                tags.append(item.get("tag") or item.get("name") or tag_text)
        return tags

    def _main_sleep_period(self, payload: dict) -> dict | None:
        """Pick the longest sleep period of the day (the real night, not naps)."""
        periods = payload.get("data", [])
        if not periods:
            return None
        return max(periods, key=lambda p: p.get("total_sleep_duration") or 0)

    async def _get_optional(self, endpoint: str, params: dict) -> dict:
        """GET that tolerates missing scope / no data instead of failing the whole snapshot."""
        try:
            return await self._get(endpoint, params)
        except httpx.HTTPStatusError:
            return {"data": []}

    async def fetch_snapshot(self, day: date | None = None) -> WellnessSnapshot:
        target = day or date.today()
        start = target.isoformat()
        end = (target + timedelta(days=1)).isoformat()
        params = {"start_date": start, "end_date": end}

        sleep_data = await self._get("daily_sleep", params)
        readiness_data = await self._get("daily_readiness", params)
        activity_data = await self._get("daily_activity", params)
        stress_data = await self._get("daily_stress", params)

        rest_data = await self._get_optional("rest_mode_period", params)
        tag_data = await self._get_optional("enhanced_tag", params)
        # Detailed signals that power the recap, heartbeat, and proud states.
        sleep_detail = await self._get_optional("sleep", params)
        resilience_data = await self._get_optional("daily_resilience", params)
        workout_data = await self._get_optional("workout", params)

        # Latest live-ish heart rate (shown when Ouri is petted).
        now = datetime.now()
        hr_data = await self._get_optional(
            "heartrate",
            {
                "start_datetime": (now - timedelta(hours=3)).isoformat(),
                "end_datetime": now.isoformat(),
            },
        )
        hr_items = hr_data.get("data", [])
        current_hr = hr_items[-1].get("bpm") if hr_items else None

        sleep_item = self._latest_item(sleep_data)
        readiness_item = self._latest_item(readiness_data)
        activity_item = self._latest_item(activity_data)
        stress_item = self._latest_item(stress_data)
        resilience_item = self._latest_item(resilience_data)
        workout_item = self._latest_item(workout_data)
        sleep_period = self._main_sleep_period(sleep_detail)

        stress_raw = (stress_item or {}).get("day_summary")
        try:
            stress_summary = StressSummary(stress_raw) if stress_raw else StressSummary.UNKNOWN
        except ValueError:
            stress_summary = StressSummary.UNKNOWN

        contributors = (readiness_item or {}).get("contributors") or {}

        def _minutes(seconds: int | None) -> int | None:
            return round(seconds / 60) if seconds else None

        resting_hr = None
        if sleep_period:
            resting_hr = sleep_period.get("lowest_heart_rate") or sleep_period.get(
                "average_heart_rate"
            )

        snapshot = WellnessSnapshot(
            day=target,
            captured_at=datetime.now(),
            sleep_score=(sleep_item or {}).get("score"),
            readiness_score=(readiness_item or {}).get("score"),
            activity_score=(activity_item or {}).get("score"),
            stress_summary=stress_summary,
            temperature_deviation=(readiness_item or {}).get("temperature_deviation"),
            body_temperature_contributor=contributors.get("body_temperature"),
            steps=(activity_item or {}).get("steps"),
            meters_to_target=(activity_item or {}).get("meters_to_target"),
            resting_heart_rate=resting_hr,
            current_heart_rate=current_hr,
            resilience_level=(resilience_item or {}).get("level"),
            workout_intensity=(workout_item or {}).get("intensity"),
            sleep_deep_min=_minutes((sleep_period or {}).get("deep_sleep_duration")),
            sleep_rem_min=_minutes((sleep_period or {}).get("rem_sleep_duration")),
            sleep_light_min=_minutes((sleep_period or {}).get("light_sleep_duration")),
            total_sleep_min=_minutes((sleep_period or {}).get("total_sleep_duration")),
            rest_mode_active=self._active_rest_mode(rest_data),
            symptom_tags=self._symptom_tags(tag_data),
            data_stale=sleep_item is None and readiness_item is None,
        )
        return snapshot_with_time_of_day(snapshot)

    async def fetch_history(
        self, days: int = 7, end: date | None = None
    ) -> list[WellnessSnapshot]:
        """Lightweight per-day score history (oldest -> newest) for trend computation."""
        end_day = end or date.today()
        start_day = end_day - timedelta(days=days - 1)
        params = {
            "start_date": start_day.isoformat(),
            "end_date": (end_day + timedelta(days=1)).isoformat(),
        }

        sleep_data = await self._get_optional("daily_sleep", params)
        readiness_data = await self._get_optional("daily_readiness", params)
        activity_data = await self._get_optional("daily_activity", params)

        by_day: dict[str, dict] = {}
        for item in sleep_data.get("data", []):
            by_day.setdefault(item.get("day"), {})["sleep"] = item.get("score")
        for item in readiness_data.get("data", []):
            by_day.setdefault(item.get("day"), {})["readiness"] = item.get("score")
        for item in activity_data.get("data", []):
            by_day.setdefault(item.get("day"), {})["activity"] = item.get("score")

        snapshots: list[WellnessSnapshot] = []
        for day_str in sorted(d for d in by_day if d):
            scores = by_day[day_str]
            snapshots.append(
                WellnessSnapshot(
                    day=date.fromisoformat(day_str),
                    sleep_score=scores.get("sleep"),
                    readiness_score=scores.get("readiness"),
                    activity_score=scores.get("activity"),
                )
            )
        return snapshots
