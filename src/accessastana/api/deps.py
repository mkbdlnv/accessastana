"""FastAPI dependencies (Dependency Injection: routers never construct their
own sessions or services, which makes them trivially testable)."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from accessastana.api.services import (
    AccessibilityService,
    CatalogService,
    EngineCache,
    ScenarioService,
)
from accessastana.db.session import get_sessionmaker
from accessastana.settings import get_settings


def get_session(request: Request) -> Iterator[Session]:
    maker = request.app.state.sessionmaker
    with maker() as s:
        yield s


def get_engines(request: Request) -> EngineCache:
    return request.app.state.engines


def catalog(s: Session = Depends(get_session)) -> CatalogService:
    return CatalogService(s)


def accessibility(s: Session = Depends(get_session)) -> AccessibilityService:
    return AccessibilityService(s)


def scenarios(
    s: Session = Depends(get_session), engines: EngineCache = Depends(get_engines)
) -> ScenarioService:
    st = get_settings()
    return ScenarioService(s, engines, st.scenario_max_facilities, st.optimize_max_k)


def default_sessionmaker() -> object:
    return get_sessionmaker()
