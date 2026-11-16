"""Open-Meteo Historical Weather API → `climate_profiles`.

API docs: https://open-meteo.com/en/docs/historical-weather-api (no key; CC BY 4.0).
The raw JSON is cached under data/raw/weather/, so (a) the import is
reproducible and versioned by the cache file's checksum, and (b) we call
the free API once per city/period rather than on every run.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
from sqlalchemy import delete
from sqlalchemy.orm import Session

from accessastana.analysis.climate import classify_days, climate_summary, profile_shares
from accessastana.config import load_seasons
from accessastana.db.models import ClimateProfile
from accessastana.ingestion.base import BaseLoader, bulk_insert

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
DAILY_VARS = [
    "temperature_2m_mean",
    "temperature_2m_min",
    "wind_speed_10m_mean",
    "wind_speed_10m_max",
    "snowfall_sum",
]

Fetcher = Callable[[str, dict[str, Any]], dict[str, Any]]


def http_fetch(url: str, params: dict[str, Any]) -> dict[str, Any]:
    """GET the Open-Meteo archive API and return the JSON payload."""
    r = httpx.get(url, params=params, timeout=120)
    r.raise_for_status()
    return r.json()  # type: ignore[no-any-return]


def to_daily_frame(payload: dict[str, Any]) -> pd.DataFrame:
    """Open-Meteo daily payload → DataFrame indexed by date."""
    d = payload["daily"]
    df = pd.DataFrame({k: d[k] for k in d if k != "time"}, index=pd.to_datetime(d["time"]))
    return df.dropna(subset=["temperature_2m_min", "wind_speed_10m_mean"])


class OpenMeteoLoader(BaseLoader):
    """Open-Meteo history → season profiles with shares of days."""

    name = "climate"
    fetcher: Fetcher = staticmethod(http_fetch)  # replaced by a fake in tests

    def _cache_path(self) -> Path:
        p = load_seasons(self.ctx.config_dir).reference_period
        return self.ctx.path(f"data/raw/weather/{self.ctx.city.slug}_{p['start']}_{p['end']}.json")

    def source_files(self) -> list[Path]:
        cache = self._cache_path()
        if not cache.exists():
            w, p = self.ctx.city.weather, load_seasons(self.ctx.config_dir).reference_period
            params = {
                "latitude": w["latitude"],
                "longitude": w["longitude"],
                "start_date": p["start"],
                "end_date": p["end"],
                "daily": ",".join(DAILY_VARS),
                "timezone": "auto",
                "wind_speed_unit": "kmh",
            }
            payload = type(self).fetcher(ARCHIVE_URL, params)
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(payload))
        return [cache, self.ctx.config_path / "seasons.yaml"]

    def extract(self) -> dict[str, Any]:
        payload = json.loads(self._cache_path().read_text())
        daily = to_daily_frame(payload)
        seasons = load_seasons(self.ctx.config_dir)
        labels = classify_days(daily, seasons)
        out = {}
        for key, prof in seasons.profiles.items():
            shares = profile_shares(labels, prof.months)
            out[key] = {
                "speed_mps": prof.speed_mps,
                "max_minutes": prof.max_minutes,
                "share_of_days": shares.get(key),
                "stats": {
                    **climate_summary(daily, prof.months),
                    "grid_point": [payload.get("latitude"), payload.get("longitude")],
                    "label": prof.label,
                },
            }
        return out

    def load(self, session: Session, data: dict[str, Any], run_id: int) -> tuple[int, dict[str, Any]]:
        slug = self.ctx.city.slug
        session.execute(delete(ClimateProfile).where(ClimateProfile.city_slug == slug))
        n = bulk_insert(
            session,
            ClimateProfile.__table__,  # type: ignore[arg-type]
            [{"city_slug": slug, "season": k, **v} for k, v in data.items()],
        )
        return n, {k: v["share_of_days"] for k, v in data.items()}
