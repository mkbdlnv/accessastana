"""Static figures for the paper (matplotlib, PNG, 200 dpi).

Colour rules: seasons are categorical identities and use the first three
slots of a CVD-validated palette, in fixed order. Maps are sequential
(magnitude), so they use one hue from light to dark, never a rainbow.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import h3
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from shapely.geometry import Polygon

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
SEASON_COLORS = {"summer": "#2a78d6", "winter": "#eb6834", "winter_severe": "#1baf7a"}
SEASON_LABELS = {"summer": "Summer", "winter": "Winter (typical)", "winter_severe": "Winter (severe cold)"}


def _style(ax: plt.Axes) -> None:
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def season_bars(by_season: pd.DataFrame, labels: dict[str, str], out: Path) -> Path:
    """Grouped bars: share of population reaching each category within the
    season's acceptable time."""
    seasons = [s for s in SEASON_COLORS if s in set(by_season.season)]
    cats = list(dict.fromkeys(by_season.category))
    fig, ax = plt.subplots(figsize=(9, 4.2), facecolor=SURFACE)
    _style(ax)
    width = 0.8 / len(seasons)
    for k, s in enumerate(seasons):
        sub = by_season[by_season.season == s].set_index("category").reindex(cats)
        xs = [i + (k - (len(seasons) - 1) / 2) * width for i in range(len(cats))]
        ax.bar(xs, sub["reachable"] * 100, width * 0.92, color=SEASON_COLORS[s], label=SEASON_LABELS[s])
    # Short labels: wrap at the first space/bracket so neighbours never collide.
    short = [
        labels.get(c, c).replace(" (", "\n(").replace("Public transport stops", "Transit\nstops")
        for c in cats
    ]
    ax.set_xticks(range(len(cats)), short, rotation=0, fontsize=9, color=INK)
    ax.set_ylabel("% of residents within acceptable walk", color=INK2, fontsize=9)
    ax.set_ylim(0, 100)
    ax.legend(frameon=False, fontsize=9, ncols=3, loc="upper left", bbox_to_anchor=(0, 1.12))
    fig.tight_layout()
    fig.savefig(out, dpi=200, facecolor=SURFACE)
    plt.close(fig)
    return out


def district_index_bars(districts: pd.DataFrame, out: Path) -> Path:
    seasons = [s for s in SEASON_COLORS if s in set(districts.season)]
    names = sorted(set(districts.district.dropna()) - {"—"})
    fig, ax = plt.subplots(figsize=(9, 4), facecolor=SURFACE)
    _style(ax)
    width = 0.8 / len(seasons)
    for k, s in enumerate(seasons):
        sub = districts[districts.season == s].set_index("district").reindex(names)
        xs = [i + (k - (len(seasons) - 1) / 2) * width for i in range(len(names))]
        ax.bar(xs, sub["index"], width * 0.92, color=SEASON_COLORS[s], label=SEASON_LABELS[s])
    ax.set_xticks(range(len(names)), names, fontsize=9, color=INK)
    ax.set_ylabel("15-minute index (population-weighted)", color=INK2, fontsize=9)
    ax.set_ylim(0, 1)
    ax.legend(frameon=False, fontsize=9, ncols=3, loc="upper left", bbox_to_anchor=(0, 1.12))
    fig.tight_layout()
    fig.savefig(out, dpi=200, facecolor=SURFACE)
    plt.close(fig)
    return out


def index_maps(cells_by_season: dict[str, pd.DataFrame], boundary: gpd.GeoSeries, out: Path) -> Path:
    """Small multiples: composite index per H3 cell, one panel per season,
    shared single-hue scale 0..1. Unpopulated cells are drawn light grey."""
    fig, axes = plt.subplots(
        1, len(cells_by_season), figsize=(5 * len(cells_by_season), 5), facecolor=SURFACE
    )
    axes = axes if len(cells_by_season) > 1 else [axes]
    for ax, (season, df) in zip(axes, cells_by_season.items(), strict=True):
        g = gpd.GeoDataFrame(
            df, geometry=[Polygon([(b, a) for a, b in h3.cell_to_boundary(c)]) for c in df.h3], crs=4326
        )
        g[g.population <= 0].plot(ax=ax, color="#ecebe7", linewidth=0)
        g[g.population > 0].plot(
            ax=ax, column="index", cmap="Blues", vmin=0, vmax=1, linewidth=0.2, edgecolor=SURFACE
        )
        boundary.boundary.plot(ax=ax, color=INK2, linewidth=0.6)
        ax.set_title(SEASON_LABELS.get(season, season), fontsize=10, color=INK)
        ax.set_axis_off()
    sm = plt.cm.ScalarMappable(cmap="Blues", norm=plt.Normalize(0, 1))
    cb = fig.colorbar(sm, ax=axes, shrink=0.6, location="right")
    cb.set_label("15-minute index (share of 7 categories reachable)", fontsize=9, color=INK2)
    fig.text(
        0.01, 0.01, "© OpenStreetMap contributors · Kontur Population (CC BY 4.0)", fontsize=7, color=INK2
    )
    fig.savefig(out, dpi=200, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    return out
