"""Assemble reports/<city>/: CSV tables, PNG figures, summary.md and report.pdf."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from accessastana.config import load_categories, load_city, load_seasons
from accessastana.db.repositories import read_df
from accessastana.db.session import session_scope
from accessastana.reporting import figures, tables
from accessastana.settings import get_settings

ATTRIBUTION = (
    "© OpenStreetMap contributors (ODbL). Population: Kontur Population (CC BY 4.0), calibrated to "
    "Bureau of National Statistics RK totals. Weather: Open-Meteo.com (CC BY 4.0)."
)


def _font() -> str:
    """Register DejaVu Sans (bundled with matplotlib) for Cyrillic/Kazakh text."""
    if "DejaVu" not in pdfmetrics.getRegisteredFontNames():
        ttf = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
        pdfmetrics.registerFont(TTFont("DejaVu", str(ttf / "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(ttf / "DejaVuSans-Bold.ttf")))
    return "DejaVu"


def collect(session: Session, slug: str, out_dir: Path) -> dict[str, Any]:
    """Compute all tables + figures and write CSV/PNG files."""
    out_dir.mkdir(parents=True, exist_ok=True)
    labels = {k: c.label for k, c in load_categories().items()}
    wide = tables.accessibility_wide(session, slug)
    if wide.empty:
        raise LookupError(f"no accessibility results for {slug}; run `accessastana analyze all` first")
    climate = read_df(
        session,
        "SELECT season, speed_mps, max_minutes, share_of_days, stats FROM climate_profiles "
        "WHERE city_slug=:c",
        c=slug,
    )
    runs = read_df(
        session,
        """SELECT DISTINCT ON (loader) loader, source_version, left(checksum, 12) checksum,
                                      finished_at::date AS date, rows FROM import_runs
                               WHERE city_slug=:c AND status='success' ORDER BY loader, finished_at DESC""",
        c=slug,
    )
    t: dict[str, pd.DataFrame] = {
        "data_versions": runs,
        "data_summary": tables.data_summary(session, slug),
        "climate_profiles": climate.drop(columns="stats"),
        "accessibility_by_season": tables.by_season(wide),
    }
    t["climate_comparison"] = tables.climate_comparison(t["accessibility_by_season"], climate)
    t["districts"] = tables.districts(wide)
    t["severe_sensitivity"] = tables.severe_sensitivity(wide)
    for name, df in t.items():
        df.to_csv(out_dir / f"{name}.csv", index=False)

    boundary = gpd.GeoSeries.from_wkt(
        read_df(session, "SELECT ST_AsText(boundary) w FROM cities WHERE slug=:c", c=slug).w, crs=4326
    )
    figs = {
        "season_bars": figures.season_bars(
            t["accessibility_by_season"], labels, out_dir / "fig_season_bars.png"
        ),
        "district_index": figures.district_index_bars(t["districts"], out_dir / "fig_district_index.png"),
        "index_maps": figures.index_maps(
            {s: tables.cell_index(wide, s) for s in load_seasons().api_seasons},
            boundary,
            out_dir / "fig_index_maps.png",
        ),
    }
    return {"tables": t, "figures": figs, "labels": labels, "climate": climate}


def write_markdown(slug: str, data: dict[str, Any], out: Path) -> None:
    """Write reports/<city>/summary.md with all tables."""
    t = data["tables"]
    cc = t["climate_comparison"]
    lines = [
        f"# AccessAstana report: {slug}",
        "",
        ATTRIBUTION,
        "",
        "## Data versions",
        t["data_versions"].to_markdown(index=False),
        "",
        "## Data summary",
        t["data_summary"].to_markdown(index=False),
        "",
        "## Climate profiles",
        t["climate_profiles"].to_markdown(index=False),
        "",
        "## Share of residents within the acceptable walk (by season)",
        t["accessibility_by_season"].round(3).to_markdown(index=False),
        "",
        f"## Summer vs winter (share of severe-cold winter days: {cc.attrs.get('p_severe', 0):.1%})",
        cc.round(3).to_markdown(index=False),
        "",
        "## Sensitivity: acceptable walk on severe-cold days (assumed 10 min)",
        t["severe_sensitivity"].round(3).to_markdown(index=False),
        "",
        "## Districts",
        t["districts"].round(3).to_markdown(index=False),
        "",
        "![](fig_season_bars.png)",
        "![](fig_district_index.png)",
        "![](fig_index_maps.png)",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")


def _table(df: pd.DataFrame, font: str, pct_cols: tuple[str, ...] = ()) -> Table:
    def fmt(col: str, v: Any) -> str:
        if isinstance(v, float):
            if (
                col in pct_cols
                or col.endswith("reachable")
                or col.startswith("within_")
                or col in {"summer", "winter_typical", "winter_severe", "winter_expected"}
            ):
                return f"{v:.1%}" if pd.notna(v) else "—"
            return f"{v:,.2f}" if pd.notna(v) else "—"
        return str(v)

    data = [list(df.columns)] + [
        [fmt(c, v) for c, v in zip(df.columns, row, strict=True)] for row in df.itertuples(index=False)
    ]
    tbl = Table(data, repeatRows=1)
    tbl.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), font, 7),
                ("FONT", (0, 0), (-1, 0), f"{font}-Bold", 7),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#52514e")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f3f0")]),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ]
        )
    )
    return tbl


def write_pdf(slug: str, data: dict[str, Any], out: Path) -> Path:
    """Write reports/<city>/report.pdf (Cyrillic-capable font)."""
    font = _font()
    st = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=st["Heading1"], fontName=f"{font}-Bold", fontSize=16)
    h2 = ParagraphStyle("h2", parent=st["Heading2"], fontName=f"{font}-Bold", fontSize=12)
    body = ParagraphStyle("b", parent=st["BodyText"], fontName=font, fontSize=8.5, leading=11)
    t, city = data["tables"], load_city(slug)
    cc = t["climate_comparison"]
    dist = t["districts"]
    dist_short = dist[["season", "district", "population", "index"]]
    story: list[Any] = [
        Paragraph(f"AccessAstana — {city.name.get('en', slug)}", h1),
        Paragraph("Climate-adjusted walking accessibility of social infrastructure (open data).", body),
        Paragraph(ATTRIBUTION, body),
        Spacer(1, 8),
        Paragraph("1. Data versions", h2),
        _table(t["data_versions"], font),
        Spacer(1, 6),
        Paragraph("2. Data summary", h2),
        _table(t["data_summary"], font),
        Spacer(1, 6),
        Paragraph("3. Season profiles", h2),
        Paragraph(
            "Walking speed and acceptable one-way time per profile (config/seasons.yaml, with references). "
            "share_of_days = share of December–February days in this profile, from Open-Meteo 2015–2024.",
            body,
        ),
        _table(t["climate_profiles"], font, pct_cols=("share_of_days",)),
        Spacer(1, 6),
        Paragraph("4. Accessibility by season (city, population-weighted)", h2),
        _table(t["accessibility_by_season"].replace({"category": data["labels"]}), font),
        Spacer(1, 6),
        Image(str(data["figures"]["season_bars"]), width=17 * cm, height=7.9 * cm),
        Paragraph(
            f"5. Summer vs winter. Expected winter day = mix of typical and severe profiles "
            f"(severe share {cc.attrs.get('p_severe', 0):.1%}).",
            h2,
        ),
        _table(cc.replace({"category": data["labels"]}), font),
        Spacer(1, 6),
        Paragraph("5a. Sensitivity of the severe-cold result to the assumed 10-minute walk", h2),
        _table(t["severe_sensitivity"].replace({"category": data["labels"]}), font),
        Spacer(1, 6),
        Paragraph("6. Districts", h2),
        _table(dist_short, font),
        Spacer(1, 6),
        Image(str(data["figures"]["district_index"]), width=17 * cm, height=7.5 * cm),
        Image(str(data["figures"]["index_maps"]), width=17 * cm, height=5.6 * cm),
        Spacer(1, 8),
        Paragraph(
            "Limitations: population is a model (Kontur) rescaled to official totals; walking speeds are "
            "transferred from Nordic observational studies; OSM completeness is not verified against official registries; sidewalk snow clearance is not observed; "
            "H3 centroids represent whole cells (~0.74 km²).",
            body,
        ),
    ]
    SimpleDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.4 * cm,
        title=f"AccessAstana {slug}",
    ).build(story)
    return out


def build_report(
    slug: str, database_url: str | None = None, out_root: Path | None = None, docs_dir: Path | None = None
) -> Path:
    """Write reports/<slug>/ (CSV, PNG, summary.md, report.pdf).

    If `docs_dir` is given, also regenerate docs/results-<slug>.md, so the numbers
    quoted in the documentation always come from the same run (never typed by hand).
    """
    out_dir = (out_root or get_settings().project_root / "reports") / slug
    with session_scope(database_url) as s:
        data = collect(s, slug, out_dir)
    write_markdown(slug, data, out_dir / "summary.md")
    if docs_dir is not None:
        from accessastana.reporting.results_doc import write_results_doc

        write_results_doc(slug, data, docs_dir / f"results-{slug}.md")
    return write_pdf(slug, data, out_dir / "report.pdf")
