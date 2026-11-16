"""Shared fixtures.

Unit tests need nothing external. Integration tests (marker `db`) need a
disposable PostGIS database in TEST_DATABASE_URL; it is migrated to an empty
schema and seeded with the toy city by running the REAL loaders and jobs.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from dotenv import load_dotenv

from accessastana.analysis.graph import WalkGraph

load_dotenv(Path(__file__).resolve().parents[1] / ".env")  # local convenience; CI sets env vars directly


def grid_graph(n: int = 5, spacing: float = 100.0) -> WalkGraph:
    """n×n lattice, node id = i*n + j at (j*spacing, i*spacing). Shortest path
    between two nodes = Manhattan distance × spacing (a known closed form)."""
    ids, xs, ys, us, vs = [], [], [], [], []
    for i in range(n):
        for j in range(n):
            ids.append(i * n + j)
            xs.append(j * spacing)
            ys.append(i * spacing)
            if j + 1 < n:
                us.append(i * n + j)
                vs.append(i * n + j + 1)
            if i + 1 < n:
                us.append(i * n + j)
                vs.append((i + 1) * n + j)
    nodes = pd.DataFrame({"id": ids, "x": xs, "y": ys})
    edges = pd.DataFrame({"u": us, "v": vs, "length_m": spacing})
    return WalkGraph.from_tables(nodes, edges)


@pytest.fixture
def grid() -> WalkGraph:
    return grid_graph()


@pytest.fixture
def rng() -> np.random.Generator:
    return np.random.default_rng(42)


# --------------------------------------------------------------------------- database
@pytest.fixture(scope="session")
def db_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL not set")
    return url


@pytest.fixture(scope="session")
def toy_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    from tests.fixtures import toy

    d = tmp_path_factory.mktemp("toy")
    toy.make_osm(d / "toy.osm")
    toy.make_kontur_gpkg(d / "kontur.gpkg")
    toy.make_controls(d / "controls.csv")
    return d


def toy_city(toy_dir: Path):  # type: ignore[no-untyped-def]
    from accessastana.config import CityConfig

    return CityConfig(
        slug="astana",
        name={"en": "Testville", "ru": "Тестград", "kk": "Тестград"},
        osm={"pbf": str(toy_dir / "toy.osm"), "boundary_relation_id": 1000, "district_admin_level": "6"},
        metric_crs="EPSG:32642",
        h3_resolution=8,
        population={
            "kontur_gpkg": str(toy_dir / "kontur.gpkg"),
            "control_totals_csv": str(toy_dir / "controls.csv"),
        },
        weather={"latitude": 51.1, "longitude": 71.4},
        map_center=[71.41, 51.104],
    )


@pytest.fixture(scope="session")
def seeded_db(db_url: str, toy_dir: Path) -> Iterator[str]:
    """Empty schema → run all loaders on the toy city → run analysis jobs."""
    from alembic import command
    from alembic.config import Config

    from accessastana.ingestion import available_loaders
    from accessastana.ingestion.base import LoadContext
    from accessastana.ingestion.open_meteo import OpenMeteoLoader
    from accessastana.jobs import run_accessibility
    from tests.fixtures.toy import fake_open_meteo

    root = Path(__file__).resolve().parents[1]
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "migrations"))
    cfg.attributes["url"] = db_url
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")

    city = toy_city(toy_dir)
    ctx = LoadContext(city=city, project_root=toy_dir, database_url=db_url)
    OpenMeteoLoader.fetcher = staticmethod(fake_open_meteo)  # type: ignore[assignment]
    results = {}
    for name in ["osm-boundary", "osm-network", "osm-pois", "population", "climate"]:
        results[name] = available_loaders()[name](ctx).run()
    results["accessibility"] = run_accessibility("astana", db_url)
    os.environ["ACCESSASTANA_TOY_RESULTS"] = repr({k: getattr(v, "details", v) for k, v in results.items()})
    yield db_url
