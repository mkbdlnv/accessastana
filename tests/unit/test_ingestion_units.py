"""Pure parts of the loaders: H3 aggregation, calibration,
deduplication, tag matching and the OSM→graph path (no DB, no downloads)."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import h3
import pandas as pd
import pytest
from shapely.geometry import Point, Polygon

from accessastana.config import CategoryConfig, load_categories
from accessastana.ingestion.kontur import calibrate, cell_polygon, cover_polygon
from accessastana.ingestion.osm_network import is_walkable
from tests.fixtures import toy


def test_category_matching_is_or_of_ands() -> None:
    c = CategoryConfig(
        label="x", rules=[{"amenity": ["clinic"]}, {"healthcare": ["centre"], "operator": ["state"]}]
    )
    assert c.matches({"amenity": "clinic"})
    assert c.matches({"healthcare": "centre", "operator": "state"})
    assert not c.matches({"healthcare": "centre"})
    assert set(load_categories()) >= {
        "school",
        "kindergarten",
        "clinic",
        "pharmacy",
        "transit_stop",
        "grocery",
        "park",
    }


def test_h3_cover_and_cell_polygon_areas() -> None:
    poly = Polygon(toy.city_square())
    cells = cover_polygon(poly, 8)
    assert cells and all(h3.get_resolution(c) == 8 for c in cells)
    # every returned cell has its centre inside the polygon
    assert all(poly.contains(Point(h3.cell_to_latlng(c)[::-1])) for c in cells)
    area = gpd.GeoSeries([cell_polygon(cells[0])], crs=4326).to_crs(32642).area.iloc[0]
    assert 0.6e6 < area < 0.9e6  # r8 average ≈ 0.74 km²


def test_population_aggregation_sums_to_kontur(tmp_path: Path) -> None:
    gpkg = toy.make_kontur_gpkg(tmp_path / "k.gpkg")
    k = gpd.read_file(gpkg)
    assert k["population"].sum() == 1000 * len(k)
    assert k.crs.to_epsg() == 3857


def test_calibration_city_and_district() -> None:
    cells = pd.DataFrame({"population_raw": [10.0, 30.0, 60.0], "district": ["A", "A", "B"]})
    controls = pd.DataFrame({"city": ["x"], "district": [None], "population": [200.0]})
    pop, info = calibrate(cells, controls, "x")
    assert info == {"method": "city", "factor": 2.0} and pop.tolist() == [20.0, 60.0, 120.0]
    controls_d = pd.DataFrame({"city": ["x", "x"], "district": ["A", "B"], "population": [80.0, 60.0]})
    pop, info = calibrate(cells, controls_d, "x")
    assert info["method"] == "district" and pop.tolist() == [20.0, 60.0, 60.0]
    pop, info = calibrate(cells, controls.assign(city="other"), "x")
    assert info["method"] == "none" and pop.sum() == 100


def test_walkability_filter() -> None:
    assert is_walkable({"highway": "footway"})
    assert is_walkable({"highway": "residential", "access": "private", "foot": "yes"})
    assert not is_walkable({"highway": "motorway"})
    assert not is_walkable({"highway": "service", "access": "private"})
    assert not is_walkable({"highway": "path", "foot": "no"})
    assert not is_walkable({"building": "yes"})


osmium = pytest.importorskip("osmium")


def test_osm_xml_to_graph_and_pois(tmp_path: Path) -> None:
    from accessastana.ingestion.osm_boundary import read_admin_areas
    from accessastana.ingestion.osm_network import graph_tables, write_walk_xml
    from accessastana.ingestion.osm_pois import prepare_category, read_osm_pois

    src = toy.make_osm(tmp_path / "toy.osm")
    areas = read_admin_areas(src, 1000, "6")
    assert areas["city"]["name"] == "Тестград"
    assert sorted(d["name"] for d in areas["districts"]) == ["Батыс ауданы", "Шығыс ауданы"]

    stats = write_walk_xml(src, areas["city"]["geometry"], tmp_path / "walk.osm")
    assert stats["ways"] == 2 * toy.N  # the motorway is excluded
    nodes, edges = graph_tables(tmp_path / "walk.osm")
    # OSMnx simplification removes the 4 grid corners (degree-2 nodes) and
    # merges their two edges into one L-shaped edge.
    assert len(nodes) == toy.N * toy.N - 4
    assert len(edges) == 2 * toy.N * (toy.N - 1) - 4
    assert edges["length"].between(100, 220).all()
    assert (edges["length"] > 200).sum() == 4

    cats = load_categories()
    pois = read_osm_pois(src, areas["city"]["geometry"], cats)
    kg = prepare_category(pois[pois.category == "kindergarten"], cats["kindergarten"], "EPSG:32642")
    assert len(pois[pois.category == "kindergarten"]) == 2 and len(kg) == 1  # node + polygon merged
    assert kg.iloc[0]["merged_ids"]  # the merged object's id is kept for audit
    parks = prepare_category(pois[pois.category == "park"], cats["park"], "EPSG:32642")
    assert len(parks) == 1  # the tiny garden is dropped
    # perimeter ≈ 2·(210 m + 222 m) ≈ 864 m, sampled every 100 m → 8 points
    assert len(parks.iloc[0]["access_points"]) == 8
