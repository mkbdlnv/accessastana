"""OSM .pbf → pedestrian network (OSMnx) → tables `network_nodes`, `network_edges`.

Why the detour through an .osm XML file: OSMnx builds graphs from the
Overpass API or from OSM XML (`ox.graph_from_xml`), but it cannot read .pbf.
Querying Overpass would make the pipeline depend on a live service and on the
day it is run. Instead we (1) filter walkable ways from the pinned Geofabrik
.pbf with pyosmium, (2) write them as XML, (3) let OSMnx do topology
simplification and keep the largest connected component.

Walkability filter (`is_walkable`): adapted from OSMnx's built-in "walk" network
type. It keeps everything with a `highway` tag except motor-only and
non-existent roads, and drops ways tagged `foot=no` or with private access.
Difference from OSMnx: we KEEP `highway=cycleway`, because in Astana many
cycle tracks are shared paths with no separate footway mapped (Phase 0
inventory: 133 km of cycleways).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from xml.sax.saxutils import quoteattr

import geopandas as gpd
import osmium
import pandas as pd
from shapely.geometry import Point
from shapely.prepared import prep
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from accessastana.db.models import City, NetworkEdge, NetworkNode
from accessastana.ingestion.base import BaseLoader, bulk_insert

EXCLUDED_HIGHWAYS = {
    "motorway",
    "motorway_link",
    "trunk",
    "trunk_link",
    "construction",
    "proposed",
    "planned",
    "abandoned",
    "raceway",
    "bus_guideway",
    "busway",
    "razed",
    "no",
    "platform",
    "elevator",
}
PRIVATE_ACCESS = {"private", "no"}
CLIP_BUFFER_M = 1000  # keep paths just outside the border: shortest paths may leave the city


def is_walkable(tags: Any) -> bool:
    hw = tags.get("highway")
    if hw is None or hw in EXCLUDED_HIGHWAYS or tags.get("area") == "yes":
        return False
    if tags.get("foot") == "no" or tags.get("service") == "private":
        return False
    # access=private/no unless foot is explicitly allowed
    return not (
        tags.get("access") in PRIVATE_ACCESS and tags.get("foot") not in {"yes", "designated", "permissive"}
    )


def write_walk_xml(pbf: Path, clip_polygon_4326: Any, out_xml: Path) -> dict[str, int]:
    """Write walkable ways intersecting `clip_polygon_4326` (+ their nodes) to OSM XML."""
    clip = prep(clip_polygon_4326)
    minx, miny, maxx, maxy = clip_polygon_4326.bounds
    nodes: dict[int, tuple[float, float]] = {}
    ways: list[tuple[int, list[int], dict[str, str]]] = []
    for obj in osmium.FileProcessor(str(pbf), osmium.osm.NODE | osmium.osm.WAY).with_locations():
        if not isinstance(obj, osmium.osm.Way) or not is_walkable(obj.tags):
            continue
        try:
            coords = [(n.ref, n.lon, n.lat) for n in obj.nodes]
        except osmium.InvalidLocationError:
            continue
        # cheap bbox test before the exact polygon test
        if not any(
            minx <= x <= maxx and miny <= y <= maxy and clip.contains(Point(x, y)) for _, x, y in coords
        ):
            continue
        for ref, x, y in coords:
            nodes[ref] = (x, y)
        ways.append((obj.id, [c[0] for c in coords], {t.k: t.v for t in obj.tags}))
    out_xml.parent.mkdir(parents=True, exist_ok=True)
    with open(out_xml, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<osm version="0.6" generator="accessastana">\n')
        for nid, (x, y) in nodes.items():
            f.write(f'<node id="{nid}" lat="{y:.7f}" lon="{x:.7f}" version="1"/>\n')
        for wid, refs, tags in ways:
            f.write(f'<way id="{wid}" version="1">')
            f.writelines(f'<nd ref="{r}"/>' for r in refs)
            f.writelines(f"<tag k={quoteattr(k)} v={quoteattr(v)}/>" for k, v in tags.items())
            f.write("</way>\n")
        f.write("</osm>\n")
    return {"ways": len(ways), "nodes": len(nodes)}


def graph_tables(xml_path: Path) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Build a simplified, undirected walking graph with OSMnx and return
    (nodes, edges). Edge length is OSMnx's great-circle length in metres."""
    import osmnx as ox

    # bidirectional=True: pedestrians may walk both ways on one-way streets.
    # retain_all=False: keep only the largest connected component, otherwise
    # cells snapped to an isolated fragment would get no route at all.
    g = ox.graph_from_xml(xml_path, bidirectional=True, simplify=True, retain_all=False)
    nodes, edges = ox.graph_to_gdfs(g)
    edges = edges.reset_index()
    # Undirected: keep one row per (min(u,v), max(u,v), geometry length).
    edges["a"] = edges[["u", "v"]].min(axis=1)
    edges["b"] = edges[["u", "v"]].max(axis=1)
    edges = edges.sort_values("length").drop_duplicates(subset=["a", "b", "key"])
    edges["highway"] = edges["highway"].map(lambda h: h[0] if isinstance(h, list) else h)
    return nodes.reset_index(), edges


class OsmNetworkLoader(BaseLoader):
    name = "osm-network"

    def source_files(self) -> list[Path]:
        return [self.ctx.path(self.ctx.city.osm["pbf"])]

    def config_fingerprint(self) -> str:
        return super().config_fingerprint() + repr(sorted(EXCLUDED_HIGHWAYS)) + str(CLIP_BUFFER_M)

    def _clip_polygon(self) -> Any:
        from accessastana.db.session import get_sessionmaker

        with get_sessionmaker(self.ctx.database_url)() as s:
            wkt = s.scalar(select(City.boundary.ST_AsText()).where(City.slug == self.ctx.city.slug))
        if wkt is None:
            raise RuntimeError("run the osm-boundary loader first")
        poly = gpd.GeoSeries.from_wkt([wkt], crs=4326).to_crs(self.ctx.city.metric_crs)
        return poly.buffer(CLIP_BUFFER_M).to_crs(4326).iloc[0]

    def extract(self) -> dict[str, Any]:
        xml = self.ctx.path(f"data/interim/{self.ctx.city.slug}_walk.osm")
        stats = write_walk_xml(self.source_files()[0], self._clip_polygon(), xml)
        nodes, edges = graph_tables(xml)
        return {"nodes": nodes, "edges": edges, "stats": stats}

    def load(self, session: Session, data: dict[str, Any], run_id: int) -> tuple[int, dict[str, Any]]:
        slug = self.ctx.city.slug
        session.execute(delete(NetworkEdge).where(NetworkEdge.city_slug == slug))
        session.execute(delete(NetworkNode).where(NetworkNode.city_slug == slug))
        nodes: pd.DataFrame = data["nodes"]
        edges: gpd.GeoDataFrame = data["edges"]
        n_nodes = bulk_insert(
            session,
            NetworkNode.__table__,  # type: ignore[arg-type]
            [
                {
                    "city_slug": slug,
                    "id": int(r.osmid),
                    "geometry": f"SRID=4326;POINT({r.x} {r.y})",
                    "import_run_id": run_id,
                }
                for r in nodes.itertuples()
            ],
        )
        n_edges = bulk_insert(
            session,
            NetworkEdge.__table__,  # type: ignore[arg-type]
            [
                {
                    "city_slug": slug,
                    "u": int(r.u),
                    "v": int(r.v),
                    "length_m": float(r.length),
                    "highway": str(r.highway) if r.highway is not None else None,
                    "geometry": f"SRID=4326;{r.geometry.wkt}",
                    "import_run_id": run_id,
                }
                for r in edges.itertuples()
            ],
        )
        details = {
            **data["stats"],
            "graph_nodes": n_nodes,
            "graph_edges": n_edges,
            "total_km": round(float(edges["length"].sum()) / 1000, 1),
        }
        return n_nodes + n_edges, details
