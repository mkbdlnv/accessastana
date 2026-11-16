"""Command-line entry point: `accessastana --help`.

Typical offline pipeline for a city (heavy work, run on a laptop):
    accessastana db-upgrade
    accessastana ingest all --city astana
    accessastana analyze all --city astana
    accessastana report --city astana
then copy the database to the server (see docs/deployment-aws.md).
"""

from __future__ import annotations

import json
import logging

import typer

from accessastana.config import load_city
from accessastana.settings import get_settings

app = typer.Typer(no_args_is_help=True, help="AccessAstana data pipeline")

INGEST_ORDER = ["osm-boundary", "osm-network", "osm-pois", "population", "climate"]


def _setup_logging() -> None:
    logging.basicConfig(
        level=get_settings().log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )


@app.command("db-upgrade")
def db_upgrade() -> None:
    """Apply Alembic migrations."""
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(get_settings().project_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(get_settings().project_root / "migrations"))
    command.upgrade(cfg, "head")


@app.command()
def ingest(
    source: str = typer.Argument(..., help=f"one of {INGEST_ORDER} or 'all'"),
    city: str = typer.Option("astana"),
    force: bool = typer.Option(False, help="re-import even if inputs are unchanged"),
) -> None:
    """Run one loader (or all, in dependency order)."""
    _setup_logging()
    from accessastana.ingestion import available_loaders
    from accessastana.ingestion.base import LoadContext

    s = get_settings()
    ctx = LoadContext(city=load_city(city), project_root=s.project_root, force=force)
    loaders = available_loaders()
    names = INGEST_ORDER if source == "all" else [source]
    for name in names:
        if name not in loaders:
            raise typer.BadParameter(f"unknown or unavailable loader {name!r} (installed: {list(loaders)})")
        loader = loaders[name](ctx)
        res = loader.run()
        typer.echo(
            f"{name}: {'skipped (unchanged)' if res.skipped else f'{res.rows} rows'} "
            f"{json.dumps(res.details, ensure_ascii=False, default=str)[:400]}"
        )


@app.command()
def analyze(
    step: str = typer.Argument(..., help="accessibility | all"),
    city: str = typer.Option("astana"),
) -> None:
    """Run analysis jobs and store results in the DB."""
    _setup_logging()
    from accessastana.jobs import run_accessibility

    if step in {"accessibility", "all"}:
        typer.echo(json.dumps(run_accessibility(city), ensure_ascii=False, indent=1, default=str))


@app.command()
def report(city: str = typer.Option("astana")) -> None:
    """Write tables/figures (reports/<city>/) and the PDF report."""
    _setup_logging()
    from accessastana.reporting.build import build_report

    out = build_report(city)
    typer.echo(f"report written to {out}")


@app.command()
def pipeline(city: str = typer.Option("astana"), force: bool = False) -> None:
    """ingest all → analyze all → report."""
    ingest("all", city=city, force=force)
    analyze("all", city=city)
    report(city=city)


if __name__ == "__main__":
    app()
