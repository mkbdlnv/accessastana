"""Phase 0 spike: inventory of OSM social-infrastructure POIs, districts and
walkable network inside the Astana boundary.

Usage: python -I spike/02_osm_inventory.py <pbf> <boundary.geojson> <out_dir>

The category -> tag mapping here is a DRAFT; the production version will live
in a YAML file (ingestion/config/osm_categories.yaml) in Phase 2.
"""

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import osmium
import shapely.wkb
from pyproj import Geod
from shapely.geometry import LineString, Point, shape
from shapely.prepared import prep

pbf, boundary_path, out_dir = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
city = shape(json.loads(boundary_path.read_text())["features"][0]["geometry"])
city_p = prep(city)
minx, miny, maxx, maxy = city.bounds
geod = Geod(ellps="WGS84")

# Draft mapping: category -> list of (key, allowed values). An object matches a
# category if ANY of the pairs matches. Order matters only for reporting.
CATEGORIES: dict[str, list[tuple[str, set[str]]]] = {
    "school": [("amenity", {"school"})],
    "kindergarten": [("amenity", {"kindergarten", "childcare"})],
    "clinic": [("amenity", {"clinic", "doctors"}), ("healthcare", {"clinic", "centre", "doctor"})],
    "hospital": [("amenity", {"hospital"}), ("healthcare", {"hospital"})],
    "pharmacy": [("amenity", {"pharmacy"}), ("healthcare", {"pharmacy"})],
    "transit_stop": [("highway", {"bus_stop"}), ("public_transport", {"platform"})],
    "grocery": [("shop", {"supermarket", "convenience", "grocery", "greengrocer"})],
    "park": [("leisure", {"park", "garden"})],
}
# Highway values usable by pedestrians (OSMnx 'walk' network uses a similar
# exclusion logic: motorways/trunk-links etc. are excluded).
WALK_HIGHWAYS = {
    "footway",
    "path",
    "pedestrian",
    "steps",
    "living_street",
    "residential",
    "service",
    "unclassified",
    "tertiary",
    "secondary",
    "primary",
    "track",
    "tertiary_link",
    "secondary_link",
    "primary_link",
    "cycleway",
    "corridor",
}

wkb = osmium.geom.WKBFactory()


def match(tags) -> list[str]:
    cats = []
    for cat, rules in CATEGORIES.items():
        if any(tags.get(k) in vals for k, vals in rules):
            cats.append(cat)
    return cats


def in_bbox(lon: float, lat: float) -> bool:
    return minx <= lon <= maxx and miny <= lat <= maxy


pois: list[dict] = []
districts: list[dict] = []
walk_len_m: Counter = Counter()
sidewalk_tagged = 0
walk_ways = 0

# Pass 1: nodes + closed ways/relations as areas (POIs and districts).
keys = ["amenity", "healthcare", "shop", "leisure", "highway", "public_transport", "boundary"]
fp = osmium.FileProcessor(str(pbf)).with_areas().with_locations()
for obj in fp:
    tags = obj.tags
    if isinstance(obj, osmium.osm.Node):
        cats = match(tags)
        if not cats or not in_bbox(obj.location.lon, obj.location.lat):
            continue
        pt = Point(obj.location.lon, obj.location.lat)
        osm_type, osm_id, area_m2 = "node", obj.id, 0.0
    elif isinstance(obj, osmium.osm.Area):
        is_district = tags.get("boundary") == "administrative" and tags.get("admin_level") in {
            "6",
            "7",
            "8",
            "9",
        }
        cats = match(tags)
        if not cats and not is_district:
            continue
        try:
            geom = shapely.wkb.loads(wkb.create_multipolygon(obj), hex=True)
        except Exception:
            continue
        pt = geom.representative_point()
        if not city_p.contains(pt):
            continue
        if is_district and not obj.from_way():
            districts.append(
                {
                    "type": "Feature",
                    "geometry": geom.__geo_interface__,
                    "properties": {
                        "relation_id": obj.orig_id(),
                        "admin_level": tags.get("admin_level"),
                        "name": tags.get("name"),
                        "name_en": tags.get("name:en"),
                    },
                }
            )
        if not cats:
            continue
        osm_type = "way" if obj.from_way() else "relation"
        osm_id = obj.orig_id()
        area_m2 = abs(geod.geometry_area_perimeter(geom)[0])
    elif isinstance(obj, osmium.osm.Way):
        hw = tags.get("highway")
        if hw not in WALK_HIGHWAYS or tags.get("foot") == "no" or tags.get("access") == "private":
            continue
        try:
            coords = [(n.lon, n.lat) for n in obj.nodes]
        except osmium.InvalidLocationError:
            continue
        if not coords or not in_bbox(*coords[0]) or not city_p.contains(Point(coords[0])):
            continue
        walk_len_m[hw] += geod.geometry_length(LineString(coords))
        walk_ways += 1
        if "sidewalk" in tags or "sidewalk:both" in tags:
            sidewalk_tagged += 1
        continue
    else:
        continue
    if not city_p.contains(pt):
        continue
    for c in cats:
        pois.append(
            {
                "category": c,
                "osm_type": osm_type,
                "osm_id": osm_id,
                "lon": round(pt.x, 7),
                "lat": round(pt.y, 7),
                "name": tags.get("name", ""),
                "name_ru": tags.get("name:ru", ""),
                "name_kk": tags.get("name:kk", ""),
                "has_addr": "addr:street" in tags or "addr:housenumber" in tags,
                "operator": tags.get("operator", ""),
                "area_m2": round(area_m2, 1),
            }
        )

out_dir.mkdir(parents=True, exist_ok=True)
with open(out_dir / "astana_osm_pois.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(pois[0].keys()))
    w.writeheader()
    w.writerows(pois)
(out_dir / "astana_districts.geojson").write_text(
    json.dumps({"type": "FeatureCollection", "features": districts}, ensure_ascii=False)
)

# ---- summary ----
by_cat: dict[str, Counter] = defaultdict(Counter)
for p in pois:
    c = by_cat[p["category"]]
    c["total"] += 1
    c[p["osm_type"]] += 1
    c["named"] += bool(p["name"])
    c["with_addr"] += p["has_addr"]
summary = {
    "city_area_km2": round(abs(geod.geometry_area_perimeter(city)[0]) / 1e6, 1),
    "categories": {k: dict(v) for k, v in by_cat.items()},
    "park_area_km2": round(sum(p["area_m2"] for p in pois if p["category"] == "park") / 1e6, 2),
    "districts": [(d["properties"]["admin_level"], d["properties"]["name"]) for d in districts],
    "walk_network_km": {k: round(v / 1000) for k, v in walk_len_m.most_common()},
    "walk_network_total_km": round(sum(walk_len_m.values()) / 1000),
    "walk_ways": walk_ways,
    "walk_ways_with_sidewalk_tag": sidewalk_tagged,
}
(out_dir / "osm_inventory_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
print(json.dumps(summary, ensure_ascii=False, indent=2))
