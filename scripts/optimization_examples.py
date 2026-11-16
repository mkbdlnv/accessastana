"""Reproducible optimisation examples for the report (docs/final/evidence/optimization_examples.txt).

Usage: uv run python scripts/optimization_examples.py [base_url]   (default http://localhost:8080/api)
"""

import sys

import httpx

base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080/api"
c = httpx.Client(base_url=base, timeout=300)
cases = [(cat, season, k, m) for cat in ("kindergarten", "clinic", "school") for season in ("summer", "winter_severe")
         for k in (5,) for m in ("max_covering", "p_median")]
print("category | season | k | method | status | solve_s | share_before | share_after | Δpp | pop_gain | mean_min_before | mean_min_after")
for cat, season, k, m in cases:
    r = c.post("/optimize", json={"city": "astana", "category": cat, "season": season, "k": k, "method": m}).json()
    b, a = r["before"], r["after"]
    print(f"{cat} | {season} | {k} | {m} | {r['status']} | {r['solve_seconds']} | {b['share_reachable']:.4f} | "
          f"{a['share_reachable']:.4f} | {100 * (a['share_reachable'] - b['share_reachable']):.2f} | "
          f"{a['population_reachable'] - b['population_reachable']:.0f} | {b['mean_minutes']:.2f} | {a['mean_minutes']:.2f}")
