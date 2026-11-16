"""Kontur Population (H3 r8 GeoPackage) → `h3_cells` with calibrated population.

Steps
1. Cover the city with ALL H3 cells whose centroid lies inside the boundary
   (`h3.polygon_to_cells` uses the same centroid-containment rule). Kontur
   omits empty cells, but the map needs them too (population 0).
2. Attach Kontur population by H3 index.
3. Assign each cell to the district containing its centroid.
4. Calibrate (Phase 0 decision A): Kontur 2023-11 sums to ~53% of the official
   2025 total, so we rescale. If control totals exist for ALL districts, each
   district gets its own factor; otherwise one city-wide factor is used. This
   keeps Kontur's relative spatial pattern within each area and only fixes
   the level. Limitation (stated in the paper): growth since 2023 was
   concentrated in new districts, which a city-wide factor cannot capture.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import geopandas as gpd
import h3
import pandas as pd
from shapely.geometry import Point, Polygon
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from accessastana.db.models import City, District, H3Cell
from accessastana.ingestion.base import BaseLoader, bulk_insert


def cover_polygon(boundary_4326: Any, resolution: int) -> list[str]:
    """All H3 cells whose centre is inside the (multi)polygon."""
    shape = h3.geo_to_h3shape(boundary_4326.__geo_interface__)
    return sorted(h3.h3shape_to_cells(shape, resolution))


def cell_polygon(cell: str) -> Polygon:
    """H3 cell boundary as a shapely Polygon (lon/lat)."""
    return Polygon([(lng, lat) for lat, lng in h3.cell_to_boundary(cell)])


def calibrate(
    cells: pd.DataFrame, controls: pd.DataFrame, city_slug: str
) -> tuple[pd.Series, dict[str, Any]]:
    """Return calibrated population per cell and a description of the factors.

    `cells` needs columns population_raw and district (name or None).
    `controls` has columns city, district (NaN for city total), population.
    """
    c = controls[controls["city"] == city_slug]
    district_rows = c[c["district"].notna() & (c["district"] != "")]
    city_row = c[c["district"].isna() | (c["district"] == "")]
    known = set(cells["district"].dropna().unique())
    if known and known <= set(district_rows["district"]):
        raw_by_d = cells.groupby("district")["population_raw"].sum()
        target = district_rows.set_index("district")["population"]
        factors = (target / raw_by_d).reindex(known)
        f_cell = cells["district"].map(factors).fillna(1.0)
        return cells["population_raw"] * f_cell, {"method": "district", "factors": factors.round(4).to_dict()}
    if len(city_row):
        raw_total = cells["population_raw"].sum()
        factor = float(city_row["population"].iloc[0]) / raw_total if raw_total else 1.0
        return cells["population_raw"] * factor, {"method": "city", "factor": round(factor, 4)}
    return cells["population_raw"].copy(), {"method": "none"}


class KonturLoader(BaseLoader):
    """Kontur population → calibrated H3 cells."""

    name = "population"

    def source_files(self) -> list[Path]:
        p = self.ctx.city.population
        return [self.ctx.path(p["kontur_gpkg"]), self.ctx.path(p["control_totals_csv"])]

    def extract(self) -> dict[str, Any]:
        from accessastana.db.session import get_sessionmaker

        slug, res = self.ctx.city.slug, self.ctx.city.h3_resolution
        with get_sessionmaker(self.ctx.database_url)() as s:
            wkt = s.scalar(select(City.boundary.ST_AsText()).where(City.slug == slug))
            districts = [
                (d.id, d.name, d.geometry_wkt)
                for d in s.execute(
                    select(
                        District.id, District.name, District.geometry.ST_AsText().label("geometry_wkt")
                    ).where(District.city_slug == slug)
                )
            ]
        if wkt is None:
            raise RuntimeError("run the osm-boundary loader first")
        boundary = gpd.GeoSeries.from_wkt([wkt], crs=4326)
        gpkg, controls_csv = self.source_files()
        k = gpd.read_file(gpkg, bbox=tuple(boundary.to_crs(3857).total_bounds), columns=["h3", "population"])
        pop = dict(zip(k["h3"], k["population"], strict=True))

        cells = pd.DataFrame({"h3": cover_polygon(boundary.iloc[0], res)})
        cells["population_raw"] = cells["h3"].map(pop).fillna(0.0)
        latlng = cells["h3"].map(h3.cell_to_latlng)
        cent = gpd.GeoDataFrame(cells, geometry=[Point(p[1], p[0]) for p in latlng], crs=4326)
        if districts:
            dg = gpd.GeoDataFrame(
                {"district_id": [d[0] for d in districts], "district": [d[1] for d in districts]},
                geometry=gpd.GeoSeries.from_wkt([d[2] for d in districts]),
                crs=4326,
            )
            cent = gpd.sjoin(cent, dg, predicate="within", how="left").drop(columns="index_right")
            cent = cent[~cent.index.duplicated()]
        else:
            cent["district_id"], cent["district"] = None, None
        controls = pd.read_csv(controls_csv, dtype={"district": str})
        cent["population"], calib = calibrate(cent, controls, slug)
        not_in_kontur = int((~cells["h3"].isin(pop.keys())).sum())
        return {
            "cells": cent,
            "calibration": calib,
            "kontur_total_in_city": float(cent["population_raw"].sum()),
            "cells_without_kontur": not_in_kontur,
        }

    def load(self, session: Session, data: dict[str, Any], run_id: int) -> tuple[int, dict[str, Any]]:
        slug = self.ctx.city.slug
        cells: gpd.GeoDataFrame = data["cells"]
        session.execute(delete(H3Cell).where(H3Cell.city_slug == slug))
        n = bulk_insert(
            session,
            H3Cell.__table__,
            [  # type: ignore[arg-type]
                {
                    "city_slug": slug,
                    "h3": r.h3,
                    "district_id": None if pd.isna(r.district_id) else int(r.district_id),
                    "population_raw": float(r.population_raw),
                    "population": float(r.population),
                    "geometry": f"SRID=4326;{cell_polygon(r.h3).wkt}",
                    "centroid": f"SRID=4326;POINT({r.geometry.x} {r.geometry.y})",
                    "import_run_id": run_id,
                }
                for r in cells.itertuples()
            ],
        )
        total = float(cells["population"].sum())
        city = session.get(City, slug)
        if city is not None:
            city.population_total = total
        return n, {
            "calibration": data["calibration"],
            "kontur_total_in_city": round(data["kontur_total_in_city"]),
            "calibrated_total": round(total),
            "cells_without_kontur": data["cells_without_kontur"],
        }
