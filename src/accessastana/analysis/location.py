"""Facility location: where should k NEW facilities go?

Both models keep existing facilities and add k new ones at candidate sites
(centroids of populated H3 cells; this is the usual "discrete candidate set"
approximation). Solved as MIPs with OR-Tools (CBC).

Notation: i = demand cell (weight w_i = population), j = candidate site,
d_ij = walking minutes, e_i = minutes to the nearest EXISTING facility,
T = acceptable minutes (season profile).

1. Maximal Covering Location Problem (Church & ReVelle, 1974):
       max  Σ_i w_i u_i
       s.t. u_i ≤ Σ_{j: d_ij ≤ T} y_j     for cells not already covered (e_i > T)
            Σ_j y_j = k,  y_j ∈ {0,1},  0 ≤ u_i ≤ 1
   → maximises the number of NEWLY covered residents.

2. p-median with existing facilities (Hakimi, 1964; ReVelle & Swain, 1970):
       min  Σ_i w_i ( e_i z_i + Σ_j d_ij x_ij )
       s.t. z_i + Σ_j x_ij = 1   (each cell is served by an existing or new site)
            x_ij ≤ y_j,  Σ_j y_j = k,  binaries y; x, z continuous ≥ 0
   → minimises the population-weighted average walking time.
   Only pairs with d_ij < e_i are generated: assigning a cell to a new site
   farther than its current facility can never improve the objective. This
   keeps the model sparse (thousands rather than millions of variables).
   Unreachable e_i are capped at `cap_minutes` so the objective stays finite.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
from ortools.linear_solver import pywraplp


@dataclass
class LocationSolution:
    """Chosen candidate indices, objective value, solver status and solve time."""

    chosen: list[int]  # candidate indices (columns of d)
    objective: float
    status: str
    solve_seconds: float


_STATUS = {
    pywraplp.Solver.OPTIMAL: "Optimal",
    pywraplp.Solver.FEASIBLE: "Feasible",
    pywraplp.Solver.INFEASIBLE: "Infeasible",
    pywraplp.Solver.NOT_SOLVED: "NotSolved",
}


def _solver(time_limit_s: float) -> pywraplp.Solver:
    s = pywraplp.Solver.CreateSolver("CBC")
    if s is None:  # pragma: no cover - depends on OR-Tools build
        raise RuntimeError("CBC solver not available in this OR-Tools build")
    s.SetTimeLimit(int(time_limit_s * 1000))
    return s


def maximal_covering(
    w: np.ndarray, d: np.ndarray, existing: np.ndarray, k: int, threshold: float, time_limit_s: float = 30
) -> LocationSolution:
    """w (n,), d (n, m) minutes (inf = unreachable), existing (n,) minutes."""
    _, m = d.shape
    k = min(k, m)
    s = _solver(time_limit_s)
    y = [s.BoolVar(f"y{j}") for j in range(m)]
    obj = s.Objective()
    for i in np.flatnonzero((existing > threshold) & (w > 0)):
        cover = np.flatnonzero(d[i] <= threshold)
        if cover.size == 0:
            continue
        u = s.NumVar(0, 1, f"u{i}")
        s.Add(u <= sum(y[j] for j in cover))
        obj.SetCoefficient(u, float(w[i]))
    s.Add(sum(y) == k)
    obj.SetMaximization()
    t0 = time.perf_counter()
    status = s.Solve()
    chosen = [j for j in range(m) if y[j].solution_value() > 0.5]
    return LocationSolution(chosen, obj.Value(), _STATUS.get(status, str(status)), time.perf_counter() - t0)


def p_median(
    w: np.ndarray,
    d: np.ndarray,
    existing: np.ndarray,
    k: int,
    cap_minutes: float = 60.0,
    time_limit_s: float = 60,
) -> LocationSolution:
    """p-median with existing facilities (see the module docstring for the model)."""
    _, m = d.shape
    k = min(k, m)
    e = np.minimum(np.where(np.isfinite(existing), existing, cap_minutes), cap_minutes)
    s = _solver(time_limit_s)
    y = [s.BoolVar(f"y{j}") for j in range(m)]
    obj = s.Objective()
    for i in np.flatnonzero(w > 0):
        better = np.flatnonzero(d[i] < e[i])
        if better.size == 0:
            obj.SetOffset(obj.offset() + float(w[i] * e[i]))
            continue
        z = s.NumVar(0, 1, f"z{i}")
        xs = []
        for j in better:
            x = s.NumVar(0, 1, f"x{i}_{j}")
            s.Add(x <= y[j])
            obj.SetCoefficient(x, float(w[i] * d[i, j]))
            xs.append(x)
        s.Add(z + sum(xs) == 1)
        obj.SetCoefficient(z, float(w[i] * e[i]))
    s.Add(sum(y) == k)
    obj.SetMinimization()
    t0 = time.perf_counter()
    status = s.Solve()
    chosen = [j for j in range(m) if y[j].solution_value() > 0.5]
    return LocationSolution(chosen, obj.Value(), _STATUS.get(status, str(status)), time.perf_counter() - t0)
