"""Shared data access: read the DB into the DataFrames the analysis engine needs.

Repository pattern: SQL lives here (and in api/repositories), never in
analysis/ or in API routers.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from pyproj import Transformer
from sqlalchemy import text
from sqlalchemy.orm import Session

from accessastana.analysis.accessibility import Destinations
from accessastana.analysis.engine import CityEngine
from accessastana.analysis.graph import WalkGraph
from accessastana.config import load_categories, load_city, load_seasons


def read_df(session: Session, sql: str, **params: object) -> pd.DataFrame:
    res = session.execute(text(sql), params)
    return pd.DataFrame(res.fetchall(), columns=list(res.keys()))


def load_engine(session: Session, slug: str) -> CityEngine:
    city = load_city(slug)
    tf = Transformer.from_crs(4326, city.metric_crs, always_xy=True)

    def project(lon: pd.Series, lat: pd.Series) -> tuple[np.ndarray, np.ndarray]:
        return tf.transform(lon.to_numpy(float), lat.to_numpy(float))  # type: ignore[no-any-return]

    nodes = read_df(
        session,
        "SELECT id, ST_X(geometry) lon, ST_Y(geometry) lat FROM network_nodes WHERE city_slug=:c",
        c=slug,
    )
    if nodes.empty:
        raise LookupError(f"no network for city {slug!r}; run ingestion first")
    nodes["x"], nodes["y"] = project(nodes.lon, nodes.lat)
    edges = read_df(session, "SELECT u, v, length_m FROM network_edges WHERE city_slug=:c", c=slug)
    graph = WalkGraph.from_tables(nodes, edges)

    cells = read_df(
        session,
        """SELECT h3, ST_X(centroid) lon, ST_Y(centroid) lat, population, district_id
           FROM h3_cells WHERE city_slug=:c ORDER BY h3""",
        c=slug,
    )
    cells["x"], cells["y"] = project(cells.lon, cells.lat)

    pois = read_df(
        session,
        """SELECT id, category, ST_X(geometry) lon, ST_Y(geometry) lat, attrs
           FROM pois WHERE city_slug=:c AND source='osm'""",
        c=slug,
    )
    dests: dict[str, Destinations] = {}
    for cat in load_categories():
        sub = pois[pois.category == cat]
        ids: list[int] = []
        pts: list[tuple[float, float]] = []
        for r in sub.itertuples():
            # Parks: route to boundary sample points; others: to the POI point.
            access = (r.attrs or {}).get("access_points") or [[r.lon, r.lat]]
            ids += [int(r.id)] * len(access)
            pts += [tuple(p) for p in access]
        xy = np.empty((0, 2))
        if pts:
            arr = np.asarray(pts, float)
            xy = np.column_stack(tf.transform(arr[:, 0], arr[:, 1]))
        dests[cat] = Destinations(np.asarray(ids, dtype=np.int64), xy)
    return CityEngine(slug, city.metric_crs, graph, cells, dests, load_seasons().profiles)
