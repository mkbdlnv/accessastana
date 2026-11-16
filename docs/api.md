# Описание API AccessAstana

REST API на FastAPI. Машиночитаемая спецификация OpenAPI 3:
`docs/openapi.json` (генерируется командой `uv run python scripts/export_openapi.py`).
Интерактивная документация (Swagger UI) открывается на `http://<сервер>:8000/docs`
и показана на рисунке `docs/final/screenshots/09_api_docs.png`.

- **Базовый адрес:** напрямую `http://localhost:8000`; через веб-интерфейс — префикс `/api`
  (nginx убирает его при проксировании, так что `/api/cities` равно `/cities`).
- **Формат:** JSON (UTF-8), координаты WGS 84 (EPSG:4326), время в минутах, доли в диапазоне [0, 1].
- **Аутентификация:** нет. API отдаёт только агрегированные открытые данные, на запись
  работают только сохраняемые сценарии.
- **Сжатие:** gzip для ответов больше 1 КБ.
- **Ошибки:** `404` — неизвестный город, категория или сезон (`{"detail": "unknown category 'zoo'"}`);
  `422` — неверные параметры или превышение лимитов (`{"detail": "k must be <= 20"}`);
  `503` — недоступна БД (только `/health`).

Значения перечислений:
- `season`: `summer` | `winter` | `winter_severe`;
- `category`: `school` | `kindergarten` | `clinic` | `pharmacy` | `transit_stop` | `grocery` | `park`,
  а также для `/accessibility` псевдокатегория `index` (15-минутный индекс).

## Сводка эндпоинтов

| Метод и путь | Назначение | Источник данных | p95, с* |
|---|---|---|---|
| `GET /health` | Проверка сервиса и БД | БД (`SELECT 1`) | — |
| `GET /cities` | Города: центр карты, население, атрибуции | `cities` + YAML | — |
| `GET /categories` | Категории объектов | `config/categories.yaml` | — |
| `GET /seasons?city=` | Сезонные профили и доля зимних дней | `config/seasons.yaml` + `climate_profiles` | — |
| `GET /accessibility?city=&category=&season=&format=json\|geojson` | Минуты (или индекс) по H3-ячейкам | `accessibility_results` (предрасчёт) | 0,014 (школы), 0,070 (индекс) |
| `GET /districts/summary?city=&season=` | Доли ≤ 5/10/15 мин и индекс по районам | `accessibility_results` + `h3_cells` | 0,061 |
| `GET /districts?city=` | Границы районов (GeoJSON) | `districts` | — |
| `GET /pois?city=&category=` | Объекты OSM (GeoJSON), id используются в сценариях | `pois` | — |
| `POST /scenarios` | Сценарий «что если» | `CityEngine` в памяти | 0,006 |
| `POST /optimize` | Рекомендации k мест (MCLP / p-медиана) | `CityEngine` + OR-Tools CBC | 0,037 / 0,806 |
| `GET /reports/{city}.pdf` | PDF-отчёт (строится при первом запросе) | `reporting/` | — |

\* Измерено на данных Астаны, n = 20 после прогрева: `docs/final/evidence/benchmark.txt`.

## Примеры (реальные ответы, длинные списки сокращены «…»)

### GET /accessibility
```bash
curl "http://localhost:8080/api/accessibility?city=astana&category=school&season=winter"
```
```json
{"city": "astana", "category": "school", "season": "winter", "metric": "minutes", "max_minutes": 15.0,
 "cells": [{"h3": "8821502da1fffff", "value": null, "reachable": false, "population": 0.0}, "…"]}
```
`value = null` означает, что объект недоступен в пределах отсечки маршрутизации (6 км)
или ячейка дальше 600 м от пешеходной сети. При `category=index` поле `metric`
равно `"index"`, а `value` лежит в [0, 1].

### GET /districts/summary
```bash
curl "http://localhost:8080/api/districts/summary?city=astana&season=winter"
```
```json
{"city": "astana", "season": "winter", "thresholds": [5.0, 10.0, 15.0],
 "districts": [{"id": 6, "name": "Алматы ауданы", "population": 206759.14, "index": 0.6012,
   "categories": {"school": {"share_within": {"5": 0.1319, "10": 0.3071, "15": 0.4797},
                             "share_reachable": 0.4797, "mean_minutes": 18.31}}}, "…"],
 "city_total": {"…": "…"}}
```

### POST /scenarios
Запрос: добавить поликлинику.
```bash
curl -X POST http://localhost:8080/api/scenarios -H 'content-type: application/json' \
  -d '{"city":"astana","category":"clinic","season":"winter","add":[{"lon":71.479,"lat":51.094}]}'
```
```json
{"scenario_id": null,
 "before": {"population_reachable": 635445.6, "share_reachable": 0.4156, "mean_minutes": 24.84},
 "after":  {"population_reachable": 643750.2, "share_reachable": 0.4211, "mean_minutes": 24.41},
 "changed_cells": [{"h3": "8821538005fffff", "before": 34.24, "after": 17.41, "reachable_after": false}, "…"]}
```
Поля запроса: `add` — список `{lon, lat, name?}`; `remove` — список id из `/pois`;
`save: true` сохраняет сценарий в таблицы `scenarios` и `scenario_facilities` и возвращает `scenario_id`.
Лимит — 50 добавленных и удалённых объектов в сумме.

### POST /optimize
```bash
curl -X POST http://localhost:8080/api/optimize -H 'content-type: application/json' \
  -d '{"city":"astana","category":"kindergarten","season":"winter_severe","k":2,"method":"max_covering"}'
```
```json
{"method": "max_covering", "k": 2, "status": "Optimal", "solve_seconds": 0.005,
 "locations": [{"h3": "882153825bfffff", "lon": 71.41503, "lat": 51.18346, "population_gain": 14353.84},
               {"h3": "88215382adfffff", "lon": 71.49182, "lat": 51.13489, "population_gain": 14562.12}],
 "before": {"population_reachable": 378234.1, "share_reachable": 0.2474, "mean_minutes": 20.82},
 "after":  {"population_reachable": 407150.1, "share_reachable": 0.2663, "mean_minutes": 20.57}}
```
`method`: `max_covering` максимизирует число жителей, впервые попадающих в порог;
`p_median` минимизирует средневзвешенное время. Ограничение: `1 ≤ k ≤ 20`.

### GET /pois
```bash
curl "http://localhost:8080/api/pois?city=astana&category=clinic"   # 117 объектов
```
```json
{"type": "Feature", "geometry": {"type": "Point", "coordinates": [71.422653, 51.180514]},
 "properties": {"id": 2678, "name": "ТОО \"Дом Здоровья\"", "category": "clinic"}}
```

## Слои кода
`api/routers` (HTTP, валидация pydantic) → `api/services` (бизнес-логика, лимиты,
`EngineCache`) → `api/repositories` (SQL) и `analysis.CityEngine` (расчёты в памяти).
Схемы запросов и ответов описаны в `api/schemas.py`; их докстринги попадают в OpenAPI.
