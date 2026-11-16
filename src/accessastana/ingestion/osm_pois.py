"""OSM .pbf → facility POIs by category (tag mapping in config/categories.yaml) → `pois`."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import osmium
import pandas as pd
import shapely.wkb
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
from shapely.geometry import Point
from shapely.prepared import prep
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from accessastana.config import CategoryConfig, load_categories
from accessastana.db.models import City, Poi
from accessastana.ingestion.base import BaseLoader, bulk_insert

KEEP_TAGS = (
    "amenity",
    "healthcare",
    "shop",
    "leisure",
    "highway",
    "public_transport",
    "operator",
    "ref",
    "addr:street",
    "addr:housenumber",
    "name:ru",
    "name:kk",
    "name:en",
    "opening_hours",
)


def read_osm_pois(pbf: Path, boundary_4326: Any, categories: dict[str, CategoryConfig]) -> gpd.GeoDataFrame:
    """Every node/closed way/multipolygon matching a category, inside the
    boundary (tested on the representative point). Polygons keep their
    geometry so parks can be sampled along their boundary later."""
    city = prep(boundary_4326)
    minx, miny, maxx, maxy = boundary_4326.bounds
    wkb = osmium.geom.WKBFactory()
    rows: list[dict[str, Any]] = []
    for obj in osmium.FileProcessor(str(pbf)).with_areas().with_locations():
        if not isinstance(obj, osmium.osm.Node | osmium.osm.Area):
            continue
        cats = [k for k, c in categories.items() if c.matches(obj.tags)]
        if not cats:
            continue
        if isinstance(obj, osmium.osm.Node):
            x, y = obj.location.lon, obj.location.lat
            if not (minx <= x <= maxx and miny <= y <= maxy):
                continue
            geom: Any = Point(x, y)
            ext_id = f"node/{obj.id}"
        else:
            try:
                geom = shapely.wkb.loads(wkb.create_multipolygon(obj), hex=True)
            except RuntimeError:
                continue
            ext_id = f"{'way' if obj.from_way() else 'relation'}/{obj.orig_id()}"
        point = geom if geom.geom_type == "Point" else geom.representative_point()
        if not city.contains(point):
            continue
        tags = {k: obj.tags.get(k) for k in KEEP_TAGS if obj.tags.get(k)}
        name = obj.tags.get("name") or obj.tags.get("name:ru") or obj.tags.get("name:kk")
        address = (
            " ".join(filter(None, [obj.tags.get("addr:street"), obj.tags.get("addr:housenumber")])) or None
        )
        for cat in cats:
            rows.append(
                {
                    "category": cat,
                    "external_id": ext_id,
                    "name": name,
                    "address": address,
                    "tags": tags,
                    "shape": geom,
                    "geometry": point,
                }
            )
    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs=4326)
    return gdf


def dedupe_points(gdf: gpd.GeoDataFrame, radius_m: float, metric_crs: str) -> gpd.GeoDataFrame:
    """Merge objects of ONE category closer than `radius_m` (e.g. a school
    mapped as both node and building polygon).

    Algorithm: build a graph whose edges connect points within the radius,
    take connected components (single-linkage clustering), and keep one
    representative per component: prefer polygons (more complete mapping),
    then named objects. Single linkage can chain a long row of objects, so
    the radius must stay small (20-50 m, see categories.yaml).
    """
    if radius_m <= 0 or len(gdf) < 2:
        return gdf.assign(merged_ids=[[]] * len(gdf))
    xy = np.column_stack([gdf.to_crs(metric_crs).geometry.x, gdf.to_crs(metric_crs).geometry.y])
    pairs = cKDTree(xy).query_pairs(radius_m, output_type="ndarray")
    from scipy.sparse import coo_matrix

    n = len(gdf)
    adj = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(n, n)) if len(pairs) else None
    labels = connected_components(adj, directed=False)[1] if adj is not None else np.arange(n)
    g = gdf.reset_index(drop=True).assign(
        _cluster=labels,
        _rank=[
            (0 if s.geom_type != "Point" else 1, 0 if isinstance(nm, str) and nm else 1)
            for s, nm in zip(gdf["shape"], gdf["name"], strict=True)
        ],
    )
    keep_rows = []
    for _, grp in g.groupby("_cluster"):
        grp = grp.sort_values("_rank")
        best = grp.iloc[0].copy()
        best["merged_ids"] = list(grp["external_id"].iloc[1:])
        keep_rows.append(best)
    return gpd.GeoDataFrame(keep_rows, geometry="geometry", crs=gdf.crs).drop(columns=["_cluster", "_rank"])


def boundary_samples(
    shape_4326: Any, spacing_m: float, metric_crs: str, max_points: int = 200
) -> list[list[float]]:
    """Points every `spacing_m` along a polygon's exterior(s): a proxy for park
    entrances, because routing to a large park's centroid overstates the walk."""
    s = gpd.GeoSeries([shape_4326], crs=4326).to_crs(metric_crs).iloc[0]
    rings = [s.exterior] if s.geom_type == "Polygon" else [p.exterior for p in s.geoms]
    pts = []
    for ring in rings:
        n = max(1, int(ring.length // spacing_m))
        pts += [ring.interpolate(i * ring.length / n) for i in range(n)]
    pts = pts[:: max(1, len(pts) // max_points)]
    back = gpd.GeoSeries(pts, crs=metric_crs).to_crs(4326)
    return [[round(p.x, 7), round(p.y, 7)] for p in back]


def prepare_category(gdf: gpd.GeoDataFrame, cfg: CategoryConfig, metric_crs: str) -> gpd.GeoDataFrame:
    """Apply per-category rules: minimum area, dedupe, access points."""
    if gdf.empty:
        return gdf
    areas = gpd.GeoSeries(gdf["shape"], crs=4326).to_crs(metric_crs).area
    gdf = gdf.assign(area_m2=areas.values)
    if cfg.min_area_m2:
        is_poly = gdf["shape"].map(lambda s: s.geom_type != "Point")
        applies = is_poly
        if cfg.min_area_applies_to:
            rule = cfg.min_area_applies_to
            applies = is_poly & gdf["tags"].map(lambda t: all(t.get(k) in v for k, v in rule.items()))
        gdf = gdf[~applies | (gdf["area_m2"] >= cfg.min_area_m2)]
    gdf = dedupe_points(gdf, cfg.dedupe_radius_m, metric_crs)
    if cfg.boundary_sample_m:
        gdf = gdf.assign(
            access_points=[
                boundary_samples(s, cfg.boundary_sample_m, metric_crs) if s.geom_type != "Point" else []
                for s in gdf["shape"]
            ]
        )
    return gdf


class OsmPoiLoader(BaseLoader):
    name = "osm-pois"

    def source_files(self) -> list[Path]:
        return [self.ctx.path(self.ctx.city.osm["pbf"]), self.ctx.config_path / "categories.yaml"]

    def extract(self) -> gpd.GeoDataFrame:
        from accessastana.db.session import get_sessionmaker

        with get_sessionmaker(self.ctx.database_url)() as s:
            wkt = s.scalar(select(City.boundary.ST_AsText()).where(City.slug == self.ctx.city.slug))
        if wkt is None:
            raise RuntimeError("run the osm-boundary loader first")
        boundary = gpd.GeoSeries.from_wkt([wkt]).iloc[0]
        cats = load_categories(self.ctx.config_dir)
        raw = read_osm_pois(self.source_files()[0], boundary, cats)
        parts = [
            prepare_category(raw[raw.category == c], cfg, self.ctx.city.metric_crs) for c, cfg in cats.items()
        ]
        return pd.concat([p for p in parts if not p.empty], ignore_index=True)

    def load(self, session: Session, data: gpd.GeoDataFrame, run_id: int) -> tuple[int, dict[str, Any]]:
        slug = self.ctx.city.slug
        session.execute(delete(Poi).where(Poi.city_slug == slug, Poi.source == "osm"))
        records = []
        for r in data.itertuples():
            attrs = {"tags": r.tags, "area_m2": round(float(r.area_m2), 1), "merged_ids": r.merged_ids}
            if isinstance(getattr(r, "access_points", None), list) and r.access_points:
                attrs["access_points"] = r.access_points
            records.append(
                {
                    "city_slug": slug,
                    "source": "osm",
                    "category": r.category,
                    "external_id": r.external_id,
                    "name": r.name,
                    "address": r.address,
                    "attrs": attrs,
                    "geometry": f"SRID=4326;POINT({r.geometry.x} {r.geometry.y})",
                    "import_run_id": run_id,
                }
            )
        n = bulk_insert(session, Poi.__table__, records)  # type: ignore[arg-type]
        return n, {"by_category": data.groupby("category").size().to_dict()}
