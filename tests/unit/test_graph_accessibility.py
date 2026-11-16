"""Shortest paths and accessibility on synthetic graphs with known answers."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from accessastana.analysis.accessibility import (
    MAX_SNAP_M,
    Destinations,
    composite_index,
    mean_minutes,
    metrics,
    nearest_facility,
    share_within,
    summarize_groups,
    to_minutes,
)
from accessastana.analysis.graph import WalkGraph
from tests.conftest import grid_graph


def test_grid_shortest_path_is_manhattan(grid: WalkGraph) -> None:
    # 5x5 grid, spacing 100: from (0,0) to (4,4) = 8 edges = 800 m
    d = grid.distances_from(np.array([0]), np.arange(grid.n))
    assert d[0, 24] == pytest.approx(800)
    assert d[0, 12] == pytest.approx(400)


def test_parallel_edges_keep_shortest() -> None:
    nodes = pd.DataFrame({"id": [1, 2], "x": [0.0, 100.0], "y": [0.0, 0.0]})
    edges = pd.DataFrame({"u": [1, 2, 1], "v": [2, 1, 2], "length_m": [300.0, 120.0, 500.0]})
    g = WalkGraph.from_tables(nodes, edges)
    assert g.distances_from(np.array([0]), np.array([1]))[0, 0] == pytest.approx(120)


def test_edges_to_unknown_nodes_and_self_loops_are_ignored() -> None:
    nodes = pd.DataFrame({"id": [1, 2], "x": [0.0, 1.0], "y": [0.0, 0.0]})
    edges = pd.DataFrame({"u": [1, 1, 2], "v": [2, 1, 99], "length_m": [10.0, 5.0, 1.0]})
    g = WalkGraph.from_tables(nodes, edges)
    assert g.matrix.nnz == 2  # one undirected edge stored in both directions


def test_multi_source_includes_offsets_and_identifies_source(grid: WalkGraph) -> None:
    # Sources at node 0 (offset 0) and node 24 (offset 500).
    dist, src = grid.multi_source(np.array([0, 24]), np.array([0.0, 500.0]))
    assert dist[0] == pytest.approx(0, abs=0.01)
    assert src[0] == 0
    # node 20 = (row 4, col 0): via 0 → 400; via 24 → 400 + 500 → source 0 wins
    assert dist[20] == pytest.approx(400, abs=0.01) and src[20] == 0
    # node 24 itself: from source 1 = 500, from source 0 = 800 → 500
    assert dist[24] == pytest.approx(500, abs=0.01) and src[24] == 1


def test_multi_source_empty_and_limit(grid: WalkGraph) -> None:
    d, s = grid.multi_source(np.array([], dtype=int), np.array([]))
    assert np.isinf(d).all() and (s == -1).all()
    d, s = grid.multi_source(np.array([0]), np.array([0.0]), limit=250)
    assert np.isinf(d[24]) and s[24] == -1
    assert np.isfinite(d[1])


def test_nearest_facility_with_snap_distances(grid: WalkGraph) -> None:
    cells = np.array([[0.0, 10.0], [400.0, 400.0], [5000.0, 5000.0]])  # last one is far from the network
    dest = Destinations(np.array([7, 9]), np.array([[400.0, 300.0], [0.0, 400.0]]))
    d, f = nearest_facility(grid, cells, dest)
    # cell 0 snaps to node (0,0) with 10 m; facility 9 at node (row 4, col 0) is 400 m away
    assert d[0] == pytest.approx(410, abs=0.01) and f[0] == 9
    # cell 1 at node (4,4); facility 7 at node (3,4): 100 m
    assert d[1] == pytest.approx(100, abs=0.01) and f[1] == 7
    # cell 2 is > MAX_SNAP_M from any node → unreachable
    assert np.hypot(5000 - 400, 5000 - 400) > MAX_SNAP_M
    assert np.isinf(d[2]) and f[2] == -1


def test_multiple_points_per_facility_take_closest(grid: WalkGraph) -> None:
    # A 'park' with two access points maps back to ONE facility id.
    dest = Destinations(np.array([5, 5]), np.array([[0.0, 0.0], [400.0, 400.0]]))
    d, f = nearest_facility(grid, np.array([[400.0, 300.0]]), dest)
    assert d[0] == pytest.approx(100, abs=0.01) and f[0] == 5


def test_nearest_facility_no_destinations(grid: WalkGraph) -> None:
    d, f = nearest_facility(
        grid, np.array([[0.0, 0.0]]), Destinations(np.array([], dtype=int), np.empty((0, 2)))
    )
    assert np.isinf(d[0]) and f[0] == -1


def test_minutes_and_population_shares() -> None:
    mins = to_minutes(np.array([0.0, 600.0, 1200.0, np.inf]), speed_mps=1.0)
    assert mins.tolist()[:3] == [0.0, 10.0, 20.0] and np.isinf(mins[3])
    pop = np.array([10.0, 20.0, 30.0, 40.0])
    assert share_within(mins, pop, 15) == pytest.approx(0.3)
    assert share_within(mins, np.zeros(4), 15) == 0.0
    assert mean_minutes(mins, pop) == pytest.approx((0 * 10 + 10 * 20 + 20 * 30) / 60)
    assert mean_minutes(np.array([np.inf]), np.array([1.0])) is None
    m = metrics(mins, pop, 15)
    assert m["population_reachable"] == 30 and m["share_reachable"] == pytest.approx(0.3)


def test_composite_index_equal_and_custom_weights() -> None:
    df = pd.DataFrame({"a": [5.0, 20.0], "b": [10.0, np.inf]})
    assert composite_index(df, 15).tolist() == [1.0, 0.0]
    df2 = pd.DataFrame({"a": [5.0], "b": [20.0]})
    assert composite_index(df2, 15).iloc[0] == 0.5
    assert composite_index(df2, 15, {"a": 3.0, "b": 1.0}).iloc[0] == pytest.approx(0.75)


def test_summarize_groups_population_weighted() -> None:
    df = pd.DataFrame(
        {
            "district": ["A", "A", "B"],
            "population": [100.0, 300.0, 50.0],
            "index": [1.0, 0.0, 0.5],
            "school": [4.0, 12.0, 30.0],
        }
    )
    t = summarize_groups(df, ["school"], [5, 15], 15).set_index("district")
    assert t.loc["A", "population"] == 400
    assert t.loc["A", "index"] == pytest.approx(0.25)
    assert t.loc["A", "school__within_5"] == pytest.approx(0.25)
    assert t.loc["A", "school__within_15"] == pytest.approx(1.0)
    assert t.loc["B", "school__reachable"] == 0.0


def test_bigger_grid_scales() -> None:
    g = grid_graph(30, 50.0)
    d, _ = g.multi_source(np.array([0]), np.array([0.0]))
    assert d[-1] == pytest.approx(2 * 29 * 50)
