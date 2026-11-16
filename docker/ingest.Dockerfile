# Offline preprocessing image (ingestion + analysis + reports).
FROM python:3.15-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --extra ingest --no-install-project
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./
RUN uv sync --frozen --no-dev --extra ingest
ENV PATH="/app/.venv/bin:$PATH" ACCESSASTANA_PROJECT_ROOT=/app
ENTRYPOINT []
CMD ["accessastana", "--help"]
