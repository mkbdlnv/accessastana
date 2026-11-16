# Системное руководство (System Manual) AccessAstana

Для администраторов и разработчиков. Архитектура описана в `docs/architecture.md`,
развёртывание на AWS — в `docs/deployment-aws.md`, API — в `docs/api.md`.

## 1. Состав системы

| Компонент | Технологии | Образ / запуск |
|---|---|---|
| Офлайн-пайплайн (ingestion, analysis, reporting) | Python 3.12, uv, pyosmium, OSMnx, geopandas, scipy, OR-Tools, matplotlib, reportlab | `uv run accessastana …` или `docker/ingest.Dockerfile` |
| API | FastAPI, uvicorn, SQLAlchemy 2, GeoAlchemy2, Alembic | `docker/api.Dockerfile` |
| Frontend | React 19, TypeScript, Vite, MapLibre GL, deck.gl | `frontend/Dockerfile` (nginx) |
| БД | PostgreSQL 17 + PostGIS 3.5 | `postgis/postgis:17-3.5` |

Схема данных: `docs/diagrams/png/er.png`. Миграции: `migrations/versions/0001`, `0002`.

## 2. Требования к окружению

- **Разработка:** macOS, Linux или Windows с WSL2; Docker 24+; uv ≥ 0.4 (сам ставит Python 3.12); Node.js ≥ 22.12; около 2 ГБ диска под данные.
- **Сервер:** Ubuntu 24.04 x86_64, 2 vCPU, 4 ГБ ОЗУ, 20 ГБ диска; наружу открыт только порт 80.

## 3. Конфигурация

| Файл / переменная | Назначение |
|---|---|
| `.env` (из `.env.example`) | `POSTGRES_*`, `DB_PORT`, `ACCESSASTANA_DATABASE_URL`, `ACCESSASTANA_CORS_ORIGINS`, `TEST_DATABASE_URL`. **Не коммитить** |
| `ACCESSASTANA_OPTIMIZE_MAX_K` (по умолчанию 20), `ACCESSASTANA_SCENARIO_MAX_FACILITIES` (50) | Защита от перегрузки |
| `config/cities/<город>.yaml` | Город: relation OSM, метрическая СК, H3, файлы данных, точка погоды |
| `config/categories.yaml` | Правила тегов OSM, дедупликация, параметры парков |
| `config/seasons.yaml` | Сезонные профили со ссылками на источники |
| `data/reference/population_control.csv` | Официальные итоги населения для калибровки |

**Добавление города:** скопировать `config/cities/astana.yaml`, указать relation id
границы, уровень районов, UTM-зону, координаты погоды и пути к файлам данных, затем
выполнить `accessastana pipeline --city <slug>`. Код менять не нужно.

## 4. Эксплуатационные процедуры

| Задача | Команда |
|---|---|
| Миграции БД | `uv run accessastana db-upgrade` (в контейнере api выполняется при старте) |
| Полный пересчёт | `uv run --extra ingest accessastana pipeline --city astana` (~6 мин) |
| Один загрузчик | `uv run --extra ingest accessastana ingest osm-pois --city astana [--force]` |
| Только расчёт или отчёт | `uv run accessastana analyze all`, `uv run accessastana report` |
| Резервная копия БД | `./scripts/export_db.sh` → `backups/accessastana-YYYYMMDD.dump` |
| Восстановление | `./scripts/restore_db.sh backups/<файл>.dump` (можно запускать повторно) |
| Проверка стенда | `ACCESSASTANA_SMOKE_URL=http://<host> uv run pytest tests/system -m system` |
| Замер задержек | `uv run python scripts/benchmark_api.py http://<host>/api 20` |
| Диаграммы | `./scripts/render_diagrams.sh`, `uv run python scripts/draw_uml_wireframes.py` |
| Спецификация OpenAPI | `uv run python scripts/export_openapi.py` |
| Логи | `docker compose -f docker-compose.prod.yml logs -f api` |

Журнал импортов: `SELECT loader, source_version, left(checksum,12), status, rows, finished_at FROM import_runs ORDER BY id;`

## 5. Контроль качества

```bash
uv run ruff check . && uv run ruff format --check .       # стиль и статический анализ
uv run mypy                                                # типы (analysis, api)
uv run pytest --cov=accessastana                           # unit + integration + acceptance (нужен TEST_DATABASE_URL)
cd frontend && npm run lint && npm test && npm run build   # фронтенд
```
CI (`.github/workflows/ci.yml`) запускает то же самое на каждый Pull Request с
сервисом PostGIS. `build.yml` собирает образы linux/amd64 и публикует их в GHCR
при слиянии в `main`.

## 6. Устранение неполадок

| Симптом | Причина | Решение |
|---|---|---|
| `role "accessastana" does not exist` | На порту 5432 отвечает локальный Postgres | В `.env` указать `DB_PORT=5433` и тот же порт в обоих URL |
| `no matching manifest for linux/arm64` | Образ PostGIS есть только для amd64 | Уже задано `platform: linux/amd64` (эмуляция на Apple Silicon) |
| `unknown or unavailable loader 'osm-…'` | Не установлены osmium и osmnx | `uv sync --extra ingest` |
| `/accessibility` → 404 `no accessibility results` | Не выполнен расчёт | `accessastana analyze all` |
| Первый `/scenarios` медленный | Граф города загружается в память (≈1 с) | Это нормально; дальше запросы занимают миллисекунды |
| `pg_restore: cannot drop schema public` | Старая версия скрипта | Использовать текущий `scripts/restore_db.sh` |

## 7. Безопасность и лицензии

- Секреты хранятся только в `.env` и переменных окружения; `.env` в `.gitignore`.
- В продакшене публичен только порт 80 (nginx). Порт БД наружу не открывается. CORS ограничен `PUBLIC_ORIGIN`.
- Лицензия кода — MIT (`LICENSE`). Данные и дамп БД — ODbL (производная база OSM) и CC BY 4.0.
  Атрибуции показываются в UI, PDF и API.
