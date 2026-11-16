"""Common loader interface.

Design patterns (to defend orally):
- **Strategy**: every data source (OSM network, OSM POIs, Kontur,
  Open-Meteo...) is a concrete `BaseLoader`. The CLI selects one by name from
  `LOADERS` and does not know source-specific details.
- **Template Method**: `BaseLoader.run()` fixes the import algorithm (compute
  checksum → skip if already imported → extract → replace old rows → record
  the run). Subclasses implement only `source_files()`, `extract()` and `load()`.

Idempotency and versioning: a run is identified by the SHA-256 of the input
files plus the relevant config. If a successful run with the same checksum
exists, the import is skipped (unless --force). Otherwise the previous rows of
this loader for this city are deleted and the new ones inserted in ONE
transaction, so a failed import never leaves half-written data.
"""

from __future__ import annotations

import hashlib
import json
import logging
from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

from sqlalchemy import Table, insert, select
from sqlalchemy.orm import Session

from accessastana.config import CityConfig
from accessastana.db.models import ImportRun
from accessastana.db.session import get_sessionmaker

log = logging.getLogger(__name__)


@dataclass
class LoadContext:
    city: CityConfig
    project_root: Path
    database_url: str | None = None
    force: bool = False
    config_dir: Path | None = None

    @property
    def config_path(self) -> Path:
        from accessastana.settings import get_settings

        return self.config_dir or get_settings().config_dir

    def path(self, relative: str) -> Path:
        p = Path(relative)
        return p if p.is_absolute() else self.project_root / p


@dataclass
class LoadResult:
    loader: str
    skipped: bool
    rows: int = 0
    details: dict[str, Any] = field(default_factory=dict)


def sha256_files(paths: Iterable[Path], extra: str = "") -> str:
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(p.name.encode())
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    h.update(extra.encode())
    return h.hexdigest()


class BaseLoader(ABC):
    name: ClassVar[str]

    def __init__(self, ctx: LoadContext) -> None:
        self.ctx = ctx

    # ---- to implement -------------------------------------------------------
    @abstractmethod
    def source_files(self) -> list[Path]:
        """Input files whose content defines the data version."""

    @abstractmethod
    def extract(self) -> Any:
        """Read + transform inputs into in-memory data (no DB writes)."""

    @abstractmethod
    def load(self, session: Session, data: Any, run_id: int) -> tuple[int, dict[str, Any]]:
        """Replace this loader's rows for the city. Returns (rows, details)."""

    # ---- optional hooks -----------------------------------------------------
    def config_fingerprint(self) -> str:
        """Config that affects the output (included in the checksum)."""
        return json.dumps(self.ctx.city.model_dump(), sort_keys=True, default=str)

    def source_version(self) -> str:
        return ", ".join(p.name for p in self.source_files())

    # ---- template method ----------------------------------------------------
    def run(self) -> LoadResult:
        files = self.source_files()
        missing = [str(p) for p in files if not p.exists()]
        if missing:
            raise FileNotFoundError(f"{self.name}: missing input files: {missing}")
        checksum = sha256_files(files, self.config_fingerprint())
        make_session = get_sessionmaker(self.ctx.database_url)
        with make_session() as s:
            done = s.scalar(
                select(ImportRun.id).where(
                    ImportRun.city_slug == self.ctx.city.slug,
                    ImportRun.loader == self.name,
                    ImportRun.checksum == checksum,
                    ImportRun.status == "success",
                )
            )
        if done and not self.ctx.force:
            log.info("%s: inputs unchanged (run %s) — skipping", self.name, done)
            return LoadResult(self.name, skipped=True)

        log.info("%s: extracting %s", self.name, self.source_version())
        data = self.extract()
        with make_session() as s, s.begin():
            run = ImportRun(
                city_slug=self.ctx.city.slug,
                loader=self.name,
                source_version=self.source_version()[:256],
                checksum=checksum,
                status="running",
            )
            s.add(run)
            s.flush()
            rows, details = self.load(s, data, run.id)
            run.status, run.rows, run.details = "success", rows, details
            run.finished_at = datetime.now(UTC)
        log.info("%s: loaded %d rows", self.name, rows)
        return LoadResult(self.name, skipped=False, rows=rows, details=details)


def bulk_insert(session: Session, table: Table, records: Sequence[dict[str, Any]], chunk: int = 5000) -> int:
    """Fast multi-row insert. Geometry values are passed as EWKT strings
    ('SRID=4326;POINT(71 51)'), which PostGIS casts implicitly."""
    for i in range(0, len(records), chunk):
        session.execute(insert(table), list(records[i : i + chunk]))
    return len(records)


def ewkt(geom: Any) -> str:
    return f"SRID=4326;{geom.wkt}"
