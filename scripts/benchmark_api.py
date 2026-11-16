"""Measure API latency on the real Astana data (for NFR-01/NFR-02 in docs/requirements.md).

Usage: uv run python scripts/benchmark_api.py [base_url] [n]
Default base_url is http://localhost:8080/api (nginx → API), and n = 20 requests per endpoint
after one warm-up request. Prints p50/p95/max in seconds.
"""

import statistics
import sys
import time

import httpx

base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080/api"
n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
c = httpx.Client(base_url=base, timeout=120)

cases = {
    "GET /accessibility (school, winter)": lambda: c.get(
        "/accessibility", params={"city": "astana", "category": "school", "season": "winter"}
    ),
    "GET /accessibility (index, summer)": lambda: c.get(
        "/accessibility", params={"city": "astana", "category": "index", "season": "summer"}
    ),
    "GET /districts/summary": lambda: c.get(
        "/districts/summary", params={"city": "astana", "season": "winter"}
    ),
    "POST /scenarios (+2 clinics, winter)": lambda: c.post(
        "/scenarios",
        json={
            "city": "astana",
            "category": "clinic",
            "season": "winter",
            "add": [{"lon": 71.45, "lat": 51.09}, {"lon": 71.38, "lat": 51.16}],
        },
    ),
    "POST /optimize (MCLP k=5)": lambda: c.post(
        "/optimize",
        json={
            "city": "astana",
            "category": "kindergarten",
            "season": "winter_severe",
            "k": 5,
            "method": "max_covering",
        },
    ),
    "POST /optimize (p-median k=5)": lambda: c.post(
        "/optimize",
        json={"city": "astana", "category": "clinic", "season": "winter", "k": 5, "method": "p_median"},
    ),
}
print(f"base={base} n={n}")
print(f"{'endpoint':40s} {'p50':>7s} {'p95':>7s} {'max':>7s}")
for name, call in cases.items():
    assert call().status_code == 200  # warm-up (loads the engine once)
    t = []
    for _ in range(n):
        t0 = time.perf_counter()
        r = call()
        t.append(time.perf_counter() - t0)
        assert r.status_code == 200, r.text
    print(f"{name:40s} {statistics.median(t):7.3f} {statistics.quantiles(t, n=20)[18]:7.3f} {max(t):7.3f}")
