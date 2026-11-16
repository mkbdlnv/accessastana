"""CityEngine: in-memory model of one city (graph + cells + facilities).

Facade pattern: the API services and the batch jobs talk to this one object
instead of wiring graph/accessibility/scenario/location modules themselves.
The engine is built from plain DataFrames (see db/repositories.py), so it has
no database dependency and can be constructed in tests from toy data.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from pyproj import Transformer

from accessastana.analysis.accessibility import (
    ROUTING_CUTOFF_M,
    Destinations,
    metrics,
    nearest_facility,
    to_minutes,
)
from accessastana.analysis.graph import WalkGraph
from accessastana.analysis.location import LocationSolution, maximal_covering, p_median
from accessastana.analysis.scenarios import apply_scenario
from accessastana.config import SeasonProfile


@dataclass
class CityEngine:
    """In-memory model of one city; see the module docstring."""

    slug: str
    metric_crs: str
    graph: WalkGraph
    cells: pd.DataFrame  # h3, x, y (metric), lon, lat, population, district_id
    destinations: dict[str, Destinations]  # category → destination points
    profiles: dict[str, SeasonProfile]
    _baseline: dict[str, tuple[np.ndarray, np.ndarray]] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self._to_metric = Transformer.from_crs(4326, self.metric_crs, always_xy=True)
        self._to_wgs = Transformer.from_crs(self.metric_crs, 4326, always_xy=True)

    # ---- helpers ------------------------------------------------------------
    @property
    def cells_xy(self) -> np.ndarray:
        """Cell centroids in the metric CRS, shape (n_cells, 2)."""
        return self.cells[["x", "y"]].to_numpy(float)

    @property
    def population(self) -> np.ndarray:
        """Calibrated population per cell, shape (n_cells,)."""
        return self.cells["population"].to_numpy(float)

    def lonlat_to_xy(self, lonlat: Sequence[Sequence[float]]) -> np.ndarray:
        """WGS84 lon/lat pairs → metric x/y, shape (n, 2)."""
        if not len(lonlat):
            return np.empty((0, 2))
        arr = np.asarray(lonlat, float)
        x, y = self._to_metric.transform(arr[:, 0], arr[:, 1])
        return np.column_stack([x, y])

    def profile(self, season: str) -> SeasonProfile:
        """Season profile by key; KeyError for an unknown season."""
        if season not in self.profiles:
            raise KeyError(f"unknown season {season!r}")
        return self.profiles[season]

    def dest(self, category: str) -> Destinations:
        """Destination points of a category; KeyError for an unknown category."""
        if category not in self.destinations:
            raise KeyError(f"unknown category {category!r}")
        return self.destinations[category]

    # ---- accessibility ------------------------------------------------------
    def baseline(self, category: str) -> tuple[np.ndarray, np.ndarray]:
        """(distance_m, nearest facility id) per cell — cached per category."""
        if category not in self._baseline:
            self._baseline[category] = nearest_facility(self.graph, self.cells_xy, self.dest(category))
        return self._baseline[category]

    def minutes(self, category: str, season: str) -> np.ndarray:
        """Walking minutes per cell to the nearest facility for a category and season."""
        return to_minutes(self.baseline(category)[0], self.profile(season).speed_mps)

    # ---- scenarios ----------------------------------------------------------
    def _scenario_arrays(
        self, category: str, season: str, add_lonlat: Sequence[Sequence[float]], remove_ids: Sequence[int]
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]:
        """(before_min, after_min, facility_after, changed_mask, recomputed)."""
        prof = self.profile(season)
        base_d, base_f = self.baseline(category)
        out = apply_scenario(
            self.graph,
            self.cells_xy,
            self.dest(category),
            base_d,
            base_f,
            add_xy=self.lonlat_to_xy(add_lonlat),
            remove_ids=remove_ids,
        )
        before = to_minutes(base_d, prof.speed_mps)
        after = to_minutes(out.distance_m, prof.speed_mps)
        return before, after, out.facility, out.changed, out.recomputed_cells

    def scenario(
        self,
        category: str,
        season: str,
        add_lonlat: Sequence[Sequence[float]] = (),
        remove_ids: Sequence[int] = (),
    ) -> dict[str, Any]:
        """Before/after metrics and changed cells for added/removed facilities."""
        prof = self.profile(season)
        before, after, _fac, changed, recomputed = self._scenario_arrays(
            category, season, add_lonlat, remove_ids
        )
        return {
            "before": metrics(before, self.population, prof.max_minutes),
            "after": metrics(after, self.population, prof.max_minutes),
            "changed_cells": [
                {
                    "h3": self.cells["h3"].iat[i],
                    "before": _f(before[i]),
                    "after": _f(after[i]),
                    "reachable_after": bool(after[i] <= prof.max_minutes),
                }
                for i in np.flatnonzero(changed)
            ],
            "recomputed_cells": recomputed,
        }

    # ---- optimisation -------------------------------------------------------
    def candidate_matrix(self, speed_mps: float, limit_m: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Demand cells (populated) × candidate sites (same cells), in minutes."""
        node, snap = self.graph.snap(self.cells_xy)
        demand = np.flatnonzero((self.population > 0) & (snap <= 600))
        cand = demand  # candidate sites = populated cell centroids
        net = self.graph.distances_from(node[cand], node[demand], limit=limit_m)  # (m, n)
        d_m = net.T + snap[demand][:, None] + snap[cand][None, :]
        return demand, cand, to_minutes(d_m, speed_mps)

    def optimize(self, category: str, season: str, k: int, method: str = "max_covering") -> dict[str, Any]:
        """Recommend k new sites (MCLP or p-median) and evaluate them as a scenario."""
        prof = self.profile(season)
        cap_minutes = 60.0
        limit_m = (prof.max_minutes if method == "max_covering" else cap_minutes) * 60 * prof.speed_mps
        demand, cand, d = self.candidate_matrix(prof.speed_mps, min(limit_m, ROUTING_CUTOFF_M))
        existing = self.minutes(category, season)[demand]
        w = self.population[demand]
        sol: LocationSolution
        if method == "max_covering":
            sol = maximal_covering(w, d, existing, k, prof.max_minutes)
        elif method == "p_median":
            sol = p_median(w, d, existing, k, cap_minutes=cap_minutes)
        else:
            raise ValueError("method must be max_covering or p_median")
        chosen_cells = cand[sol.chosen]
        lonlat = self.cells[["lon", "lat"]].to_numpy(float)[chosen_cells]
        before, after, fac_after, _changed, _n = self._scenario_arrays(category, season, lonlat.tolist(), ())
        # Population that NEWLY gets a facility within the threshold, credited to
        # the new site that is now nearest (new ids are -1000, -1001, ...).
        newly = (before > prof.max_minutes) & (after <= prof.max_minutes)
        site = -1000 - fac_after
        gains = np.bincount(site[newly], weights=self.population[newly], minlength=len(chosen_cells))
        return {
            "method": method,
            "k": len(chosen_cells),
            "status": sol.status,
            "solve_seconds": round(sol.solve_seconds, 3),
            "locations": [
                {
                    "h3": self.cells["h3"].iat[c],
                    "lon": float(lonlat[n, 0]),
                    "lat": float(lonlat[n, 1]),
                    "population_gain": float(gains[n]),
                }
                for n, c in enumerate(chosen_cells)
            ],
            "before": metrics(before, self.population, prof.max_minutes),
            "after": metrics(after, self.population, prof.max_minutes),
        }


def _f(v: float) -> float | None:
    return round(float(v), 2) if np.isfinite(v) else None
