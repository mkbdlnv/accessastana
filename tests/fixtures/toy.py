"""Synthetic test data: a tiny 'city' near Astana's coordinates.

Geometry: a 9×9 street grid, ~105 m (lon) × 111 m (lat) between nodes,
origin at (71.40 E, 51.10 N). The city boundary is a square around the grid,
split into two districts (west/east). Nothing here is real data.
"""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import quoteattr

import geopandas as gpd
import h3
import pandas as pd
from shapely.geometry import Polygon

LON0, LAT0 = 71.40, 51.10
DLON, DLAT = 0.0015, 0.001
N = 9


def grid_node_id(i: int, j: int) -> int:
    return 1 + i * N + j


def grid_lonlat(i: int, j: int) -> tuple[float, float]:
    return LON0 + j * DLON, LAT0 + i * DLAT


class _Osm:
    def __init__(self) -> None:
        self.nodes: list[str] = []
        self.ways: list[str] = []
        self.rels: list[str] = []
        self._nid = 10_000
        self._wid = 100

    def node(self, lon: float, lat: float, tags: dict[str, str] | None = None, nid: int | None = None) -> int:
        nid = nid or self._next_node()
        t = "".join(f"<tag k={quoteattr(k)} v={quoteattr(v)}/>" for k, v in (tags or {}).items())
        self.nodes.append(f'<node id="{nid}" lat="{lat:.7f}" lon="{lon:.7f}" version="1">{t}</node>')
        return nid

    def way(self, refs: list[int], tags: dict[str, str]) -> int:
        self._wid += 1
        nd = "".join(f'<nd ref="{r}"/>' for r in refs)
        t = "".join(f"<tag k={quoteattr(k)} v={quoteattr(v)}/>" for k, v in tags.items())
        self.ways.append(f'<way id="{self._wid}" version="1">{nd}{t}</way>')
        return self._wid

    def polygon(self, coords: list[tuple[float, float]], tags: dict[str, str]) -> int:
        refs = [self.node(x, y) for x, y in coords]
        return self.way([*refs, refs[0]], tags)

    def relation(self, rid: int, outer_way: int, tags: dict[str, str]) -> None:
        t = "".join(f"<tag k={quoteattr(k)} v={quoteattr(v)}/>" for k, v in tags.items())
        self.rels.append(
            f'<relation id="{rid}" version="1"><member type="way" ref="{outer_way}" role="outer"/>{t}</relation>'
        )

    def _next_node(self) -> int:
        self._nid += 1
        return self._nid

    def write(self, path: Path) -> Path:
        body = "\n".join(self.nodes + self.ways + self.rels)
        path.write_text(
            f'<?xml version="1.0" encoding="UTF-8"?>\n<osm version="0.6">\n{body}\n</osm>\n', encoding="utf-8"
        )
        return path


def city_square(margin: float = 0.0012) -> list[tuple[float, float]]:
    x0, y0 = LON0 - margin, LAT0 - margin
    x1, y1 = LON0 + (N - 1) * DLON + margin, LAT0 + (N - 1) * DLAT + margin
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def make_osm(path: Path) -> Path:
    o = _Osm()
    for i in range(N):
        for j in range(N):
            o.node(*grid_lonlat(i, j), nid=grid_node_id(i, j))
    for i in range(N):  # east-west streets
        o.way([grid_node_id(i, j) for j in range(N)], {"highway": "residential", "name": f"Street {i}"})
    for j in range(N):  # north-south streets
        o.way([grid_node_id(i, j) for i in range(N)], {"highway": "footway"})
    # A motorway that must be excluded from the walking network.
    a, b = o.node(LON0 - 0.001, LAT0 - 0.0005), o.node(LON0 + 0.02, LAT0 - 0.0005)
    o.way([a, b], {"highway": "motorway"})

    # Facilities (all inside the grid).
    o.node(*grid_lonlat(1, 1), {"amenity": "school", "name": "Школа-гимназия №1"})
    o.node(*grid_lonlat(7, 7), {"amenity": "school", "name": "Школа № 2"})
    o.node(*grid_lonlat(4, 2), {"amenity": "kindergarten", "name": "Балабақша Айгөлек"})
    # The same kindergarten as a building polygon a few metres away → must be deduplicated.
    x, y = grid_lonlat(4, 2)
    o.polygon(
        [
            (x + 0.0001, y + 0.0001),
            (x + 0.0003, y + 0.0001),
            (x + 0.0003, y + 0.0002),
            (x + 0.0001, y + 0.0002),
        ],
        {"amenity": "kindergarten", "name": "Балабақша Айгөлек", "building": "yes"},
    )
    o.node(*grid_lonlat(6, 3), {"amenity": "clinic", "name": "Поликлиника №5"})
    o.node(*grid_lonlat(2, 6), {"amenity": "pharmacy", "name": "Europharma"})
    o.node(*grid_lonlat(4, 4), {"shop": "supermarket", "name": "Magnum"})
    o.node(*grid_lonlat(3, 5), {"highway": "bus_stop", "name": "Stop A"})
    o.node(*grid_lonlat(5, 1), {"highway": "bus_stop", "name": "Stop B"})
    px, py = grid_lonlat(6, 6)
    o.polygon(
        [(px, py), (px + 0.003, py), (px + 0.003, py + 0.002), (px, py + 0.002)],
        {"leisure": "park", "name": "Park"},
    )
    # A tiny private garden: must be dropped by min_area_m2 for gardens.
    gx, gy = grid_lonlat(0, 4)
    o.polygon(
        [(gx, gy), (gx + 0.0001, gy), (gx + 0.0001, gy + 0.0001), (gx, gy + 0.0001)], {"leisure": "garden"}
    )

    # Boundaries: city (admin_level 4, id 1000) and two districts.
    sq = city_square()
    o.relation(
        1000,
        o.polygon(sq, {}),
        {
            "type": "boundary",
            "boundary": "administrative",
            "admin_level": "4",
            "name": "Тестград",
            "name:en": "Testville",
        },
    )
    mid = LON0 + (N - 1) * DLON / 2
    west = [sq[0], (mid, sq[0][1]), (mid, sq[2][1]), sq[3]]
    east = [(mid, sq[0][1]), sq[1], sq[2], (mid, sq[2][1])]
    o.relation(
        2001,
        o.polygon(west, {}),
        {"type": "boundary", "boundary": "administrative", "admin_level": "6", "name": "Батыс ауданы"},
    )
    o.relation(
        2002,
        o.polygon(east, {}),
        {"type": "boundary", "boundary": "administrative", "admin_level": "6", "name": "Шығыс ауданы"},
    )
    return o.write(path)


def make_kontur_gpkg(path: Path, res: int = 8) -> Path:
    """Population 1000 for every r8 cell touching the grid (Kontur layout:
    columns h3, population, geometry in EPSG:3857)."""
    poly = Polygon(city_square())
    cells = sorted(h3.h3shape_to_cells(h3.geo_to_h3shape(poly.buffer(0.004).__geo_interface__), res))
    geoms = [Polygon([(lng, lat) for lat, lng in h3.cell_to_boundary(c)]) for c in cells]
    gdf = gpd.GeoDataFrame(
        {"h3": cells, "population": [1000.0] * len(cells)}, geometry=geoms, crs=4326
    ).to_crs(3857)
    gdf.to_file(path, driver="GPKG")
    return path


def make_controls(path: Path) -> Path:
    pd.DataFrame(
        [
            {
                "city": "astana",
                "district": "",
                "population": 50000,
                "reference_date": "2025-01-01",
                "source": "test",
            },
        ]
    ).to_csv(path, index=False)
    return path


def fake_open_meteo(_url: str, _params: dict[str, object]) -> dict[str, object]:
    """Two years of synthetic daily weather: winters alternate between mild
    (−10 °C, light wind) and severe (−30 °C, 20 km/h) days."""
    days = pd.date_range("2015-01-01", "2016-12-31", freq="D")
    winter = days.month.isin([12, 1, 2])
    severe = winter & (days.day % 2 == 0)
    tmin = [(-30.0 if s else -10.0) if w else 15.0 for w, s in zip(winter, severe, strict=True)]
    wind = [20.0 if s else 8.0 for s in severe]
    return {
        "latitude": 51.1,
        "longitude": 71.4,
        "daily": {
            "time": [d.strftime("%Y-%m-%d") for d in days],
            "temperature_2m_min": tmin,
            "temperature_2m_mean": [t + 5 for t in tmin],
            "wind_speed_10m_mean": wind,
            "wind_speed_10m_max": [w * 2 for w in wind],
            "snowfall_sum": [1.0 if w else 0.0 for w in winter],
        },
    }
