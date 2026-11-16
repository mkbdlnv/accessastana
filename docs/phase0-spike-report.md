# Phase 0 — data spike report (Astana)

Date: 2026-11-16. Inputs and licences are listed in `docs/data-sources.md`.
Reproduce with the throwaway scripts in `spike/`, run with Python 3.12:

```bash
python -I spike/01_boundary.py      data/raw/osm/kazakhstan-261115.osm.pbf data/interim
python -I spike/02_osm_inventory.py data/raw/osm/kazakhstan-261115.osm.pbf data/interim/astana_admin_candidates.geojson data/interim
python -I spike/03_population.py    data/raw/kontur/kontur_population_KZ_20231101.gpkg data/interim/astana_admin_candidates.geojson data/interim/astana_districts.geojson data/interim
```

Runtime on a laptop (Apple Silicon): boundary 39 s, inventory 2 min 8 s
(whole-country PBF). In production we will first clip the PBF to the city
bbox with `osmium extract` or `pyosmium`, so later runs take seconds.

## 1. Study area

- Astana: OSM relation 3087155, 800.3 km², 6 districts (admin_level 6).
- Kontur H3 r8 cells whose centroid lies in the city: **559**. 73 of them have
  fewer than 10 people (industrial land, river, outskirts).

## 2. OSM POI counts (draft tag mapping)

| Category | Draft tags | Objects | Nodes / polygons | Named | With address | Near-duplicate pairs (< 100 m, similar name) |
|---|---|---|---|---|---|---|
| School | `amenity=school` | 162 | 32 / 130 | 94% | 23% | 4 |
| Kindergarten | `amenity=kindergarten\|childcare` | 132 | 48 / 84 | 95% | 10% | 0 |
| Clinic | `amenity=clinic\|doctors`, `healthcare=clinic\|centre\|doctor` | 122 | 106 / 16 | 100% | 11% | 2 |
| Hospital (context only) | `amenity=hospital`, `healthcare=hospital` | 31 | 11 / 20 | 94% | 10% | – |
| Pharmacy | `amenity=pharmacy`, `healthcare=pharmacy` | 188 | 187 / 1 | 74% | 7% | 10 |
| Transit stop | `highway=bus_stop`, `public_transport=platform` | 1,152 | 1,106 / 46 | 48% | 1% | 244 |
| Grocery | `shop=supermarket\|convenience\|grocery\|greengrocer` | 637 | 607 / 30 | 88% | 10% | 60 |
| Park | `leisure=park\|garden` | 179 | 0 / 179 | 22% | 1% | – |

Total park area: 7.53 km² (0.9% of the city area).

Walkable network inside the city: **5,711 km** across 36,255 ways (largest
classes: service 1,951 km, footway 1,196 km, residential 997 km, track 456 km).

## 3. Population vs. official statistics

| | Population |
|---|---|
| Kontur 2023-11-01, summed over Astana | **814,833** |
| BNS, 2025-01-01 | **1,528,887** |
| Ratio | **0.53** |

Kontur by district: Сарыарқа 180,907 · Байқоңыр 160,130 · Нұра 143,217 ·
Есіл 132,010 · Алматы 110,194 · Сарайшық 88,345 · unassigned 30.

## 4. Obvious data gaps and risks

> Update 2026-11-16: the registry comparison (items 2, 5, 6) was later dropped from scope;
> see docs/data-sources.md §4.

1. **Population is underestimated by ~47%.** This is the biggest threat to
   validity. Shares (e.g. "% of residents within 15 min") are less affected
   than absolute counts, but the error is not uniform: the fastest-growing
   areas (Есіл, Нұра, Сарайшық) are probably the most underestimated. This
   biases accessibility scores toward the older centre.
2. **Kindergartens look heavily under-mapped.** 132 objects for a city of
   about 1.5 M people is very low. This is a hypothesis until the registry
   arrives; it is exactly what Phase 3 should quantify. Schools (162) may be
   closer to complete, but only the registry can tell.
3. **Transit stops are double-mapped.** About 21% of stops have a
   near-duplicate. They must be deduplicated (cluster within ~30–50 m) before
   computing "nearest stop", or else excluded from completeness metrics.
4. **Parks are small and mostly unnamed.** Destinations should be park
   *entrances* or polygon-boundary points, not centroids: a centroid of a
   large park can sit 500 m inside it. A minimum area threshold also needs
   deciding, because `leisure=garden` includes tiny private yards.
5. **Few address tags.** Matching OSM to registries must be spatial + fuzzy
   name. If registries lack coordinates we need geocoding, and that is itself
   a source of error to report.
6. **No registry files yet.** These block Phase 3.
7. **Climate data are reanalysis, not observations.** This is adequate for
   parametrising seasons (winter DJF mean −11.9 °C, 117 days below −20 °C in
   10 years) but not for describing micro-conditions.

## 5. Decisions (resolved 2026-11-16, see docs/data-sources.md → "Team decisions")

- **Population calibration** (recommended: *A*):
  - A. Rescale Kontur cells within each district so that district totals match
    BNS district totals (simple dasymetric correction). This keeps Kontur's
    intra-district pattern, and the fix is easy to defend and document.
  - B. Rebuild population from OSM residential buildings (footprint ×
    `building:levels`), scaled to BNS totals. This is more accurate for new
    districts, but `building:levels` coverage is unverified and it adds a
    phase of work.
  - C. Use raw Kontur and report only relative shares, with the bias stated
    as a limitation.
- **Registry files:** who collects them, and in which format. The minimum is
  schools, kindergartens and polyclinics.
- **Park definition:** `leisure=park` only, or also `garden` above an area
  threshold.
