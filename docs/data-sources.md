# Data sources

Every dataset used by AccessAstana is listed here with its licence, the exact
version we use, and known limitations. **Update this file whenever a source
version changes**: the analysis results are only reproducible for the versions
recorded here.

Required attributions (must be visible in the UI footer / map attribution
control and in the PDF report):

> © OpenStreetMap contributors (ODbL) · Population: Kontur Population (CC BY 4.0) ·
> Weather data by Open-Meteo.com (CC BY 4.0) · Official statistics: Bureau of
> National Statistics of the Republic of Kazakhstan

---

## 1. OpenStreetMap — Kazakhstan extract (Geofabrik)

| Field | Value |
|---|---|
| Provider | Geofabrik GmbH, <https://download.geofabrik.de/asia/kazakhstan.html> |
| File | `kazakhstan-261115.osm.pbf` (226,326,557 bytes) |
| Snapshot date | 2026-11-15 (Geofabrik `Last-Modified: Sun, 15 Nov 2026 23:56:52 GMT`) |
| Integrity | MD5 `f4cd092b20d1d3ed37ccf2e18fcb4c65` (verified against Geofabrik `.md5`) |
| Licence | Open Database License (ODbL) 1.0 — attribution "© OpenStreetMap contributors"; derived databases must stay under ODbL (share-alike) |
| Used for | pedestrian network, POIs by category, city + district boundaries |
| Update cadence | Geofabrik publishes daily; we pin a dated file (`kazakhstan-YYMMDD.osm.pbf`) rather than `-latest` for reproducibility |

**City boundary.** Relation **3087155** (`name=Астана`, `admin_level=4`),
800.3 km² (geodesic area). Districts: six `admin_level=6` relations inside it
(Алматы, Байқоңыр, Есіл, Нұра, Сарайшық, Сарыарқа ауданы). Сарайшық is the
newest district, created in 2024, and is already present in OSM.

**Known limitations** (measured in Phase 0, see `docs/phase0-spike-report.md`):
- Completeness is unknown and is NOT verified in this project (see section 4).
- Mixed geometry: the same facility can be mapped as a node, a building
  polygon, or both, which can double count. Schools are mostly polygons (129 of
  162), pharmacies are mostly nodes.
- Address tags are rare (≤ 23% of schools, < 10% elsewhere).
- Names mix Kazakh, Russian and Latin script. Matching must normalise case,
  script and common prefixes (e.g. «№», «школа-лицей», «ГККП», «ясли-сад»).
- Public-transport stops mix `highway=bus_stop` and `public_transport=platform`,
  and the two often describe the same stop (244 near-duplicate pairs within 100 m).
- Sidewalks are rarely tagged (428 of 36,255 walkable ways). The network will
  treat roads as walkable unless `foot=no`, which is a standard OSMnx
  assumption.
- The `population=814400` tag on the city relation is outdated and must not be used.

## 2. Population — Kontur Population, Kazakhstan

| Field | Value |
|---|---|
| Provider | Kontur, via HDX: <https://data.humdata.org/dataset/kontur-population-kazakhstan> |
| File | `kontur_population_KZ_20231101.gpkg.gz` (14,906,587 bytes) |
| Version | 2023-11-01 release |
| Licence | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| Format | GeoPackage, EPSG:3857, columns `h3` (H3 index, resolution 8), `population` |
| Used for | population weight per H3 cell |

**Method (per provider):** a fused global product built from GHSL, Facebook/Meta
HRSL, Microsoft building footprints, Copernicus land cover and OSM. It is a
model, not a census.

**Known limitations: CRITICAL for this project.**
- The total population inside the Astana boundary is **814,833**, against an
  official **1,528,887** on 2025-01-01 (Bureau of National Statistics, BNS).
  Kontur covers only **≈ 53%** of the official figure. Astana is one of the
  fastest-growing cities in the region (+6.9% in 2024), and most of the newest
  housing (Есіл, Нұра, Сарайшық) postdates Kontur's input layers.
- Absolute "people within 15 min" numbers therefore cannot be reported from raw
  Kontur values. See the calibration decision in the Phase 0 report.
- Resolution 8 cells average ~0.74 km² (edge ≈ 0.46 km). A centroid-to-facility
  time hides up to ~5 min of walking variation inside the cell.

**Optional comparison: Meta High Resolution Population Density, Kazakhstan.**
HDX dataset `kazakhstan-high-resolution-population-density-maps-demographic-estimates`,
CC BY 4.0, reference date **2019-06-01**. This is older than Kontur, so it is
useful only as a cross-check of the *spatial distribution*, not of totals. It
has not been downloaded yet.

## 3. Official population statistics — Bureau of National Statistics (BNS)

| Field | Value |
|---|---|
| Provider | Bureau of National Statistics, Agency for Strategic Planning and Reforms of RK, <https://stat.gov.kz> |
| Value used | Astana population on 2025-01-01: **1,528,887** |
| Source | BNS demographic publication for Jan–Dec 2024 (<https://stat.gov.kz/ru/news/o-demograficheskoy-situatsii-za-yanvar-dekabr-2024-goda/>), as reported by [Tengrinews](https://tengrinews.kz/kazakhstan_news/nazvana-chislennost-naseleniya-kazahstana-1-yanvarya-2025-561456/) |
| Later figures | BNS: 1,566,566 on 2025-06-01. The akimat reported 1,622,245 on 2025-11-01, but that is not a BNS figure, so we do not use it as a control total |
| Licence | Official statistics, public. Cite the source |
| TODO | Obtain **district-level** totals (BNS publishes population by district of Astana) and store them as a small CSV in `data/reference/`, with the publication URL and date |

## 4. Official facility registries: removed from scope

The original research goal 1 (OSM completeness: matching OSM POIs against
official registries) was **dropped by team decision on 2026-11-16**. No machine-readable
official registry with coordinates is openly available:
- the egov.kz school-contacts page loads its table from an internal API, and
  extracting it would amount to scraping;
- the data.egov.kz API requires a personal eGov key;
- commercial directories (2GIS, Zoon) are not allowed by their terms.

The code (loader, geocoding, matching, `/completeness` endpoint, UI tab) was removed. The
`pois.source` column is kept (always `'osm'`), so a future data source can be added.
**Consequence for the paper:** accessibility results assume OSM is complete. Where OSM
misses facilities (Phase 0 suggests kindergartens and clinics), accessibility is
underestimated. State this as a limitation.

## 5. Weather — Open-Meteo Historical Weather API

| Field | Value |
|---|---|
| Provider | Open-Meteo, <https://open-meteo.com/en/docs/historical-weather-api> (endpoint `archive-api.open-meteo.com/v1/archive`, no API key) |
| Underlying data | ECMWF reanalysis (ERA5 / ERA5-Land and others, chosen by Open-Meteo); grid cell, not a station |
| Query used | lat 51.17, lon 71.45 → snapped to grid point 51.142 N, 71.418 E, elevation 359 m; 2015-01-01 … 2024-12-31; daily `temperature_2m_mean`, `apparent_temperature_mean`, `wind_speed_10m_max`, `snowfall_sum` |
| Licence | CC BY 4.0. Attribution "Weather data by Open-Meteo.com" |
| Use policy | Free tier is for non-commercial use with rate limits. We fetch once per city and cache the result |

Phase 0 result (10 winters / summers):

| Season | Days | Mean T (°C) | 10th pct T | Mean apparent T | 10th pct apparent T | Mean daily max wind (km/h) | Days with mean T < −20 °C |
|---|---|---|---|---|---|---|---|
| Winter (DJF) | 903 | −11.9 | −21.3 | −17.4 | −26.9 | 19.6 | 117 |
| Summer (JJA) | 920 | 19.9 | 14.7 | 18.3 | 11.9 | 19.4 | 0 |

**Production query** (`ingestion/open_meteo.py`): daily `temperature_2m_mean`,
`temperature_2m_min`, `wind_speed_10m_mean`, `wind_speed_10m_max`,
`snowfall_sum`, km/h, period taken from `config/seasons.yaml`. The raw response
is cached in `data/raw/weather/astana_2015-01-01_2024-12-31.json`, and its
checksum versions the import. Using the daily minimum temperature with the
mean wind, 27.8% of December–February days have a wind chill ≤ −28
(the "severe cold" profile).

Limitations: reanalysis smooths urban heat-island and street-canyon wind
effects. The data contain no snow-clearance or sidewalk-ice information, and
those are what actually slow pedestrians. Climate data only *parametrise* the
season profiles; the walking-speed reductions come from the literature and are
documented and made configurable in Phase 5.

## 6. Basemap (frontend only)

OpenFreeMap (<https://openfreemap.org>), style `positron`: free, no API key,
built from OpenStreetMap data. Attribution «© OpenFreeMap © OpenStreetMap
contributors» is shown in the map's attribution control.

---

## Team decisions after Phase 0 (2026-11-16)

| Question | Decision | Where it is implemented |
|---|---|---|
| Population calibration | **A**: rescale Kontur to official control totals, per district when available, otherwise city-wide (current factor ×1.876) | `ingestion/kontur.py`, `data/reference/population_control.csv` |
| Park definition | `leisure=park` (any size) + `leisure=garden` ≥ 0.5 ha; destinations = points every 100 m along the park boundary | `config/categories.yaml` |
| Transit stop duplicates | merge objects of one category within 30 m (single-linkage), keep the polygon/named one | `ingestion/osm_pois.py:dedupe_points` |
| Registries / OSM completeness | **removed from scope** (no open registry with coordinates; see section 4) | — |
