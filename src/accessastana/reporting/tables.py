"""Report tables computed from the DB."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from accessastana.analysis.accessibility import (
    composite_index,
    share_within,
    summarize_groups,
    threshold_sensitivity,
)
from accessastana.config import load_categories, load_seasons
from accessastana.db.repositories import read_df


def accessibility_wide(session: Session, slug: str) -> pd.DataFrame:
    """Cells × (season, category) minutes, plus population and district."""
    df = read_df(
        session,
        """SELECT a.h3, a.season, a.category, a.minutes, c.population, d.name AS district
           FROM accessibility_results a JOIN h3_cells c ON c.city_slug=a.city_slug AND c.h3=a.h3
           LEFT JOIN districts d ON d.id=c.district_id WHERE a.city_slug=:c""",
        c=slug,
    )
    df["minutes"] = df["minutes"].astype(float).fillna(np.inf)
    return df


def data_summary(session: Session, slug: str) -> pd.DataFrame:
    """Counts of cells, population, network and POIs (data inventory table)."""
    q = read_df(
        session,
        """
        SELECT (SELECT count(*) FROM h3_cells WHERE city_slug=:c) AS h3_cells,
               (SELECT count(*) FROM h3_cells WHERE city_slug=:c AND population > 0) AS populated_cells,
               (SELECT round(sum(population_raw)) FROM h3_cells WHERE city_slug=:c) AS population_kontur,
               (SELECT round(sum(population)) FROM h3_cells WHERE city_slug=:c) AS population_calibrated,
               (SELECT count(*) FROM network_nodes WHERE city_slug=:c) AS network_nodes,
               (SELECT round(sum(length_m)/1000) FROM network_edges WHERE city_slug=:c) AS network_km,
               (SELECT count(*) FROM districts WHERE city_slug=:c) AS districts""",
        c=slug,
    )
    pois = read_df(
        session, "SELECT category, source, count(*) n FROM pois WHERE city_slug=:c GROUP BY 1,2", c=slug
    )
    rows: list[tuple[str, Any]] = list(q.iloc[0].items())
    rows += [
        (f"pois_{r.source}_{r.category}", r.n) for r in pois.sort_values(["source", "category"]).itertuples()
    ]
    return pd.DataFrame(rows, columns=["metric", "value"])


def by_season(wide: pd.DataFrame) -> pd.DataFrame:
    """City-level share of population within each threshold, by category × season."""
    seasons = load_seasons()
    rows = []
    for (cat, season), g in wide.groupby(["category", "season"]):
        m, p = g["minutes"].to_numpy(), g["population"].to_numpy()
        prof = seasons.profiles[season]
        row = {"category": cat, "season": season, "max_minutes": prof.max_minutes}
        row |= {f"within_{int(t)}": share_within(m, p, t) for t in seasons.summary_thresholds}
        row["reachable"] = share_within(m, p, prof.max_minutes)
        rows.append(row)
    return pd.DataFrame(rows)


def climate_comparison(by_season_df: pd.DataFrame, climate: pd.DataFrame) -> pd.DataFrame:
    """Summer vs winter, with an 'expected winter day' = day-weighted mix of
    typical and severe winter profiles (shares from Open-Meteo statistics)."""
    piv = by_season_df.pivot(index="category", columns="season", values="reachable")
    shares = climate.set_index("season")["share_of_days"].to_dict()
    p_sev = float(shares.get("winter_severe") or 0.0)
    out = pd.DataFrame(
        {
            "summer": piv.get("summer"),
            "winter_typical": piv.get("winter"),
            "winter_severe": piv.get("winter_severe"),
        }
    )
    out["winter_expected"] = (1 - p_sev) * out["winter_typical"] + p_sev * out["winter_severe"]
    out["loss_expected_pp"] = 100 * (out["summer"] - out["winter_expected"])
    out["loss_severe_pp"] = 100 * (out["summer"] - out["winter_severe"])
    out.attrs["p_severe"] = p_sev
    return out.reset_index()


SEVERE_THRESHOLDS = (8.0, 10.0, 12.0)  # ±2 min around the assumed 10 min (config/seasons.yaml)


def severe_sensitivity(wide: pd.DataFrame, thresholds: tuple[float, ...] = SEVERE_THRESHOLDS) -> pd.DataFrame:
    """Severe-cold profile: share of residents reached for alternative acceptable
    times. The 10-minute value is a team assumption, so the report shows how much
    the result moves if it is 8 or 12 minutes instead."""
    sub = wide[wide.season == "winter_severe"]
    rows = []
    for cat, g in sub.groupby("category"):
        shares = threshold_sensitivity(g["minutes"].to_numpy(), g["population"].to_numpy(), thresholds)
        rows.append({"category": cat, **{f"within_{int(t)}": v for t, v in shares.items()}})
    out = pd.DataFrame(rows)
    if not out.empty:
        lo, hi = f"within_{int(thresholds[0])}", f"within_{int(thresholds[-1])}"
        out["range_pp"] = 100 * (out[hi] - out[lo])
    return out


def season_cells(wide: pd.DataFrame, season: str) -> pd.DataFrame:
    """One row per cell: population, district, one minutes column per category
    and the composite index for `season`.

    Pivot on h3 ONLY and join attributes afterwards: pivoting on several index
    levels with dropna=False would build their Cartesian product (a bug we hit).
    """
    cats = list(load_categories())
    prof = load_seasons().profiles[season]
    sub = wide[wide.season == season]
    mins = sub.pivot(index="h3", columns="category", values="minutes").reindex(columns=cats).fillna(np.inf)
    meta = sub.drop_duplicates("h3").set_index("h3")[["population", "district"]]
    w = meta.join(mins).reset_index()
    w["index"] = composite_index(w[cats], prof.max_minutes)
    return w


def districts(wide: pd.DataFrame) -> pd.DataFrame:
    """Per-district index and reachable shares for every API season."""
    seasons = load_seasons()
    cats = list(load_categories())
    frames = []
    for season in seasons.api_seasons:
        prof = seasons.profiles[season]
        w = season_cells(wide, season)
        w["district"] = w["district"].fillna("—")
        t = summarize_groups(w, cats, seasons.summary_thresholds, prof.max_minutes)
        frames.append(
            t[["district", "population", "index", *[f"{c}__reachable" for c in cats]]].assign(season=season)
        )
    return pd.concat(frames, ignore_index=True)


def cell_index(wide: pd.DataFrame, season: str) -> pd.DataFrame:
    """Composite index per cell for one season (for the maps)."""
    return season_cells(wide, season)[["h3", "population", "index"]]
