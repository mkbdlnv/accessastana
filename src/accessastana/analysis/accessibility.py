"""Walking accessibility from H3 cells to the nearest facility of a category.

Model (explicit assumptions, stated in the paper):
- Origin = H3 cell centroid; destination = facility point (for parks, many
  points along the park boundary — see ingestion/osm_pois.py).
- Walk distance = straight line centroid→nearest graph node
                + network shortest path
                + straight line nearest graph node→facility.
  The straight-line connectors approximate the walk inside a block.
- Cells farther than MAX_SNAP_M from any walkable way (river, rail yards)
  get no value: their centroid is not a place where people live.
- Routing is cut off at ROUTING_CUTOFF_M; anything beyond counts as
  "unreachable" (minutes = None) for every season profile.
- Time = distance / speed (season profile). Slope is ignored: Astana is flat.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from accessastana.analysis.graph import WalkGraph

MAX_SNAP_M = 600.0
# 60 min at the slowest profile speed (1.10 m/s) ≈ 4 km; 6 km is a safe cap.
ROUTING_CUTOFF_M = 6000.0


@dataclass(frozen=True)
class Destinations:
    """Destination points. Several points may belong to one facility."""

    facility_ids: np.ndarray  # (m,) int
    xy: np.ndarray  # (m, 2) metric

    def without(self, removed: Sequence[int]) -> Destinations:
        """Copy without the given facility ids (all their destination points)."""
        keep = ~np.isin(self.facility_ids, np.asarray(list(removed), dtype=self.facility_ids.dtype))
        return Destinations(self.facility_ids[keep], self.xy[keep])

    def plus(self, ids: np.ndarray, xy: np.ndarray) -> Destinations:
        """Copy with extra destination points appended (ids may repeat for multi-point facilities)."""
        return Destinations(np.concatenate([self.facility_ids, ids]), np.vstack([self.xy, xy]))

    def __len__(self) -> int:
        return int(self.facility_ids.shape[0])


def nearest_facility(
    graph: WalkGraph, cells_xy: np.ndarray, dest: Destinations, limit_m: float = ROUTING_CUTOFF_M
) -> tuple[np.ndarray, np.ndarray]:
    """Walking distance (m) from each cell to its nearest facility, and that
    facility's id. Unreachable → (inf, -1)."""
    c_node, c_snap = graph.snap(cells_xy)
    if len(dest) == 0:
        return np.full(len(cells_xy), np.inf), np.full(len(cells_xy), -1)
    d_node, d_snap = graph.snap(dest.xy)
    node_dist, src = graph.multi_source(d_node, d_snap, limit=limit_m)
    dist = node_dist[c_node] + c_snap
    fac = np.where(src[c_node] >= 0, dest.facility_ids[np.clip(src[c_node], 0, None)], -1)
    bad = (c_snap > MAX_SNAP_M) | ~np.isfinite(dist) | (dist > limit_m)
    dist[bad] = np.inf
    fac[bad] = -1
    return dist, fac


def to_minutes(distance_m: np.ndarray, speed_mps: float) -> np.ndarray:
    """Metres → minutes; inf stays inf (unreachable)."""
    return np.asarray(distance_m, dtype=float) / speed_mps / 60.0


def share_within(minutes: np.ndarray, population: np.ndarray, threshold: float) -> float:
    """Population-weighted share of residents within `threshold` minutes."""
    total = float(np.sum(population))
    if total <= 0:
        return 0.0
    return float(np.sum(population[np.asarray(minutes) <= threshold]) / total)


def mean_minutes(minutes: np.ndarray, population: np.ndarray) -> float | None:
    """Population-weighted mean over residents WITH a reachable facility."""
    m = np.asarray(minutes)
    ok = np.isfinite(m) & (population > 0)
    if not ok.any():
        return None
    return float(np.average(m[ok], weights=population[ok]))


def metrics(minutes: np.ndarray, population: np.ndarray, max_minutes: float) -> dict[str, float | None]:
    """Headline metrics used by summaries, scenarios and optimisation."""
    reach = np.asarray(minutes) <= max_minutes
    return {
        "population_reachable": float(np.sum(population[reach])),
        "share_reachable": share_within(minutes, population, max_minutes),
        "mean_minutes": mean_minutes(minutes, population),
    }


def threshold_sensitivity(
    minutes: np.ndarray, population: np.ndarray, thresholds: Sequence[float]
) -> dict[float, float]:
    """Share of residents within each candidate acceptable time.

    Used to test how strongly a conclusion depends on an ASSUMED threshold
    (e.g. 8 / 10 / 12 min on severe-cold days, config/seasons.yaml). Walking
    speed stays fixed; only the acceptable time changes.
    """
    return {float(t): share_within(minutes, population, t) for t in thresholds}


def composite_index(
    minutes_by_category: pd.DataFrame, max_minutes: float, weights: Mapping[str, float] | None = None
) -> pd.Series:
    """15-minute index of a cell = weighted share of categories reachable
    within `max_minutes` (equal weights by default) → value in [0, 1].

    Equal weights are a deliberate, transparent default (as in Moreno et al.'s
    "15-minute city" concept, every essential function counts); the weights
    can be changed for sensitivity analysis.
    """
    cols = list(minutes_by_category.columns)
    w = pd.Series({c: (weights or {}).get(c, 1.0) for c in cols}, dtype=float)
    reach = (minutes_by_category <= max_minutes).astype(float)
    return (reach * w).sum(axis=1) / w.sum()


def summarize_groups(
    df: pd.DataFrame,
    categories: Sequence[str],
    thresholds: Sequence[float],
    max_minutes: float,
    group: str = "district",
) -> pd.DataFrame:
    """Per-group (district) table: population, index, and per category the
    population shares within each threshold + mean minutes.

    `df` columns: group, population, index, and one minutes column per category.
    """
    rows = []
    for name, g in df.groupby(group, dropna=False):
        pop = g["population"].to_numpy()
        row: dict[str, object] = {group: name, "population": float(pop.sum())}
        row["index"] = float(np.average(g["index"], weights=pop)) if pop.sum() > 0 else None
        for c in categories:
            m = g[c].to_numpy()
            for t in thresholds:
                row[f"{c}__within_{int(t)}"] = share_within(m, pop, t)
            row[f"{c}__reachable"] = share_within(m, pop, max_minutes)
            row[f"{c}__mean_minutes"] = mean_minutes(m, pop)
        rows.append(row)
    return pd.DataFrame(rows)
