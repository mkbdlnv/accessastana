# AccessAstana

**Climate-adjusted accessibility of social infrastructure in Astana using open data.**
Course project, *Applied Software Development Project*, Astana IT University.

For every H3 cell (resolution 8, about 0.74 km²) the system computes the network
walking time to the nearest school, kindergarten, clinic, pharmacy, transit stop,
grocery store and park, weighted by population. It then compares **summer vs
winter** (slower walking on snow, a shorter acceptable walk in severe cold), and
recommends **locations for new facilities** (maximal covering / p-median),
with interactive what-if scenarios on a map.

Other Kazakhstan cities can be added with one YAML file in `config/cities/`.

> Scope note: the original goal "OSM completeness vs official registries" was dropped
> (no open registry with coordinates is available; see `docs/data-sources.md` §4).
> Results therefore assume OpenStreetMap is complete.

| | |
|---|---|
| Architecture & design decisions | [docs/architecture.md](docs/architecture.md) |
| Data sources, licences, versions, limitations | [docs/data-sources.md](docs/data-sources.md) |
| Phase 0 data spike | [docs/phase0-spike-report.md](docs/phase0-spike-report.md) |
| First results for Astana | [docs/results-astana.md](docs/results-astana.md) |
| API contract | [docs/api-contract.md](docs/api-contract.md) (live OpenAPI at `/docs`) |
| AWS deployment | [docs/deployment-aws.md](docs/deployment-aws.md) |
| Frontend | [frontend/README.md](frontend/README.md) |

## Quick start (local)

Requirements: Docker, [uv](https://docs.astral.sh/uv/) (Python 3.12 is installed by uv), Node 22.

```bash
cp .env.example .env                       # adjust ports/passwords (DB_PORT if 5432 is taken)
docker compose up -d db
uv sync --extra ingest                     # Python deps incl. osmium/osmnx for ingestion
uv run accessastana db-upgrade             # Alembic migrations

# Data (see docs/data-sources.md for the exact files and versions)
mkdir -p data/raw/osm data/raw/kontur
curl -L -o data/raw/osm/kazakhstan-261115.osm.pbf https://download.geofabrik.de/asia/kazakhstan-261115.osm.pbf
curl -L https://geodata-eu-central-1-kontur-public.s3.amazonaws.com/kontur_datasets/kontur_population_KZ_20231101.gpkg.gz \
  | gunzip > data/raw/kontur/kontur_population_KZ_20231101.gpkg

uv run accessastana pipeline --city astana # ingest → analyze → report (~5 min)

uv run uvicorn accessastana.api.main:app --reload      # API on :8000, docs on /docs
cd frontend && npm install && npm run dev               # UI on :5173
```

Or run everything in containers: `docker compose up -d --build` → UI at http://localhost:8080.

## CLI

```
accessastana db-upgrade
accessastana ingest {osm-boundary|osm-network|osm-pois|population|climate|all} --city astana [--force]
accessastana analyze {accessibility|all} --city astana
accessastana report --city astana         # reports/astana/{*.csv,*.png,summary.md,report.pdf}
accessastana pipeline --city astana
```

Imports are **idempotent and versioned**: a loader whose inputs and config are
unchanged (SHA-256) is skipped, and every run is recorded in `import_runs`.

## Repository layout

```
config/                 categories.yaml (OSM tag mapping), seasons.yaml (climate profiles + references), cities/*.yaml
data/reference/         official population control totals (committed)
src/accessastana/
  ingestion/            BaseLoader + loaders: OSM boundary/network/POIs, Kontur, Open-Meteo
  db/                   SQLAlchemy/GeoAlchemy2 models, sessions, repositories
  analysis/             graph, accessibility, climate, location (OR-Tools), scenarios, CityEngine
  reporting/            report tables, figures, PDF
  api/                  FastAPI: routers → services → repositories
  jobs.py, cli.py
migrations/             Alembic
frontend/               React + Vite + TS + MapLibre + deck.gl, i18n kk/ru/en
tests/                  unit (synthetic graphs, toy optimisation) + integration (toy city in PostGIS)
docker/, docker-compose*.yml, scripts/, .github/
spike/                  Phase 0 throwaway scripts
```

## Quality

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy                                   # analysis + api, strict defs
uv run pytest --cov=accessastana.analysis --cov=accessastana.api   # needs TEST_DATABASE_URL for integration tests
cd frontend && npm run lint && npm test && npm run build
```

Tests never download data. Integration tests build a synthetic city (OSM XML,
GeoPackage, fake Open-Meteo) and run the **real** loaders, jobs
and API against a disposable PostGIS database. Current coverage of
`analysis` + `api` is about 98%. CI runs all of this on every PR (GitHub
Actions with a PostGIS service container), builds images on `main`, and
Dependabot keeps uv/npm/actions/docker dependencies updated.

## Modelling assumptions (all configurable, with sources in `config/seasons.yaml`)

| Parameter | Value | Source |
|---|---|---|
| Summer walking speed | 1.33 m/s (4.8 km/h) | within Knoblauch et al. (1996), TRR 1538 |
| Winter speed factor (compact snow) | × 0.935 | Fossum (NTNU), 2021: 1.43 vs 1.53 m/s on asphalt |
| Severe-cold speed factor (ice) | × 0.830 | Fossum, 2021: 1.27 vs 1.53 m/s |
| Severe-cold day | wind chill ≤ −28 | ECCC wind-chill guidance (frostbite risk in 10–30 min) |
| Acceptable walk | 15 min (10 min on severe-cold days) | 15-minute city; 10 min is a stated team assumption |
| Population | Kontur × 1.876 | calibrated to BNS 2025-01-01 total |

## Attribution

© OpenStreetMap contributors (ODbL) · Kontur Population (CC BY 4.0) ·
Weather data by Open-Meteo.com (CC BY 4.0) · Bureau of National Statistics RK ·
Basemap © OpenFreeMap.
