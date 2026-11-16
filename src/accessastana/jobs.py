"""Batch analysis jobs (offline): compute and persist results.

These are the "heavy preprocessing" steps. The server only reads their output,
plus on-demand scenario/optimisation computations.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import numpy as np
from sqlalchemy import delete

from accessastana.config import load_categories, load_seasons
from accessastana.db.models import AccessibilityResult
from accessastana.db.repositories import load_engine
from accessastana.db.session import session_scope
from accessastana.ingestion.base import bulk_insert

log = logging.getLogger(__name__)


def run_accessibility(slug: str, database_url: str | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    seasons = load_seasons()
    with session_scope(database_url) as s:
        engine = load_engine(s, slug)
        log.info(
            "engine loaded: %d nodes, %d cells (%.1fs)",
            engine.graph.n,
            len(engine.cells),
            time.perf_counter() - t0,
        )
        s.execute(delete(AccessibilityResult).where(AccessibilityResult.city_slug == slug))
        records: list[dict[str, Any]] = []
        summary: dict[str, Any] = {}
        for cat in load_categories():
            _dist, fac = engine.baseline(cat)
            for season in seasons.api_seasons:
                prof = seasons.profiles[season]
                mins = engine.minutes(cat, season)
                records += [
                    {
                        "city_slug": slug,
                        "h3": h,
                        "category": cat,
                        "season": season,
                        "minutes": round(float(m), 2) if np.isfinite(m) else None,
                        "reachable": bool(m <= prof.max_minutes),
                        "nearest_poi_id": int(f) if f >= 0 else None,
                    }
                    for h, m, f in zip(engine.cells["h3"], mins, fac, strict=True)
                ]
                pop = engine.population
                summary[f"{cat}/{season}"] = round(float(pop[mins <= prof.max_minutes].sum() / pop.sum()), 3)
        bulk_insert(s, AccessibilityResult.__table__, records)  # type: ignore[arg-type]
    summary["_seconds"] = round(time.perf_counter() - t0, 1)
    return {"share_of_population_reachable": summary}
