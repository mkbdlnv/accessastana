# API contract (v1)

Base URL: `/` on the API service (port 8000). The frontend reaches it via the
`/api` prefix: the Vite dev proxy and nginx in production strip `/api`.
OpenAPI is generated at `/docs` and is the source of truth once implemented.

Enumerations
- `season`: `summer` | `winter` | `winter_severe`
- `category`: `school` | `kindergarten` | `clinic` | `pharmacy` | `transit_stop` | `grocery` | `park`
  plus the pseudo-category `index` (composite 15-minute index) for `/accessibility`.

## GET /health
`{"status": "ok", "db": "ok"}` (`db` is `"error"` and the HTTP status is 503 when the DB is unreachable)

## GET /cities
```json
[{"slug": "astana", "name": {"en": "Astana", "ru": "Астана", "kk": "Астана"},
  "center": [71.43, 51.13], "h3_resolution": 8, "population_total": 1528887.0,
  "attribution": ["© OpenStreetMap contributors", "..."]}]
```

## GET /categories
`[{"key": "school", "label": "Schools"}, ...]`

## GET /seasons?city=astana
`[{"key": "summer", "label": "Summer", "speed_mps": 1.33, "max_minutes": 15, "share_of_days": null}, ...]`

## GET /accessibility?city=&category=&season=&format=json|geojson
`format=json` (default):
```json
{"city": "astana", "category": "school", "season": "winter", "metric": "minutes",
 "max_minutes": 15,
 "cells": [{"h3": "882c2a...", "value": 7.4, "reachable": true, "population": 2310.5}]}
```
- For a normal category, `metric` is `"minutes"` and `value` is the walking time
  to the nearest facility (`null` = unreachable within 60 min).
- For `category=index`, `metric` is `"index"`, `value` is in [0, 1] (the
  population-independent share of categories reachable within `max_minutes`),
  and `reachable` is `value >= 0.999`.
- `format=geojson` returns a FeatureCollection of hexagon polygons with the
  same properties.

## GET /districts/summary?city=&season=
```json
{"city": "astana", "season": "summer", "thresholds": [5, 10, 15],
 "districts": [{"id": 1, "name": "Есіл ауданы", "population": 260000.0, "index": 0.71,
   "categories": {"school": {"share_within": {"5": 0.21, "10": 0.55, "15": 0.80},
                             "share_reachable": 0.80, "mean_minutes": 9.1}}}],
 "city_total": {"id": null, "name": "Astana", "population": 1528887.0, "index": 0.69, "categories": {}}}
```
`share_*` values are population-weighted fractions in [0, 1].

## GET /districts?city=
GeoJSON FeatureCollection of district polygons: `properties: {id, name, name_en}`.

## GET /pois?city=&category=
GeoJSON FeatureCollection of OSM facility points: `properties: {id, name, category}`.

## POST /scenarios
Request:
```json
{"city": "astana", "category": "school", "season": "winter",
 "add": [{"lon": 71.42, "lat": 51.10, "name": "New school"}], "remove": [123],
 "save": false, "name": null}
```
Response:
```json
{"scenario_id": null,
 "before": {"population_reachable": 900000.0, "share_reachable": 0.59, "mean_minutes": 12.3},
 "after":  {"population_reachable": 930000.0, "share_reachable": 0.61, "mean_minutes": 11.8},
 "changed_cells": [{"h3": "882c...", "before": 21.0, "after": 6.5, "reachable_after": true}]}
```

## POST /optimize
Request: `{"city": "astana", "category": "school", "season": "winter", "k": 5, "method": "max_covering" | "p_median"}`
Response:
```json
{"method": "max_covering", "k": 5, "status": "Optimal", "solve_seconds": 0.8,
 "locations": [{"h3": "882c...", "lon": 71.4, "lat": 51.1, "population_gain": 12000.0}],
 "before": {"population_reachable": 0, "share_reachable": 0, "mean_minutes": 0},
 "after": {"population_reachable": 0, "share_reachable": 0, "mean_minutes": 0}}
```
The `before`/`after` objects have the same shape as in `/scenarios`.

## GET /reports/{city}.pdf
`application/pdf`
