# API image: serves precomputed results + on-demand scenario/optimisation.
# It does NOT include the heavy ingestion stack (osmium, osmnx).
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /usr/local/bin/uv
WORKDIR /app

# Dependencies first (cached layer), then the source.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
COPY config ./config
COPY migrations ./migrations
COPY alembic.ini ./
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH" ACCESSASTANA_PROJECT_ROOT=/app
RUN useradd --create-home app && mkdir -p /app/reports && chown app /app/reports
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"
# Migrations run at start-up so a fresh server is self-initialising.
CMD ["sh", "-c", "alembic upgrade head && uvicorn accessastana.api.main:app --host 0.0.0.0 --port 8000 --workers 2"]
