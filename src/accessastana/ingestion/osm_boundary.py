"""OSM city boundary + districts → tables `cities`, `districts`."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import osmium
import shapely.wkb
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from accessastana.db.models import City, District
from accessastana.ingestion.base import BaseLoader, bulk_insert, ewkt


def as_multipolygon(g: BaseGeometry) -> MultiPolygon:
    """Wrap a Polygon into a MultiPolygon (DB column type)."""
    return MultiPolygon([g]) if isinstance(g, Polygon) else g  # type: ignore[return-value]


def read_admin_areas(pbf: Path, city_relation_id: int, district_level: str) -> dict[str, Any]:
    """Assemble the city polygon (by relation id) and all admin areas at
    `district_level` whose representative point lies inside the city."""
    wkb = osmium.geom.WKBFactory()
    city: dict[str, Any] | None = None
    candidates: list[dict[str, Any]] = []
    fp = osmium.FileProcessor(str(pbf)).with_areas(osmium.filter.TagFilter(("boundary", "administrative")))
    for obj in fp:
        if not isinstance(obj, osmium.osm.Area) or obj.from_way():
            continue
        is_city = obj.orig_id() == city_relation_id
        if not is_city and obj.tags.get("admin_level") != district_level:
            continue
        try:
            geom = shapely.wkb.loads(wkb.create_multipolygon(obj), hex=True)
        except RuntimeError:  # broken multipolygon in OSM data
            continue
        rec = {
            "osm_id": obj.orig_id(),
            "name": obj.tags.get("name", ""),
            "name_en": obj.tags.get("name:en"),
            "name_ru": obj.tags.get("name:ru"),
            "name_kk": obj.tags.get("name:kk"),
            "geometry": as_multipolygon(geom),
        }
        if is_city:
            city = rec
        else:
            candidates.append(rec)
    if city is None:
        raise ValueError(f"relation {city_relation_id} not found in {pbf}")
    districts = [d for d in candidates if city["geometry"].contains(d["geometry"].representative_point())]
    return {"city": city, "districts": districts}


class OsmBoundaryLoader(BaseLoader):
    """City boundary and districts from the OSM extract."""

    name = "osm-boundary"

    def source_files(self) -> list[Path]:
        return [self.ctx.path(self.ctx.city.osm["pbf"])]

    def extract(self) -> dict[str, Any]:
        osm = self.ctx.city.osm
        return read_admin_areas(
            self.source_files()[0], int(osm["boundary_relation_id"]), str(osm["district_admin_level"])
        )

    def load(self, session: Session, data: dict[str, Any], run_id: int) -> tuple[int, dict[str, Any]]:
        c, cfg = data["city"], self.ctx.city
        values = {
            "slug": cfg.slug,
            "name_en": cfg.name.get("en", c["name_en"] or c["name"]),
            "name_ru": cfg.name.get("ru", c["name_ru"] or c["name"]),
            "name_kk": cfg.name.get("kk", c["name_kk"] or c["name"]),
            "boundary": ewkt(c["geometry"]),
            "h3_resolution": cfg.h3_resolution,
            "metric_crs": cfg.metric_crs,
        }
        # Upsert, never delete: deleting a city would cascade to all its data.
        stmt = pg_insert(City).values(**values)
        session.execute(stmt.on_conflict_do_update(index_elements=["slug"], set_=values))
        session.execute(delete(District).where(District.city_slug == cfg.slug))
        n = bulk_insert(
            session,
            District.__table__,  # type: ignore[arg-type]
            [
                {
                    "city_slug": cfg.slug,
                    "osm_id": d["osm_id"],
                    "name": d["name"],
                    "name_en": d["name_en"],
                    "geometry": ewkt(d["geometry"]),
                }
                for d in data["districts"]
            ],
        )
        return n + 1, {"districts": [d["name"] for d in data["districts"]]}
