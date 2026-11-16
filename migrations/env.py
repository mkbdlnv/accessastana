"""Alembic environment: uses the app settings so there is one source of the DB URL."""

from logging.config import fileConfig

from alembic import context
from geoalchemy2 import alembic_helpers
from sqlalchemy import create_engine

from accessastana.db.models import Base
from accessastana.settings import get_settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Tables created by PostGIS / tiger geocoder that we must never touch.
_FOREIGN_TABLES = {"spatial_ref_sys", "topology", "layer"}


def include_object(obj, name, type_, reflected, compare_to):  # type: ignore[no-untyped-def]
    # Only manage objects that belong to OUR metadata. The postgis image also
    # installs the TIGER geocoder (tables in schema "tiger"), which autogenerate
    # would otherwise try to drop.
    if type_ == "table" and (name in _FOREIGN_TABLES or (reflected and name not in target_metadata.tables)):
        return False
    table = getattr(obj, "table", None)
    if (
        type_ in {"index", "column", "unique_constraint", "foreign_key_constraint"}
        and table is not None
        and table.name not in target_metadata.tables
    ):
        return False
    # GeoAlchemy2 helper hides the spatial indexes it manages itself.
    return bool(alembic_helpers.include_object(obj, name, type_, reflected, compare_to))


def run_migrations_online() -> None:
    url = config.attributes.get("url") or get_settings().database_url
    engine = create_engine(url)
    with engine.connect() as conn:
        context.configure(
            connection=conn,
            target_metadata=target_metadata,
            include_object=include_object,
            process_revision_directives=alembic_helpers.writer,
            render_item=alembic_helpers.render_item,
        )
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
