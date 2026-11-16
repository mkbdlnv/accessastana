"""Scenario recomputation and facility-location models on toy instances."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from accessastana.analysis.accessibility import Destinations, nearest_facility
from accessastana.analysis.engine import CityEngine
from accessastana.analysis.location import maximal_covering, p_median
from accessastana.analysis.scenarios import apply_scenario
from accessastana.config import SeasonProfile
from tests.conftest import grid_graph


def _random_setup(rng: np.random.Generator):  # type: ignore[no-untyped-def]
    g = grid_graph(12, 80.0)
    cells = rng.uniform(0, 880, size=(60, 2))
    dest = Destinations(np.arange(1, 6), rng.uniform(0, 880, size=(5, 2)))
    return g, cells, dest


def test_incremental_scenario_equals_full_recompute(rng: np.random.Generator) -> None:
    g, cells, dest = _random_setup(rng)
    base_d, base_f = nearest_facility(g, cells, dest)
    add = rng.uniform(0, 880, size=(2, 2))
    out = apply_scenario(g, cells, dest, base_d, base_f, add_xy=add, remove_ids=[2, 4])
    # Full recomputation from scratch with the modified facility set:
    full_dest = dest.without([2, 4]).plus(np.array([-1000, -1001]), add)
    full_d, full_f = nearest_facility(g, cells, full_dest)
    np.testing.assert_allclose(out.distance_m, full_d)
    np.testing.assert_array_equal(out.facility, full_f)
    assert out.recomputed_cells <= len(cells)


def test_scenario_noop_changes_nothing(rng: np.random.Generator) -> None:
    g, cells, dest = _random_setup(rng)
    base_d, base_f = nearest_facility(g, cells, dest)
    out = apply_scenario(g, cells, dest, base_d, base_f)
    assert not out.changed.any() and out.recomputed_cells == 0


def test_remove_all_makes_unreachable(rng: np.random.Generator) -> None:
    g, cells, dest = _random_setup(rng)
    base_d, base_f = nearest_facility(g, cells, dest)
    out = apply_scenario(g, cells, dest, base_d, base_f, remove_ids=list(range(1, 6)))
    assert np.isinf(out.distance_m).all() and out.changed.all()


def test_maximal_covering_picks_the_heavier_cluster() -> None:
    # 4 demand cells, 3 candidates. Candidate 0 covers cells 0,1 (pop 10+10),
    # candidate 1 covers cell 2 (pop 50), candidate 2 covers cell 3 (pop 5).
    w = np.array([10.0, 10.0, 50.0, 5.0])
    d = np.array([[5, 30, 30], [5, 30, 30], [30, 5, 30], [30, 30, 5]], dtype=float)
    existing = np.full(4, np.inf)
    s1 = maximal_covering(w, d, existing, k=1, threshold=15)
    assert s1.chosen == [1] and s1.objective == pytest.approx(50) and s1.status == "Optimal"
    s2 = maximal_covering(w, d, existing, k=2, threshold=15)
    assert sorted(s2.chosen) == [0, 1] and s2.objective == pytest.approx(70)


def test_maximal_covering_ignores_already_covered_demand() -> None:
    w = np.array([100.0, 1.0])
    d = np.array([[5.0, 30.0], [30.0, 5.0]])
    existing = np.array([3.0, np.inf])  # cell 0 is already covered
    s = maximal_covering(w, d, existing, k=1, threshold=15)
    assert s.chosen == [1]


def test_p_median_known_optimum() -> None:
    # Line of 3 cells with pop 1, 1, 10; candidates at each cell.
    w = np.array([1.0, 1.0, 10.0])
    d = np.array([[0, 10, 20], [10, 0, 10], [20, 10, 0]], dtype=float)
    s = p_median(w, d, np.full(3, np.inf), k=1, cap_minutes=60)
    # site 2: 1*20 + 1*10 + 0 = 30 ; site 1: 10 + 0 + 100 = 110 → site 2
    assert s.chosen == [2] and s.objective == pytest.approx(30)
    # With an existing facility next to cell 0 (e=1), the new site still goes to cell 2.
    s2 = p_median(w, d, np.array([1.0, 11.0, 21.0]), k=1)
    assert s2.chosen == [2] and s2.objective == pytest.approx(1 + 10 + 0)


def test_p_median_k_larger_than_candidates() -> None:
    s = p_median(np.array([1.0]), np.array([[2.0]]), np.array([np.inf]), k=5)
    assert s.chosen == [0]


def _toy_engine() -> CityEngine:
    g = grid_graph(10, 100.0)
    xs, ys = np.meshgrid(np.arange(0, 1000, 250.0), np.arange(0, 1000, 250.0))
    cells = pd.DataFrame(
        {
            "h3": [f"c{i}" for i in range(xs.size)],
            "x": xs.ravel(),
            "y": ys.ravel(),
            "population": 100.0,
            "district_id": 1,
        }
    )
    cells["lon"], cells["lat"] = 0.0, 0.0
    dests = {"school": Destinations(np.array([1]), np.array([[0.0, 0.0]]))}
    profiles = {"summer": SeasonProfile(label="s", months=[6], speed_mps=1.0, max_minutes=10)}
    e = CityEngine("toy", "EPSG:32642", g, cells, dests, profiles)
    # lon/lat of cells consistent with the metric CRS (needed for optimisation output)
    lon, lat = e._to_wgs.transform(cells.x.to_numpy(), cells.y.to_numpy())
    e.cells["lon"], e.cells["lat"] = lon, lat
    return e


def test_engine_scenario_and_optimize() -> None:
    e = _toy_engine()
    base = e.minutes("school", "summer")
    assert base[0] == pytest.approx(0, abs=0.01)
    far = int(np.argmax(base))
    res = e.scenario("school", "summer", add_lonlat=[e.cells[["lon", "lat"]].to_numpy()[far].tolist()])
    assert res["after"]["share_reachable"] > res["before"]["share_reachable"]
    assert any(c["h3"] == f"c{far}" for c in res["changed_cells"])

    opt = e.optimize("school", "summer", k=2, method="max_covering")
    assert opt["status"] == "Optimal" and opt["k"] == 2
    assert opt["after"]["population_reachable"] >= opt["before"]["population_reachable"]
    gain = sum(loc["population_gain"] for loc in opt["locations"])
    assert gain == pytest.approx(opt["after"]["population_reachable"] - opt["before"]["population_reachable"])

    pm = e.optimize("school", "summer", k=1, method="p_median")
    assert pm["after"]["mean_minutes"] < pm["before"]["mean_minutes"]
    with pytest.raises(ValueError):
        e.optimize("school", "summer", k=1, method="nope")
    with pytest.raises(KeyError):
        e.minutes("school", "monsoon")
    with pytest.raises(KeyError):
        e.dest("hospital")
