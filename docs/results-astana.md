# First results: Astana (data snapshot 2026-11-15)

Regenerate with `accessastana report --city astana`. The full tables, figures
and PDF are written to `reports/astana/`. Numbers below are **population-weighted
shares of residents** (Kontur 2023-11, calibrated to the BNS total of 1,528,887).
They assume OSM is complete (the registry comparison was dropped from scope).

## Season profiles (config/seasons.yaml)

| Profile | Speed (m/s) | Acceptable one-way walk | Share of Dec–Feb days (Open-Meteo 2015–2024) |
|---|---|---|---|
| Summer | 1.33 | 15 min | — |
| Winter, typical (compact snow) | 1.244 | 15 min | 72.2% |
| Winter, severe (wind chill ≤ −28) | 1.104 | 10 min | 27.8% |

## Share of residents within the acceptable walk

| Category | Summer | Winter (typical) | Winter (severe) | Expected winter day* | Loss vs summer (pp) |
|---|---:|---:|---:|---:|---:|
| Transit stops | 82.2% | 81.2% | 64.9% | 76.7% | −5.6 |
| Grocery | 73.7% | 70.5% | 48.0% | 64.2% | −9.5 |
| Schools | 60.7% | 56.7% | 29.4% | 49.1% | −11.6 |
| Pharmacies | 55.0% | 50.9% | 32.2% | 45.7% | −9.3 |
| Kindergartens | 54.5% | 52.4% | 24.7% | 44.7% | −9.7 |
| Parks | 48.6% | 43.2% | 27.7% | 38.9% | −9.7 |
| Clinics | 45.2% | 41.6% | 20.0% | 35.6% | −9.6 |

\* Expected winter day = 0.722 · typical + 0.278 · severe.

**Reading:** slower walking on snow alone costs only 1–5 pp. Most of the winter
loss comes from the shorter acceptable walk on severe-cold days, which removes
21–31 pp of coverage, most of all for schools and kindergartens. This is where
the result is most sensitive to an assumption (10 min, see seasons.yaml). The
paper should therefore include a sensitivity analysis with 8/10/12 minutes.

## 15-minute index by district (share of 7 categories within the walk)

| District | Population (calibrated) | Summer | Winter | Severe cold |
|---|---:|---:|---:|---:|
| Сарыарқа | 339,000 | 0.74 | 0.71 | 0.47 |
| Есіл | 248,000 | 0.70 | 0.68 | 0.44 |
| Алматы | 207,000 | 0.67 | 0.61 | 0.37 |
| Нұра | 269,000 | 0.58 | 0.50 | 0.29 |
| Сарайшық | 166,000 | 0.44 | 0.41 | 0.18 |
| Байқоңыр | 300,000 | 0.43 | 0.42 | 0.28 |
| **City** | 1,528,887 | 0.60 | — | — |

## Caveats to state in the paper

1. OSM completeness is unverified. Low clinic and kindergarten coverage may
   partly be missing OSM data rather than missing facilities.
2. Population: a single city-wide calibration factor (×1.88) cannot capture
   uneven growth since 2023. District totals from BNS would fix this; the
   pipeline uses them automatically once they are added to
   `data/reference/population_control.csv`.
3. About 31k residents live in cells more than 600 m from any mapped walkable
   way (mostly private housing with unmapped lanes). They count as "unreachable".
4. Median network/straight-line detour ratio is about 1.5, which reflects
   gated residential blocks and the rail/river barriers in the east.
