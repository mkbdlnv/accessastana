"""What-if scenarios: add/remove facilities and recompute ONLY affected cells.

Given the baseline (distance to nearest facility + which facility) per cell:
- Removing facilities: only cells whose nearest facility was removed can get
  worse. For those cells we rerun the multi-source search from the remaining
  facilities; every other cell keeps its value (its nearest facility still
  exists, and removing others cannot make it closer).
- Adding facilities: a cell improves iff the new facility is closer than its
  current one, so one multi-source search from the NEW points only, limited
  to the routing cutoff, plus an element-wise minimum, is exact.
Both rules give exactly the same result as a full recomputation. A unit
test asserts this.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from accessastana.analysis.accessibility import ROUTING_CUTOFF_M, Destinations, nearest_facility
from accessastana.analysis.graph import WalkGraph


@dataclass
class ScenarioOutcome:
    distance_m: np.ndarray
    facility: np.ndarray
    changed: np.ndarray  # bool mask of cells whose distance changed
    recomputed_cells: int  # how many cells needed a new search (for reporting)


def apply_scenario(
    graph: WalkGraph,
    cells_xy: np.ndarray,
    dest: Destinations,
    base_dist: np.ndarray,
    base_fac: np.ndarray,
    add_xy: np.ndarray | None = None,
    remove_ids: Sequence[int] = (),
    new_id_start: int = -1000,
    limit_m: float = ROUTING_CUTOFF_M,
) -> ScenarioOutcome:
    dist, fac = base_dist.copy(), base_fac.copy()
    recomputed = 0
    remaining = dest
    if len(remove_ids):
        remaining = dest.without(remove_ids)
        affected = np.isin(fac, np.asarray(list(remove_ids)))
        if affected.any():
            d2, f2 = nearest_facility(graph, cells_xy[affected], remaining, limit_m)
            dist[affected], fac[affected] = d2, f2
            recomputed += int(affected.sum())
    if add_xy is not None and len(add_xy):
        # New facilities get negative ids so they never clash with DB ids.
        ids = np.arange(new_id_start, new_id_start - len(add_xy), -1)
        d3, f3 = nearest_facility(graph, cells_xy, Destinations(ids, np.asarray(add_xy, float)), limit_m)
        better = d3 < dist
        dist[better], fac[better] = d3[better], f3[better]
        recomputed += int(better.sum())
    changed = ~np.isclose(dist, base_dist, equal_nan=True) & ~(np.isinf(dist) & np.isinf(base_dist))
    return ScenarioOutcome(dist, fac, changed, recomputed)
