# Results: Astana

> **Generated file**: `accessastana report` regenerates it from the database
> (`src/accessastana/reporting/results_doc.py`). Do not edit by hand.

All shares are **population-weighted shares of residents** (calibrated population total: 1,528,887; Kontur original: 814,833). The results assume OpenStreetMap is complete (the registry comparison is out of scope).

## Data versions

| loader       | source_version                                             | checksum     | date       |   rows |
|:-------------|:-----------------------------------------------------------|:-------------|:-----------|-------:|
| climate      | astana_2015-01-01_2024-12-31.json, seasons.yaml            | 055065fa7236 | 2026-11-16 |      3 |
| osm-boundary | kazakhstan-261115.osm.pbf                                  | 3ade4c2bc3e2 | 2026-11-16 |      7 |
| osm-network  | kazakhstan-261115.osm.pbf                                  | 537b5be299f9 | 2026-11-16 | 140531 |
| osm-pois     | kazakhstan-261115.osm.pbf, categories.yaml                 | 76e6118ea3b5 | 2026-11-16 |   2444 |
| population   | kontur_population_KZ_20231101.gpkg, population_control.csv | c27c21b5f38f | 2026-11-16 |    903 |

## Season profiles (config/seasons.yaml)

| Profile | Speed (m/s) | Acceptable one-way walk (min) | Share of Dec–Feb days |
|---|---:|---:|---:|
| Summer | 1.33 | 15 | — |
| Winter (typical) | 1.244 | 15 | 72.2% |
| Winter (severe cold) | 1.104 | 10 | 27.8% |

## Share of residents within the acceptable walk

| Category | Summer | Winter (typical) | Winter (severe) | Expected winter day* | Loss vs summer (pp) |
|---|---:|---:|---:|---:|---:|
| Public transport stops | 82.2% | 81.2% | 64.9% | 76.7% | −5.6 |
| Grocery stores | 73.7% | 70.5% | 48.0% | 64.2% | −9.5 |
| Schools | 60.7% | 56.7% | 29.4% | 49.1% | −11.6 |
| Pharmacies | 55.0% | 50.9% | 32.2% | 45.7% | −9.3 |
| Kindergartens | 54.5% | 52.4% | 24.7% | 44.7% | −9.7 |
| Parks | 48.6% | 43.2% | 27.7% | 38.9% | −9.7 |
| Clinics (primary care) | 45.2% | 41.6% | 20.0% | 35.6% | −9.6 |

\* Expected winter day = 0.722 · typical + 0.278 · severe (shares of December–February days from Open-Meteo 2015–2024).

## Sensitivity to the assumed severe-cold walk (10 min)

| Category | ≤ 8 min | ≤ 10 min (assumed) | ≤ 12 min | Range (pp) |
|---|---:|---:|---:|---:|
| Public transport stops | 53.0% | 64.9% | 72.8% | 19.9 |
| Grocery stores | 38.4% | 48.0% | 59.1% | 20.7 |
| Pharmacies | 21.5% | 32.2% | 36.2% | 14.7 |
| Schools | 21.7% | 29.4% | 37.3% | 15.7 |
| Parks | 22.5% | 27.7% | 33.1% | 10.6 |
| Kindergartens | 14.2% | 24.7% | 34.1% | 19.8 |
| Clinics (primary care) | 14.4% | 20.0% | 28.8% | 14.3 |

## 15-minute index by district (share of 7 categories within the walk)

| District | Population (calibrated) | Summer | Winter | Severe cold |
|---|---:|---:|---:|---:|
| Сарыарқа ауданы | 339,439 | 0.74 | 0.71 | 0.47 |
| Есіл ауданы | 247,693 | 0.70 | 0.68 | 0.44 |
| Алматы ауданы | 206,759 | 0.67 | 0.61 | 0.37 |
| Нұра ауданы | 268,721 | 0.58 | 0.50 | 0.29 |
| Сарайшық ауданы | 165,763 | 0.44 | 0.41 | 0.18 |
| Байқоңыр ауданы | 300,455 | 0.43 | 0.42 | 0.28 |

## Caveats

1. OSM completeness is not verified. Missing facilities in OSM make accessibility look worse than it is.
2. Population: one city-wide calibration factor. District totals from BNS would capture uneven growth.
3. Walking-speed factors are transferred from Norwegian observations (Fossum & Ryeng, 2021).
4. The 10-minute severe-cold walk is an assumption; see the sensitivity table above.
