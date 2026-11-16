"""Typed access to the YAML configuration in config/.

Validating the YAML with pydantic at load time means a typo in a tag mapping
or season profile fails fast with a clear message instead of silently
producing wrong research numbers.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from accessastana.settings import get_settings


class CategoryConfig(BaseModel):
    """One facility category: OSM tag rules and preprocessing parameters."""

    label: str
    rules: list[dict[str, list[str]]]
    dedupe_radius_m: float = 0
    min_area_m2: float = 0
    # If set, the min-area filter applies only to objects with these tags.
    min_area_applies_to: dict[str, list[str]] | None = None
    boundary_sample_m: float | None = None

    def matches(self, tags: Any) -> bool:
        """True if an OSM tag mapping satisfies any rule (OR of ANDs)."""
        return any(all(tags.get(k) in vals for k, vals in rule.items()) for rule in self.rules)


class SeasonProfile(BaseModel):
    """Walking speed and acceptable time for one season profile."""

    label: str
    months: list[int]
    speed_mps: float = Field(gt=0)
    max_minutes: float = Field(gt=0)
    day_rule: dict[str, float] | None = None


class SeasonsConfig(BaseModel):
    """All season profiles plus the reference period and summary thresholds."""

    reference_period: dict[str, str]
    profiles: dict[str, SeasonProfile]
    api_seasons: list[str]
    summary_thresholds: list[float]


class CityConfig(BaseModel):
    """Per-city configuration (config/cities/<slug>.yaml)."""

    slug: str
    name: dict[str, str]
    osm: dict[str, Any]
    metric_crs: str
    h3_resolution: int = 8
    population: dict[str, str]
    weather: dict[str, float]
    map_center: list[float]


def _load(path: Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache
def load_categories(config_dir: Path | None = None) -> dict[str, CategoryConfig]:
    """Parsed and validated config/categories.yaml (cached)."""
    d = config_dir or get_settings().config_dir
    raw = _load(d / "categories.yaml")["categories"]
    return {k: CategoryConfig(**v) for k, v in raw.items()}


@lru_cache
def load_seasons(config_dir: Path | None = None) -> SeasonsConfig:
    """Parsed and validated config/seasons.yaml (cached)."""
    d = config_dir or get_settings().config_dir
    return SeasonsConfig(**_load(d / "seasons.yaml"))


@lru_cache
def load_city(slug: str, config_dir: Path | None = None) -> CityConfig:
    """Parsed and validated config/cities/<slug>.yaml (cached)."""
    d = config_dir or get_settings().config_dir
    return CityConfig(**_load(d / "cities" / f"{slug}.yaml"))


def list_city_slugs(config_dir: Path | None = None) -> list[str]:
    """Slugs of all configured cities."""
    d = config_dir or get_settings().config_dir
    return sorted(p.stem for p in (d / "cities").glob("*.yaml"))
