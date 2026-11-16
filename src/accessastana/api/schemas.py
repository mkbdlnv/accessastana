"""Pydantic request/response models: the API contract (docs/api-contract.md)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Method = Literal["max_covering", "p_median"]


class Health(BaseModel):
    status: str
    db: str


class CityOut(BaseModel):
    slug: str
    name: dict[str, str]
    center: list[float]
    h3_resolution: int
    population_total: float | None
    attribution: list[str]


class CategoryOut(BaseModel):
    key: str
    label: str


class SeasonOut(BaseModel):
    key: str
    label: str
    speed_mps: float
    max_minutes: float
    share_of_days: float | None = None


class CellValue(BaseModel):
    h3: str
    value: float | None
    reachable: bool
    population: float


class AccessibilityOut(BaseModel):
    city: str
    category: str
    season: str
    metric: Literal["minutes", "index"]
    max_minutes: float
    cells: list[CellValue]


class CategorySummary(BaseModel):
    share_within: dict[str, float]
    share_reachable: float
    mean_minutes: float | None


class DistrictSummary(BaseModel):
    id: int | None
    name: str
    population: float
    index: float | None
    categories: dict[str, CategorySummary]


class DistrictsSummaryOut(BaseModel):
    city: str
    season: str
    thresholds: list[float]
    districts: list[DistrictSummary]
    city_total: DistrictSummary


class NewFacility(BaseModel):
    lon: float = Field(ge=-180, le=180)
    lat: float = Field(ge=-90, le=90)
    name: str | None = None


class ScenarioIn(BaseModel):
    city: str
    category: str
    season: str
    add: list[NewFacility] = []
    remove: list[int] = []
    save: bool = False
    name: str | None = None


class Metrics(BaseModel):
    population_reachable: float
    share_reachable: float
    mean_minutes: float | None


class ChangedCell(BaseModel):
    h3: str
    before: float | None
    after: float | None
    reachable_after: bool


class ScenarioOut(BaseModel):
    scenario_id: int | None
    before: Metrics
    after: Metrics
    changed_cells: list[ChangedCell]


class OptimizeIn(BaseModel):
    city: str
    category: str
    season: str
    k: int = Field(ge=1)
    method: Method = "max_covering"


class Location(BaseModel):
    h3: str
    lon: float
    lat: float
    population_gain: float


class OptimizeOut(BaseModel):
    method: Method
    k: int
    status: str
    solve_seconds: float
    locations: list[Location]
    before: Metrics
    after: Metrics
