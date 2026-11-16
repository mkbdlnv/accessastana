"""End-to-end on the toy city: loaders → jobs → API (needs TEST_DATABASE_URL)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from accessastana.db.session import get_engine, get_sessionmaker

pytestmark = pytest.mark.db


@pytest.fixture(scope="module")
def client(seeded_db: str, tmp_path_factory: pytest.TempPathFactory) -> Iterator[TestClient]:
    from accessastana.api.main import create_app
    from accessastana.reporting.build import build_report

    out = tmp_path_factory.mktemp("reports")

    def builder(city: str, refresh: bool) -> Path:
        return build_report(city, seeded_db, out)

    app = create_app(maker=get_sessionmaker(seeded_db), report_builder=builder)
    with TestClient(app) as c:
        yield c


def q(db: str, sql: str) -> list[tuple]:  # type: ignore[type-arg]
    with get_engine(db).connect() as conn:
        return [tuple(r) for r in conn.execute(text(sql))]


# ---------------------------------------------------------------- pipeline / DB state
def test_loaders_populated_tables(seeded_db: str) -> None:
    assert q(seeded_db, "SELECT name_en FROM cities") == [("Testville",)]
    assert q(seeded_db, "SELECT count(*) FROM districts") == [(2,)]
    assert q(seeded_db, "SELECT count(*) FROM network_nodes")[0][0] == 77
    cats = dict(q(seeded_db, "SELECT category, count(*) FROM pois WHERE source='osm' GROUP BY 1"))
    assert cats == {
        "school": 2,
        "kindergarten": 1,
        "clinic": 1,
        "pharmacy": 1,
        "grocery": 1,
        "transit_stop": 2,
        "park": 1,
    }
    # calibrated population equals the control total
    assert round(q(seeded_db, "SELECT sum(population) FROM h3_cells")[0][0]) == 50000
    shares = dict(q(seeded_db, "SELECT season, share_of_days FROM climate_profiles"))
    assert shares["winter_severe"] == pytest.approx(0.5, abs=0.05)


def test_import_is_idempotent(seeded_db: str, toy_dir: Path) -> None:
    from accessastana.ingestion.base import LoadContext
    from accessastana.ingestion.open_meteo import OpenMeteoLoader
    from tests.conftest import toy_city

    city = toy_city(toy_dir)
    before = q(seeded_db, "SELECT count(*) FROM import_runs")[0][0]
    res = OpenMeteoLoader(LoadContext(city=city, project_root=toy_dir, database_url=seeded_db)).run()
    assert res.skipped  # same inputs + config → nothing happens
    assert q(seeded_db, "SELECT count(*) FROM import_runs")[0][0] == before
    forced = OpenMeteoLoader(
        LoadContext(city=city, project_root=toy_dir, database_url=seeded_db, force=True)
    ).run()
    assert not forced.skipped and forced.rows == 3
    # rows are replaced, not duplicated
    assert q(seeded_db, "SELECT count(*) FROM climate_profiles") == [(3,)]
    assert q(seeded_db, "SELECT count(*) FROM import_runs")[0][0] == before + 1


def test_accessibility_results_stored(seeded_db: str) -> None:
    n_cells = q(seeded_db, "SELECT count(*) FROM h3_cells")[0][0]
    assert q(seeded_db, "SELECT count(*) FROM accessibility_results")[0][0] == n_cells * 7 * 3
    # winter is never faster than summer for the same cell/category
    bad = q(
        seeded_db,
        """SELECT count(*) FROM accessibility_results s JOIN accessibility_results w
                          USING (city_slug, h3, category) WHERE s.season='summer' AND w.season='winter'
                          AND w.minutes < s.minutes""",
    )
    assert bad == [(0,)]


# ---------------------------------------------------------------- API
def test_health_and_catalog(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok", "db": "ok"}
    cities = client.get("/cities").json()
    assert cities[0]["slug"] == "astana" and cities[0]["population_total"] == pytest.approx(50000)
    assert any("OpenStreetMap" in a for a in cities[0]["attribution"])
    assert {c["key"] for c in client.get("/categories").json()} >= {"school", "park"}
    seasons = {s["key"]: s for s in client.get("/seasons", params={"city": "astana"}).json()}
    assert seasons["winter_severe"]["max_minutes"] == 10
    assert client.get("/seasons", params={"city": "nowhere"}).status_code == 404


def test_accessibility_endpoint(client: TestClient) -> None:
    r = client.get("/accessibility", params={"city": "astana", "category": "school", "season": "summer"})
    assert r.status_code == 200
    body = r.json()
    assert body["metric"] == "minutes" and body["cells"]
    populated = [c for c in body["cells"] if c["population"] > 0 and c["value"] is not None]
    assert populated and all(c["value"] < 30 for c in populated)
    idx = client.get(
        "/accessibility", params={"city": "astana", "category": "index", "season": "winter"}
    ).json()
    assert idx["metric"] == "index" and all(0 <= c["value"] <= 1 for c in idx["cells"])
    gj = client.get(
        "/accessibility",
        params={"city": "astana", "category": "park", "season": "summer", "format": "geojson"},
    ).json()
    assert gj["type"] == "FeatureCollection" and gj["features"][0]["geometry"]["type"] == "Polygon"
    assert (
        client.get(
            "/accessibility", params={"city": "astana", "category": "zoo", "season": "summer"}
        ).status_code
        == 404
    )
    assert client.get("/accessibility", params={"city": "astana", "category": "school"}).status_code == 422


def test_districts(client: TestClient) -> None:
    s = client.get("/districts/summary", params={"city": "astana", "season": "summer"}).json()
    names = [d["name"] for d in s["districts"]]
    assert names == sorted(names) and set(names) <= {"Батыс ауданы", "Шығыс ауданы"}
    total = s["city_total"]
    assert total["population"] == pytest.approx(50000, rel=1e-6)
    assert 0 <= total["categories"]["school"]["share_within"]["15"] <= 1
    assert sum(d["population"] for d in s["districts"]) <= total["population"] + 1
    geo = client.get("/districts", params={"city": "astana"}).json()
    assert len(geo["features"]) == 2


def test_pois(client: TestClient) -> None:
    pois = client.get("/pois", params={"city": "astana", "category": "school"}).json()
    assert len(pois["features"]) == 2
    assert {f["properties"]["category"] for f in pois["features"]} == {"school"}
    assert len(client.get("/pois", params={"city": "astana"}).json()["features"]) == 9
    assert client.get("/completeness", params={"city": "astana"}).status_code == 404  # removed from scope


def test_scenarios(client: TestClient, seeded_db: str) -> None:
    school_ids = [
        f["properties"]["id"]
        for f in client.get("/pois", params={"city": "astana", "category": "school"}).json()["features"]
    ]
    r = client.post(
        "/scenarios",
        json={
            "city": "astana",
            "category": "school",
            "season": "winter_severe",
            "remove": school_ids[:1],
            "add": [],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["after"]["share_reachable"] <= body["before"]["share_reachable"]
    assert body["changed_cells"] and body["scenario_id"] is None
    r2 = client.post(
        "/scenarios",
        json={
            "city": "astana",
            "category": "clinic",
            "season": "summer",
            "add": [{"lon": 71.41, "lat": 51.107}],
            "save": True,
            "name": "t",
        },
    )
    assert r2.status_code == 200 and r2.json()["scenario_id"] is not None
    assert q(seeded_db, "SELECT count(*) FROM scenario_facilities")[0][0] >= 1
    too_many = [{"lon": 71.4, "lat": 51.1}] * 51
    assert (
        client.post(
            "/scenarios", json={"city": "astana", "category": "school", "season": "summer", "add": too_many}
        ).status_code
        == 422
    )


def test_optimize(client: TestClient) -> None:
    for method in ("max_covering", "p_median"):
        r = client.post(
            "/optimize",
            json={
                "city": "astana",
                "category": "clinic",
                "season": "winter_severe",
                "k": 2,
                "method": method,
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] in {"Optimal", "Feasible"} and len(body["locations"]) <= 2
        assert body["after"]["population_reachable"] >= body["before"]["population_reachable"]
    assert (
        client.post(
            "/optimize", json={"city": "astana", "category": "clinic", "season": "summer", "k": 999}
        ).status_code
        == 422
    )


def test_pdf_report(client: TestClient) -> None:
    r = client.get("/reports/astana.pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF" and len(r.content) > 10_000
