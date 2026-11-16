"""Phase 0 spike: extract the Astana administrative boundary (and its districts)
from the Geofabrik Kazakhstan extract.

Usage: python -I spike/01_boundary.py <kazakhstan.osm.pbf> <out_dir>

Why from the PBF and not Nominatim/Overpass: the final pipeline must be
reproducible offline from one versioned file, so the spike uses the same input.
"""

import json
import sys
from pathlib import Path

import osmium
import shapely.wkb
from shapely.geometry import mapping

pbf, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)

wkb = osmium.geom.WKBFactory()
found: list[dict] = []

# with_areas() makes pyosmium assemble multipolygons from relations; the
# filter keeps only boundary objects so assembly stays cheap on a country file.
fp = osmium.FileProcessor(str(pbf)).with_areas(osmium.filter.TagFilter(("boundary", "administrative")))
for obj in fp:
    if not isinstance(obj, osmium.osm.Area) or obj.from_way():
        continue
    tags = obj.tags
    names = " ".join(tags.get(k, "") for k in ("name", "name:en", "name:ru", "name:kk"))
    if "Астана" not in names and "Astana" not in names:
        continue
    try:
        geom = shapely.wkb.loads(wkb.create_multipolygon(obj), hex=True)
    except Exception as exc:  # broken relations happen in OSM
        print("skip", obj.orig_id(), exc)
        continue
    rec = {
        "relation_id": obj.orig_id(),
        "admin_level": tags.get("admin_level"),
        "name": tags.get("name"),
        "name_en": tags.get("name:en"),
        "population_tag": tags.get("population"),
        "population_date": tags.get("population:date"),
        "area_km2_approx": None,
    }
    found.append({"type": "Feature", "properties": rec, "geometry": mapping(geom)})
    print(rec)

(out_dir / "astana_admin_candidates.geojson").write_text(
    json.dumps({"type": "FeatureCollection", "features": found}, ensure_ascii=False)
)
