"""Database schema (SQLAlchemy 2 + GeoAlchemy2). Migrations live in migrations/.

Conventions
- All geometries are EPSG:4326. Metric computations reproject in Python using
  the city's `metric_crs`.
- H3 indexes are stored as text (e.g. '882c2a2a9dfffff') and computed in
  Python with the `h3` library. We decided NOT to depend on the h3-pg
  extension: the official postgis/postgis image does not ship it, and all
  H3 work (polyfill, centroids) happens offline during ingestion anyway.
- Every row produced by an import carries `import_run_id`, so re-imports are
  idempotent: delete the rows of the previous run for this city/source, then
  insert the new ones, in one transaction.
"""

from datetime import datetime
from typing import Any, ClassVar

from geoalchemy2 import Geometry
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    type_annotation_map: ClassVar[dict[Any, Any]] = {dict[str, Any]: JSON}


class City(Base):
    __tablename__ = "cities"
    slug: Mapped[str] = mapped_column(String(64), primary_key=True)
    name_en: Mapped[str] = mapped_column(String(128))
    name_ru: Mapped[str] = mapped_column(String(128))
    name_kk: Mapped[str] = mapped_column(String(128))
    boundary = mapped_column(Geometry("MULTIPOLYGON", srid=4326), nullable=False)
    h3_resolution: Mapped[int] = mapped_column(Integer, default=8)
    metric_crs: Mapped[str] = mapped_column(String(32))
    population_total: Mapped[float | None] = mapped_column(Float)


class ImportRun(Base):
    """Audit log of imports: which loader, which source file version, when."""

    __tablename__ = "import_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Deliberately no FK: the boundary import creates the city row, and its
    # own audit record must be writable before that row exists.
    city_slug: Mapped[str] = mapped_column(String(64))
    loader: Mapped[str] = mapped_column(String(64))
    source_version: Mapped[str] = mapped_column(String(256))  # e.g. file name + date
    checksum: Mapped[str] = mapped_column(String(64))  # sha256 of input file(s) + config
    status: Mapped[str] = mapped_column(String(16), default="running")  # running|success|failed
    rows: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class District(Base):
    __tablename__ = "districts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_slug: Mapped[str] = mapped_column(ForeignKey("cities.slug", ondelete="CASCADE"), index=True)
    osm_id: Mapped[int | None] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(String(128))
    name_en: Mapped[str | None] = mapped_column(String(128))
    geometry = mapped_column(Geometry("MULTIPOLYGON", srid=4326), nullable=False)


class H3Cell(Base):
    __tablename__ = "h3_cells"
    city_slug: Mapped[str] = mapped_column(ForeignKey("cities.slug", ondelete="CASCADE"), primary_key=True)
    h3: Mapped[str] = mapped_column(String(16), primary_key=True)
    district_id: Mapped[int | None] = mapped_column(ForeignKey("districts.id", ondelete="SET NULL"))
    population_raw: Mapped[float] = mapped_column(Float, default=0)  # Kontur as published
    population: Mapped[float] = mapped_column(Float, default=0)  # calibrated (see ingestion/kontur.py)
    geometry = mapped_column(Geometry("POLYGON", srid=4326), nullable=False)
    centroid = mapped_column(Geometry("POINT", srid=4326), nullable=False)
    import_run_id: Mapped[int | None] = mapped_column(ForeignKey("import_runs.id", ondelete="SET NULL"))


class NetworkNode(Base):
    __tablename__ = "network_nodes"
    city_slug: Mapped[str] = mapped_column(ForeignKey("cities.slug", ondelete="CASCADE"), primary_key=True)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # OSM node id
    geometry = mapped_column(Geometry("POINT", srid=4326), nullable=False)
    import_run_id: Mapped[int | None] = mapped_column(ForeignKey("import_runs.id", ondelete="SET NULL"))


class NetworkEdge(Base):
    """Undirected pedestrian edge (one row per OSMnx-simplified edge)."""

    __tablename__ = "network_edges"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    city_slug: Mapped[str] = mapped_column(ForeignKey("cities.slug", ondelete="CASCADE"), index=True)
    u: Mapped[int] = mapped_column(BigInteger)
    v: Mapped[int] = mapped_column(BigInteger)
    length_m: Mapped[float] = mapped_column(Float)
    highway: Mapped[str | None] = mapped_column(String(64))
    geometry = mapped_column(Geometry("LINESTRING", srid=4326), nullable=False)
    import_run_id: Mapped[int | None] = mapped_column(ForeignKey("import_runs.id", ondelete="SET NULL"))


class Poi(Base):
    __tablename__ = "pois"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_slug: Mapped[str] = mapped_column(ForeignKey("cities.slug", ondelete="CASCADE"))
    source: Mapped[str] = mapped_column(String(16))  # 'osm' (column kept for future sources)
    category: Mapped[str] = mapped_column(String(32))
    external_id: Mapped[str] = mapped_column(String(64))  # e.g. 'way/123'
    name: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)
    attrs: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    # Representative point used for routing. For parks additional destination
    # points (boundary samples) are stored in attrs['access_points'].
    geometry = mapped_column(Geometry("POINT", srid=4326), nullable=False)
    import_run_id: Mapped[int | None] = mapped_column(ForeignKey("import_runs.id", ondelete="SET NULL"))
    __table_args__ = (
        UniqueConstraint("city_slug", "source", "external_id", "category", name="uq_poi_source_id"),
        Index("ix_pois_city_cat_src", "city_slug", "category", "source"),
    )


class AccessibilityResult(Base):
    __tablename__ = "accessibility_results"
    city_slug: Mapped[str] = mapped_column(ForeignKey("cities.slug", ondelete="CASCADE"), primary_key=True)
    h3: Mapped[str] = mapped_column(String(16), primary_key=True)
    category: Mapped[str] = mapped_column(String(32), primary_key=True)
    season: Mapped[str] = mapped_column(String(32), primary_key=True)
    # None = no facility reachable within the routing cutoff.
    minutes: Mapped[float | None] = mapped_column(Float)
    reachable: Mapped[bool] = mapped_column(Boolean)
    nearest_poi_id: Mapped[int | None] = mapped_column(Integer)
    __table_args__ = (Index("ix_acc_city_cat_season", "city_slug", "category", "season"),)


class ClimateProfile(Base):
    """Season profiles actually used, plus the share of days they represent
    (from Open-Meteo statistics), stored for reproducibility and the report."""

    __tablename__ = "climate_profiles"
    city_slug: Mapped[str] = mapped_column(ForeignKey("cities.slug", ondelete="CASCADE"), primary_key=True)
    season: Mapped[str] = mapped_column(String(32), primary_key=True)
    speed_mps: Mapped[float] = mapped_column(Float)
    max_minutes: Mapped[float] = mapped_column(Float)
    share_of_days: Mapped[float | None] = mapped_column(Float)
    stats: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class Scenario(Base):
    __tablename__ = "scenarios"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_slug: Mapped[str] = mapped_column(ForeignKey("cities.slug", ondelete="CASCADE"))
    name: Mapped[str | None] = mapped_column(String(256))
    category: Mapped[str] = mapped_column(String(32))
    season: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class ScenarioFacility(Base):
    __tablename__ = "scenario_facilities"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id", ondelete="CASCADE"), index=True)
    action: Mapped[str] = mapped_column(String(8))  # add | remove
    poi_id: Mapped[int | None] = mapped_column(Integer)  # for remove
    geometry = mapped_column(Geometry("POINT", srid=4326))  # for add
