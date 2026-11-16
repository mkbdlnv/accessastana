# AccessAstana — web frontend

Single-page app (React + Vite + TypeScript) for the climate-adjusted walking
accessibility of social infrastructure in Astana. It talks only to the FastAPI
backend described in [`../docs/api.md`](../docs/api.md).

## Stack

| Purpose | Library |
| --- | --- |
| UI | React 19, TypeScript 6 (strict), Vite 8 |
| Basemap | MapLibre GL JS 6 + OpenFreeMap `positron` style (free, no API key) |
| H3 choropleth, points | deck.gl 9.4 (`H3HexagonLayer`, `ScatterplotLayer`, `GeoJsonLayer`) via `@deck.gl/mapbox` `MapboxOverlay` |
| i18n | own typed dictionaries `src/i18n/{en,ru,kk}.ts` (default: Russian) |
| Lint / tests | ESLint 10 flat config + typescript-eslint, Vitest 5 |

## Development

Requires Node.js ≥ 22.12.

```bash
npm install
npm run dev        # http://localhost:5173
```

The dev server proxies `/api/*` to `http://localhost:8000/*` (the `/api`
prefix is stripped), so start the API on port 8000 first. If the API is down
the UI still loads and shows an error with a "Retry" button in each panel.

To call an API on another host, set `VITE_API_BASE` (e.g.
`VITE_API_BASE=http://localhost:8000 npm run dev`); the API must then allow CORS.

## Scripts

| Command | What it does |
| --- | --- |
| `npm run dev` | dev server with hot reload |
| `npm run lint` | `tsc --noEmit` + ESLint |
| `npm test` | Vitest unit tests (colour scale, i18n key parity) |
| `npm run build` | type check + production build into `dist/` |
| `npm run preview` | serve the production build locally |

## Docker

```bash
docker build -t accessastana-frontend .
```

Multi-stage image: Node 22 builds the app, nginx 1.27 serves `dist/` and
proxies `/api/` to `http://api:8000/` (prefix stripped), so in
docker-compose the backend service must be called `api`. See `nginx.conf`.

## Code map

```
src/
  api/client.ts          typed fetch wrappers + TS types mirroring the API contract
  state/appState.ts      app state (selection, scenario edits, results) as a reducer + context
  state/useApi.ts        small GET hook: loading / error / retry, aborts stale requests
  lib/colors.ts          colour classes for minutes and the 15-minute index (+ tests)
  i18n/                  en/ru/kk dictionaries, provider, `useI18n()` hook (+ parity test)
  components/
    MapView.tsx          MapLibre map + deck.gl overlay, hover tooltip
    mapLayers.ts         builds all deck.gl layers from the current data
    Controls.tsx         city / category / season selectors
    Legend.tsx           legend with the season's minute threshold
    DistrictsPanel.tsx   /districts/summary table
    ScenarioPanel.tsx    what-if scenario (add / remove facilities, POST /scenarios)
    OptimizePanel.tsx    location optimisation (POST /optimize)
```

### How the map works

* MapLibre draws the vector basemap; deck.gl is added as a MapLibre control
  (`MapboxOverlay`, overlaid mode) and keeps its camera in sync with the map.
* The accessibility grid is an `H3HexagonLayer`: deck.gl converts each H3 index
  to a hexagon itself, so the API only sends cell ids and values.
* Colours: 5 classes of the viridis palette (yellow = good, purple = bad).
  For minutes the class breaks are T/3, 2T/3, T, 2T where T is the season's
  `max_minutes` (15 → 0–5, 5–10, 10–15, 15–30, >30); grey = unreachable (null).
  For the 15-minute index the classes are 0.2-wide steps of [0, 1].
* In scenario edit mode a map click adds a proposed facility at the clicked
  coordinate; a click on an existing facility (black point) toggles it for
  removal. After "Compute", changed cells are drawn on top with their *after*
  value and a dark outline.

## Attribution

Map data © OpenStreetMap contributors (ODbL), tiles © OpenFreeMap / OpenMapTiles.
The attribution control on the map and the footer (strings from `/cities`)
must stay visible.
