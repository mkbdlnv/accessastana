"""System smoke test against a RUNNING deployment (docker compose or EC2).

Skipped unless ACCESSASTANA_SMOKE_URL points at the public entry point, e.g.
    ACCESSASTANA_SMOKE_URL=http://localhost:8080 uv run pytest tests/system -m system
It goes through nginx (frontend container) to the API and the database, so it
checks the deployed system as a whole: routing, proxy, API, DB, PDF.
"""

from __future__ import annotations

import os
import statistics
import time

import httpx
import pytest

pytestmark = pytest.mark.system
BASE = os.environ.get("ACCESSASTANA_SMOKE_URL")


@pytest.fixture(scope="module")
def http() -> httpx.Client:
    if not BASE:
        pytest.skip("ACCESSASTANA_SMOKE_URL not set")
    return httpx.Client(base_url=BASE, timeout=60)


def test_spa_and_health(http: httpx.Client) -> None:
    assert http.get("/").status_code == 200
    assert '<div id="root"' in http.get("/some/client/route").text  # SPA fallback
    assert http.get("/api/health").json() == {"status": "ok", "db": "ok"}


def test_precomputed_layers(http: httpx.Client) -> None:
    cities = http.get("/api/cities").json()
    city = cities[0]["slug"]
    for season in ("summer", "winter", "winter_severe"):
        r = http.get("/api/accessibility", params={"city": city, "category": "index", "season": season})
        assert r.status_code == 200 and r.json()["cells"]


def test_scenario_latency(http: httpx.Client) -> None:
    """NFR-01: scenario recomputation p95 < 2 s (10 requests, after warm-up)."""
    city = http.get("/api/cities").json()[0]["slug"]
    body = {"city": city, "category": "clinic", "season": "winter", "add": [{"lon": 71.45, "lat": 51.10}]}
    http.post("/api/scenarios", json=body)  # warm-up: loads the city graph into memory
    times = []
    for _ in range(10):
        t0 = time.perf_counter()
        assert http.post("/api/scenarios", json=body).status_code == 200
        times.append(time.perf_counter() - t0)
    p95 = statistics.quantiles(times, n=20)[18]
    assert p95 < 2.0, f"p95={p95:.2f}s"


def test_pdf(http: httpx.Client) -> None:
    city = http.get("/api/cities").json()[0]["slug"]
    r = http.get(f"/api/reports/{city}.pdf")
    assert r.status_code == 200 and r.content[:4] == b"%PDF"
