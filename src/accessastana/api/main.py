"""FastAPI application factory.

`create_app()` takes optional overrides (sessionmaker, engine loader, report
builder), so integration tests can point the app at a test database and at a
toy engine without monkey-patching globals.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, sessionmaker

from accessastana import __version__
from accessastana.analysis.engine import CityEngine
from accessastana.api.routers import data, meta, planning, reports
from accessastana.api.services import BadRequest, EngineCache, NotFound
from accessastana.db.session import get_sessionmaker
from accessastana.settings import get_settings

log = logging.getLogger("accessastana.api")


def _default_engine_loader(maker: sessionmaker[Session]) -> Callable[[str], CityEngine]:
    from accessastana.db.repositories import load_engine

    def load(city: str) -> CityEngine:
        with maker() as s:
            return load_engine(s, city)

    return load


def _default_report_builder(database_url: str | None) -> Callable[[str, bool], Path]:
    def build(city: str, refresh: bool) -> Path:
        path = get_settings().project_root / "reports" / city / "report.pdf"
        if refresh or not path.exists():
            from accessastana.reporting.build import build_report

            build_report(city, database_url)
        return path

    return build


def create_app(
    maker: sessionmaker[Session] | None = None,
    engine_loader: Callable[[str], CityEngine] | None = None,
    report_builder: Callable[[str, bool], Path] | None = None,
    database_url: str | None = None,
) -> FastAPI:
    """Build the FastAPI app; arguments override the DB, engine loader and report builder (tests)."""
    settings = get_settings()
    app = FastAPI(
        title="AccessAstana API",
        version=__version__,
        description="Climate-adjusted walking accessibility of social infrastructure. "
        "Data © OpenStreetMap contributors (ODbL), Kontur Population (CC BY 4.0), Open-Meteo (CC BY 4.0).",
    )
    app.state.sessionmaker = maker or get_sessionmaker(database_url)
    app.state.engines = EngineCache(engine_loader or _default_engine_loader(app.state.sessionmaker))
    app.state.report_builder = report_builder or _default_report_builder(database_url)

    app.add_middleware(GZipMiddleware, minimum_size=1000)  # accessibility payloads are large, repetitive JSON
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.exception_handler(NotFound)
    async def _not_found(_: Request, exc: NotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(BadRequest)
    async def _bad_request(_: Request, exc: BadRequest) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(LookupError)
    async def _lookup(_: Request, exc: LookupError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    for r in (meta, data, planning, reports):
        app.include_router(r)
    return app


app = create_app()
