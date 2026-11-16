"""Repositories: the only place where the API runs SQL."""

from __future__ import annotations

from typing import Any

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from accessastana.db.repositories import read_df


class CityRepository:
    def __init__(self, session: Session) -> None:
        self.s = session

    def get(self, slug: str) -> dict[str, Any] | None:
        row = (
            self.s.execute(
                text(
                    "SELECT slug, name_en, name_ru, name_kk, h3_resolution, population_total FROM cities WHERE slug=:c"
                ),
                {"c": slug},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def all_slugs(self) -> list[str]:
        return list(self.s.scalars(text("SELECT slug FROM cities ORDER BY slug")))

    def climate_shares(self, slug: str) -> dict[str, float | None]:
        rows = self.s.execute(
            text("SELECT season, share_of_days FROM climate_profiles WHERE city_slug=:c"), {"c": slug}
        )
        return {r.season: r.share_of_days for r in rows}

    def districts_geojson(self, slug: str) -> dict[str, Any]:
        df = read_df(
            self.s,
            "SELECT id, name, name_en, ST_AsGeoJSON(geometry, 6) g FROM districts WHERE city_slug=:c "
            "ORDER BY name",
            c=slug,
        )
        return _fc(df, "g")


class AccessibilityRepository:
    def __init__(self, session: Session) -> None:
        self.s = session

    def cells(self, slug: str, season: str, categories: list[str]) -> pd.DataFrame:
        """Long table: h3, category, minutes, reachable, population, district."""
        return read_df(
            self.s,
            """SELECT a.h3, a.category, a.minutes, a.reachable, c.population, c.district_id,
                      d.name AS district
               FROM accessibility_results a
               JOIN h3_cells c ON c.city_slug = a.city_slug AND c.h3 = a.h3
               LEFT JOIN districts d ON d.id = c.district_id
               WHERE a.city_slug=:c AND a.season=:s AND a.category = ANY(:cats)""",
            c=slug,
            s=season,
            cats=categories,
        )

    def cells_geojson(self, slug: str) -> dict[str, str]:
        df = read_df(
            self.s, "SELECT h3, ST_AsGeoJSON(geometry, 6) g FROM h3_cells WHERE city_slug=:c", c=slug
        )
        return dict(zip(df.h3, df.g, strict=True))


class PoiRepository:
    def __init__(self, session: Session) -> None:
        self.s = session

    def geojson(self, slug: str, category: str | None) -> dict[str, Any]:
        df = read_df(
            self.s,
            """SELECT id, name, category, ST_AsGeoJSON(geometry, 6) g FROM pois
               WHERE city_slug=:c AND source='osm' AND (CAST(:cat AS text) IS NULL OR category=:cat) ORDER BY id""",
            c=slug,
            cat=category,
        )
        return _fc(df, "g")


def _fc(df: pd.DataFrame, geom_col: str) -> dict[str, Any]:
    import json

    props = [c for c in df.columns if c != geom_col]
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": json.loads(r[geom_col]),
                "properties": {k: _py(r[k]) for k in props},
            }
            for _, r in df.iterrows()
        ],
    }


def _py(v: Any) -> Any:
    return v.item() if hasattr(v, "item") else v
