"""Pydantic request/response models: the API contract (docs/api-contract.md)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Method = Literal["max_covering", "p_median"]


class Health(BaseModel):
    """Service health."""

    status: str
    db: str


class CityOut(BaseModel):
    """City metadata for the UI."""

    slug: str
    name: dict[str, str]
    center: list[float]
    h3_resolution: int
    population_total: float | None
    attribution: list[str]


class CategoryOut(BaseModel):
    """Facility category."""

    key: str
    label: str


class SeasonOut(BaseModel):
    """Season profile."""

    key: str
    label: str
    speed_mps: float
    max_minutes: float
    share_of_days: float | None = None


class CellValue(BaseModel):
    """Value of one H3 cell (minutes or index)."""

    h3: str
    value: float | None
    reachable: bool
    population: float


class AccessibilityOut(BaseModel):
    """Accessibility layer for one city, category and season."""

    city: str
    category: str
    season: str
    metric: Literal["minutes", "index"]
    max_minutes: float
    cells: list[CellValue]


class CategorySummary(BaseModel):
    """Population-weighted shares for one category."""

    share_within: dict[str, float]
    share_reachable: float
    mean_minutes: float | None


class DistrictSummary(BaseModel):
    """Summary of one district (or the whole city)."""

    id: int | None
    name: str
    population: float
    index: float | None
    categories: dict[str, CategorySummary]


class DistrictsSummaryOut(BaseModel):
    """District summary table."""

    city: str
    season: str
    thresholds: list[float]
    districts: list[DistrictSummary]
    city_total: DistrictSummary


class NewFacility(BaseModel):
    """A proposed facility location."""

    lon: float = Field(ge=-180, le=180)
    lat: float = Field(ge=-90, le=90)
    name: str | None = None


class ScenarioIn(BaseModel):
    """What-if scenario request."""

    city: str
    category: str
    season: str
    add: list[NewFacility] = []
    remove: list[int] = []
    save: bool = False
    name: str | None = None


class Metrics(BaseModel):
    """Headline accessibility metrics."""

    population_reachable: float
    share_reachable: float
    mean_minutes: float | None


class ChangedCell(BaseModel):
    """A cell whose walking time changed in a scenario."""

    h3: str
    before: float | None
    after: float | None
    reachable_after: bool


class ScenarioOut(BaseModel):
    """What-if scenario result."""

    scenario_id: int | None
    before: Metrics
    after: Metrics
    changed_cells: list[ChangedCell]


class OptimizeIn(BaseModel):
    """Facility-location optimisation request."""

    city: str
    category: str
    season: str
    k: int = Field(ge=1)
    method: Method = "max_covering"


class Location(BaseModel):
    """A recommended site and the population it newly covers."""

    h3: str
    lon: float
    lat: float
    population_gain: float


class OptimizeOut(BaseModel):
    """Optimisation result."""

    method: Method
    k: int
    status: str
    solve_seconds: float
    locations: list[Location]
    before: Metrics
    after: Metrics
