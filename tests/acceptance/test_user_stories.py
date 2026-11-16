"""Acceptance tests: one test per user story in docs/requirements.md.

Each test checks the story's acceptance criteria (AC) through the public
HTTP API on the seeded toy city. Test names start with the story id, so the
traceability matrix in docs/requirements.md can point at them.
"""

from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.db
CITY = "astana"


def _get(client: TestClient, path: str, **params: Any) -> Any:
    r = client.get(path, params=params)
    assert r.status_code == 200, r.text
    return r.json()


def test_us01_walking_time_map(client: TestClient) -> None:
    """US-01: map of walking time to the nearest facility of a chosen category."""
    body = _get(client, "/accessibility", city=CITY, category="school", season="summer")
    # AC1: one value per H3 cell of the city; AC2: the metric is minutes; AC3: null = unreachable
    assert body["metric"] == "minutes" and len(body["cells"]) > 0
    assert len({c["h3"] for c in body["cells"]}) == len(body["cells"])
    assert all(c["value"] is None or c["value"] >= 0 for c in body["cells"])
    # AC4: population is returned for every cell, so the map can be weighted
    assert all(c["population"] >= 0 for c in body["cells"])


def test_us02_summer_vs_winter(client: TestClient) -> None:
    """US-02: compare the same category in summer and winter."""
    s = {
        c["h3"]: c["value"]
        for c in _get(client, "/accessibility", city=CITY, category="clinic", season="summer")["cells"]
    }
    w = {
        c["h3"]: c["value"]
        for c in _get(client, "/accessibility", city=CITY, category="clinic", season="winter")["cells"]
    }
    # AC1: winter walking time is never shorter than summer for the same cell
    assert all(w[h] >= s[h] for h in s if s[h] is not None and w[h] is not None)
    # AC2: the season profiles expose speed and acceptable time
    seasons = {x["key"]: x for x in _get(client, "/seasons", city=CITY)}
    assert seasons["winter"]["speed_mps"] < seasons["summer"]["speed_mps"]
    assert seasons["winter_severe"]["max_minutes"] < seasons["summer"]["max_minutes"]


def test_us03_district_summary(client: TestClient) -> None:
    """US-03: compare districts by population share within 5/10/15 minutes."""
    body = _get(client, "/districts/summary", city=CITY, season="summer")
    assert body["thresholds"] == [5, 10, 15]
    for d in body["districts"] + [body["city_total"]]:
        sw = d["categories"]["school"]["share_within"]
        # AC1: shares are fractions in [0, 1]; AC2: they grow with the threshold
        assert 0 <= sw["5"] <= sw["10"] <= sw["15"] <= 1


def test_us04_fifteen_minute_index(client: TestClient) -> None:
    """US-04: one composite 15-minute index per cell."""
    body = _get(client, "/accessibility", city=CITY, category="index", season="summer")
    assert body["metric"] == "index"
    assert all(0 <= c["value"] <= 1 for c in body["cells"])


def test_us05_add_facility_scenario(client: TestClient) -> None:
    """US-05: what-if: add a facility and see before/after quickly."""
    import h3

    # Put the new pharmacy at the centre of the populated cell that is currently worst served.
    cells = _get(client, "/accessibility", city=CITY, category="pharmacy", season="summer")["cells"]
    worst = max(
        (c for c in cells if c["population"] > 0 and c["value"] is not None), key=lambda c: c["value"]
    )
    lat, lon = h3.cell_to_latlng(worst["h3"])
    t0 = time.perf_counter()
    r = client.post("/scenarios", json={"city": CITY, "category": "pharmacy", "season": "summer",
                                        "add": [{"lon": lon, "lat": lat}]})  # fmt: skip
    elapsed = time.perf_counter() - t0
    assert r.status_code == 200
    body = r.json()
    # AC1: coverage never decreases; AC2: changed cells are listed; AC3: answer in < 2 s
    assert body["after"]["population_reachable"] >= body["before"]["population_reachable"]
    assert worst["h3"] in {c["h3"] for c in body["changed_cells"]}
    assert elapsed < 2.0


def test_us06_remove_facility_scenario(client: TestClient) -> None:
    """US-06: what-if: close a facility."""
    pois = _get(client, "/pois", city=CITY, category="grocery")["features"]
    r = client.post("/scenarios", json={"city": CITY, "category": "grocery", "season": "summer",
                                        "remove": [pois[0]["properties"]["id"]]})  # fmt: skip
    body = r.json()
    # AC1: coverage never increases when a facility is removed
    assert body["after"]["population_reachable"] <= body["before"]["population_reachable"]


def test_us07_optimize_locations(client: TestClient) -> None:
    """US-07: recommend k new locations."""
    body = client.post("/optimize", json={"city": CITY, "category": "kindergarten", "season": "summer",
                                          "k": 2, "method": "max_covering"}).json()  # fmt: skip
    # AC1: at most k locations with coordinates; AC2: solver status reported;
    # AC3: gains per site add up to the total improvement
    assert len(body["locations"]) <= 2 and all({"lon", "lat"} <= set(loc) for loc in body["locations"])
    assert body["status"] in {"Optimal", "Feasible"}
    gain = sum(loc["population_gain"] for loc in body["locations"])
    delta = body["after"]["population_reachable"] - body["before"]["population_reachable"]
    assert gain == pytest.approx(delta, rel=1e-6, abs=1e-6)


def test_us08_pdf_report(client: TestClient) -> None:
    """US-08: download a reproducible PDF report."""
    r = client.get(f"/reports/{CITY}.pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"


def test_us10_attribution(client: TestClient) -> None:
    """US-10: required data attributions are available to the UI."""
    attr = " ".join(_get(client, "/cities")[0]["attribution"])
    for required in ("OpenStreetMap", "ODbL", "Kontur", "CC BY 4.0", "Open-Meteo"):
        assert required in attr


def test_us11_invalid_input_is_rejected(client: TestClient) -> None:
    """US-11 (robustness): invalid parameters give 404/422, never a 500."""
    assert (
        client.get(
            "/accessibility", params={"city": "nowhere", "category": "school", "season": "summer"}
        ).status_code
        == 404
    )
    assert (
        client.get(
            "/accessibility", params={"city": CITY, "category": "school", "season": "spring"}
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/optimize", json={"city": CITY, "category": "school", "season": "summer", "k": 0}
        ).status_code
        == 422
    )
