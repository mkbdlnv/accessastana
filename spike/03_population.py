"""Phase 0 spike: Kontur population (H3 r8) totals for Astana and districts.

Usage: python -I spike/03_population.py <kontur_KZ.gpkg> <boundary.geojson> <districts.geojson> <out_dir>

Assignment rule (to be kept in production): a hexagon belongs to the city /
district whose polygon contains the hexagon CENTROID. This avoids double
counting along borders; the error is bounded by half a hexagon (~0.37 km2).
"""

import json
import sys
from pathlib import Path

import geopandas as gpd
import h3

gpkg, boundary, districts_path, out_dir = map(Path, sys.argv[1:5])

city = gpd.read_file(boundary).to_crs(4326)
districts = gpd.read_file(districts_path).to_crs(4326)
# Kontur ships in EPSG:3857; read only the city bbox to keep memory small.
k = gpd.read_file(gpkg, bbox=tuple(city.to_crs(3857).total_bounds))
print("kontur columns:", list(k.columns), "crs:", k.crs, "rows in bbox:", len(k))
print("h3 resolution:", h3.get_resolution(k["h3"].iloc[0]))

# Use the H3 index itself for the centroid (exact cell centre, no reprojection).
lat_lon = k["h3"].map(h3.cell_to_latlng)
cent = gpd.GeoDataFrame(
    k.drop(columns="geometry"),
    geometry=gpd.points_from_xy([p[1] for p in lat_lon], [p[0] for p in lat_lon]),
    crs=4326,
)
in_city = gpd.sjoin(cent, city[["geometry"]], predicate="within").drop(columns="index_right")
by_d = gpd.sjoin(in_city, districts[["name", "geometry"]], predicate="within", how="left")

summary = {
    "cells_in_city": len(in_city),
    "population_total": round(float(in_city["population"].sum())),
    "cells_with_pop_lt_10": int((in_city["population"] < 10).sum()),
    "max_cell_population": round(float(in_city["population"].max())),
    "by_district": {
        str(n): round(float(v))
        for n, v in by_d.groupby(by_d["name"].fillna("<none>"))["population"].sum().items()
    },
}
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "population_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
print(json.dumps(summary, ensure_ascii=False, indent=2))
