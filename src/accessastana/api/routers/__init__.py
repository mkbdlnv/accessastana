"""HTTP routers: parse/validate requests and delegate to services. No SQL here."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from accessastana.api import deps
from accessastana.api import schemas as S
from accessastana.api.repositories import CityRepository, PoiRepository
from accessastana.api.services import (
    AccessibilityService,
    CatalogService,
    ScenarioService,
    check,
)

meta = APIRouter(tags=["meta"])
data = APIRouter(tags=["accessibility"])
planning = APIRouter(tags=["planning"])
reports = APIRouter(tags=["reports"])


@meta.get("/health", response_model=S.Health)
def health(s: Session = Depends(deps.get_session)) -> Any:
    """Liveness and database check; 503 when the database is unreachable."""
    try:
        s.execute(text("SELECT 1"))
        return S.Health(status="ok", db="ok")
    except Exception:
        return JSONResponse(status_code=503, content={"status": "degraded", "db": "error"})


@meta.get("/cities", response_model=list[S.CityOut])
def cities(svc: CatalogService = Depends(deps.catalog)) -> Any:
    """Cities with map centre, population total and required data attribution."""
    return svc.list_cities()


@meta.get("/categories", response_model=list[S.CategoryOut])
def categories() -> Any:
    """Facility categories (config/categories.yaml)."""
    return CatalogService.list_categories()


@meta.get("/seasons", response_model=list[S.SeasonOut])
def seasons(city: str = "astana", svc: CatalogService = Depends(deps.catalog)) -> Any:
    """Season profiles: walking speed, acceptable minutes and share of winter days."""
    return svc.list_seasons(city)


@data.get("/accessibility", response_model=None)
def accessibility(
    city: str,
    category: str,
    season: str,
    format: Literal["json", "geojson"] = "json",
    svc: AccessibilityService = Depends(deps.accessibility),
) -> Any:
    """Walking minutes (or the 15-minute index) per H3 cell, as JSON or GeoJSON."""
    out = svc.accessibility(city, category, season)
    return svc.as_geojson(out) if format == "geojson" else out


@data.get("/districts/summary", response_model=S.DistrictsSummaryOut)
def districts_summary(city: str, season: str, svc: AccessibilityService = Depends(deps.accessibility)) -> Any:
    """Population shares within 5/10/15 min and the 15-minute index per district."""
    return svc.district_summary(city, season)


@data.get("/districts")
def districts(city: str, s: Session = Depends(deps.get_session)) -> Any:
    """District boundaries as GeoJSON."""
    check(city=city)
    return CityRepository(s).districts_geojson(city)


@data.get("/pois")
def pois(
    city: str,
    category: str | None = None,
    s: Session = Depends(deps.get_session),
) -> Any:
    """OSM facility points as GeoJSON (their ids can be removed in scenarios)."""
    check(city=city, category=category)
    return PoiRepository(s).geojson(city, category)


@planning.post("/scenarios", response_model=S.ScenarioOut)
def scenario(req: S.ScenarioIn, svc: ScenarioService = Depends(deps.scenarios)) -> Any:
    """What-if: add and/or remove facilities and get before/after metrics."""
    return svc.run(req)


@planning.post("/optimize", response_model=S.OptimizeOut)
def optimize(req: S.OptimizeIn, svc: ScenarioService = Depends(deps.scenarios)) -> Any:
    """Recommend k new facility locations (maximal covering or p-median)."""
    return svc.optimize(req)


@reports.get("/reports/{city}.pdf", response_class=FileResponse)
def report_pdf(city: str, request: Request, refresh: bool = Query(False)) -> Any:
    """Serve reports/<city>/report.pdf; build it on first request (or refresh=true)."""
    check(city=city)
    builder = request.app.state.report_builder
    path = builder(city, refresh)
    return FileResponse(path, media_type="application/pdf", filename=f"accessastana-{city}.pdf")
