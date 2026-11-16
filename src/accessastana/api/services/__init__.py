"""Services: business logic between routers (HTTP) and repositories (SQL)."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from accessastana.analysis.accessibility import composite_index, summarize_groups
from accessastana.analysis.engine import CityEngine
from accessastana.api import schemas as S
from accessastana.api.repositories import (
    AccessibilityRepository,
    CityRepository,
)
from accessastana.config import load_categories, load_city, load_seasons
from accessastana.db.models import Scenario, ScenarioFacility

ATTRIBUTION = [
    "© OpenStreetMap contributors (ODbL)",
    "Population: Kontur Population (CC BY 4.0), calibrated to official totals of the Bureau of National Statistics RK",
    "Weather data by Open-Meteo.com (CC BY 4.0)",
]
INDEX = "index"


class NotFound(LookupError):
    """Unknown city/category/season → HTTP 404."""


class BadRequest(ValueError):
    """Invalid combination of parameters → HTTP 422."""


def check(
    city: str | None = None, category: str | None = None, season: str | None = None, allow_index: bool = False
) -> None:
    from accessastana.config import list_city_slugs

    if city is not None and city not in list_city_slugs():
        raise NotFound(f"unknown city {city!r}")
    if category is not None and category not in load_categories() and not (allow_index and category == INDEX):
        raise NotFound(f"unknown category {category!r}")
    if season is not None and season not in load_seasons().api_seasons:
        raise NotFound(f"unknown season {season!r}")


# --------------------------------------------------------------------------- catalog
class CatalogService:
    def __init__(self, session: Session) -> None:
        self.cities = CityRepository(session)

    def list_cities(self) -> list[S.CityOut]:
        out = []
        for slug in self.cities.all_slugs():
            cfg, row = load_city(slug), self.cities.get(slug) or {}
            out.append(
                S.CityOut(
                    slug=slug,
                    name=cfg.name,
                    center=cfg.map_center,
                    h3_resolution=cfg.h3_resolution,
                    population_total=row.get("population_total"),
                    attribution=ATTRIBUTION,
                )
            )
        return out

    @staticmethod
    def list_categories() -> list[S.CategoryOut]:
        return [S.CategoryOut(key=k, label=c.label) for k, c in load_categories().items()]

    def list_seasons(self, city: str) -> list[S.SeasonOut]:
        check(city=city)
        cfg, shares = load_seasons(), self.cities.climate_shares(city)
        return [
            S.SeasonOut(
                key=k,
                label=cfg.profiles[k].label,
                speed_mps=cfg.profiles[k].speed_mps,
                max_minutes=cfg.profiles[k].max_minutes,
                share_of_days=shares.get(k),
            )
            for k in cfg.api_seasons
        ]


# --------------------------------------------------------------------------- accessibility
class AccessibilityService:
    def __init__(self, session: Session) -> None:
        self.repo = AccessibilityRepository(session)
        self.cities = CityRepository(session)

    def _wide(self, city: str, season: str) -> pd.DataFrame:
        """One row per cell, one minutes column per category (NaN → inf)."""
        cats = list(load_categories())
        long = self.repo.cells(city, season, cats)
        if long.empty:
            raise NotFound(f"no accessibility results for {city}/{season}; run `accessastana analyze`")
        wide = long.pivot_table(
            index="h3", columns="category", values="minutes", aggfunc="first", dropna=False
        )
        wide = wide.reindex(columns=cats).astype(float).fillna(np.inf)
        meta = long.drop_duplicates("h3").set_index("h3")[["population", "district_id", "district"]]
        return meta.join(wide)

    def accessibility(self, city: str, category: str, season: str) -> S.AccessibilityOut:
        check(city, category, season, allow_index=True)
        prof = load_seasons().profiles[season]
        if category == INDEX:
            wide = self._wide(city, season)
            idx = composite_index(wide[list(load_categories())], prof.max_minutes)
            cells = [
                S.CellValue(h3=h, value=round(float(v), 3), reachable=bool(v >= 0.999), population=float(p))
                for h, v, p in zip(wide.index, idx, wide["population"], strict=True)
            ]
            metric = "index"
        else:
            long = self.repo.cells(city, season, [category])
            if long.empty:
                raise NotFound(f"no results for {city}/{category}/{season}")
            cells = [
                S.CellValue(
                    h3=r.h3,
                    value=None if pd.isna(r.minutes) else float(r.minutes),
                    reachable=bool(r.reachable),
                    population=float(r.population),
                )
                for r in long.itertuples()
            ]
            metric = "minutes"
        return S.AccessibilityOut(
            city=city,
            category=category,
            season=season,
            metric=metric,  # type: ignore[arg-type]
            max_minutes=prof.max_minutes,
            cells=cells,
        )

    def as_geojson(self, out: S.AccessibilityOut) -> dict[str, Any]:
        import json

        geoms = self.repo.cells_geojson(out.city)
        return {
            "type": "FeatureCollection",
            "properties": {"metric": out.metric, "max_minutes": out.max_minutes},
            "features": [
                {"type": "Feature", "geometry": json.loads(geoms[c.h3]), "properties": c.model_dump()}
                for c in out.cells
                if c.h3 in geoms
            ],
        }

    def district_summary(self, city: str, season: str) -> S.DistrictsSummaryOut:
        check(city=city, season=season)
        seasons = load_seasons()
        prof, thresholds = seasons.profiles[season], seasons.summary_thresholds
        cats = list(load_categories())
        wide = self._wide(city, season)
        wide["index"] = composite_index(wide[cats], prof.max_minutes)
        wide["district"] = wide["district"].fillna("—")
        by_d = summarize_groups(wide, cats, thresholds, prof.max_minutes, "district")
        ids = wide.drop_duplicates("district").set_index("district")["district_id"]
        total = summarize_groups(wide.assign(all="city"), cats, thresholds, prof.max_minutes, "all")
        city_name = (self.cities.get(city) or {}).get("name_en", city)

        def row(r: pd.Series, name: str, did: Any) -> S.DistrictSummary:
            return S.DistrictSummary(
                id=None if did is None or pd.isna(did) else int(did),
                name=name,
                population=float(r["population"]),
                index=None if r["index"] is None or pd.isna(r["index"]) else round(float(r["index"]), 4),
                categories={
                    c: S.CategorySummary(
                        share_within={
                            str(int(t)): round(float(r[f"{c}__within_{int(t)}"]), 4) for t in thresholds
                        },
                        share_reachable=round(float(r[f"{c}__reachable"]), 4),
                        mean_minutes=None
                        if pd.isna(r[f"{c}__mean_minutes"])
                        else round(float(r[f"{c}__mean_minutes"]), 2),
                    )
                    for c in cats
                },
            )

        # Cells outside every district polygon (border slivers) count only in the city total.
        districts = [
            row(r, str(r["district"]), ids.get(r["district"]))
            for _, r in by_d.iterrows()
            if r["district"] != "—"
        ]
        return S.DistrictsSummaryOut(
            city=city,
            season=season,
            thresholds=thresholds,
            districts=sorted(districts, key=lambda d: d.name),
            city_total=row(total.iloc[0], city_name, None),
        )


class EngineCache:
    """Keeps one CityEngine per city in memory (loading takes ~1 s and the
    graph is read-only, so sharing it between requests is safe). Engines
    are built lazily on first use; `loader` is injected for tests."""

    def __init__(self, loader: Callable[[str], CityEngine]) -> None:
        self._loader = loader
        self._engines: dict[str, CityEngine] = {}
        self._lock = threading.Lock()

    def get(self, city: str) -> CityEngine:
        with self._lock:
            if city not in self._engines:
                self._engines[city] = self._loader(city)
            return self._engines[city]

    def put(self, city: str, engine: CityEngine) -> None:
        self._engines[city] = engine


class ScenarioService:
    def __init__(self, session: Session, engines: EngineCache, max_facilities: int, max_k: int) -> None:
        self.session, self.engines = session, engines
        self.max_facilities, self.max_k = max_facilities, max_k

    def run(self, req: S.ScenarioIn) -> S.ScenarioOut:
        check(req.city, req.category, req.season)
        if len(req.add) + len(req.remove) > self.max_facilities:
            raise BadRequest(f"at most {self.max_facilities} added/removed facilities per scenario")
        engine = self.engines.get(req.city)
        res = engine.scenario(req.category, req.season, [(f.lon, f.lat) for f in req.add], req.remove)
        scenario_id = None
        if req.save:
            sc = Scenario(
                city_slug=req.city,
                name=req.name,
                category=req.category,
                season=req.season,
                result={"before": res["before"], "after": res["after"]},
            )
            self.session.add(sc)
            self.session.flush()
            for f in req.add:
                self.session.add(
                    ScenarioFacility(
                        scenario_id=sc.id, action="add", geometry=f"SRID=4326;POINT({f.lon} {f.lat})"
                    )
                )
            for pid in req.remove:
                self.session.add(ScenarioFacility(scenario_id=sc.id, action="remove", poi_id=pid))
            self.session.commit()
            scenario_id = sc.id
        return S.ScenarioOut(
            scenario_id=scenario_id,
            before=S.Metrics(**res["before"]),
            after=S.Metrics(**res["after"]),
            changed_cells=[S.ChangedCell(**c) for c in res["changed_cells"]],
        )

    def optimize(self, req: S.OptimizeIn) -> S.OptimizeOut:
        check(req.city, req.category, req.season)
        if req.k > self.max_k:
            raise BadRequest(f"k must be <= {self.max_k}")
        res = self.engines.get(req.city).optimize(req.category, req.season, req.k, req.method)
        return S.OptimizeOut(**res)
