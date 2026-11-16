"""Generate docs/results-<city>.md from the report tables.

Every number in that document comes from the same `collect()` run as the PDF,
so documentation and report cannot drift apart. Edit this generator, not the
generated file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from accessastana.config import load_seasons


def _pct(v: Any) -> str:
    return "—" if v is None or pd.isna(v) else f"{100 * float(v):.1f}%"


def write_results_doc(slug: str, data: dict[str, Any], out: Path) -> Path:
    """Write docs/results-<city>.md from the collected report data."""
    t, labels = data["tables"], data["labels"]
    seasons = load_seasons()
    climate = t["climate_profiles"].set_index("season")
    cc = t["climate_comparison"].set_index("category")
    sens = t["severe_sensitivity"].set_index("category")
    p_sev = float(cc.attrs.get("p_severe", t["climate_comparison"].attrs.get("p_severe", 0.0)))
    summary = dict(zip(t["data_summary"].metric, t["data_summary"].value, strict=True))
    versions = t["data_versions"]

    lines = [
        f"# Results: {slug.capitalize()}",
        "",
        "> **Generated file**: `accessastana report` regenerates it from the database",
        "> (`src/accessastana/reporting/results_doc.py`). Do not edit by hand.",
        "",
        "All shares are **population-weighted shares of residents** "
        f"(calibrated population total: {float(summary.get('population_calibrated', 0)):,.0f}; "
        f"Kontur original: {float(summary.get('population_kontur', 0)):,.0f}). "
        "The results assume OpenStreetMap is complete (the registry comparison is out of scope).",
        "",
        "## Data versions",
        "",
        versions.to_markdown(index=False),
        "",
        "## Season profiles (config/seasons.yaml)",
        "",
        "| Profile | Speed (m/s) | Acceptable one-way walk (min) | Share of Dec–Feb days |",
        "|---|---:|---:|---:|",
    ]
    for key in seasons.api_seasons:
        prof = seasons.profiles[key]
        share = climate["share_of_days"].get(key) if key != "summer" else None
        lines.append(f"| {prof.label} | {prof.speed_mps} | {prof.max_minutes:g} | {_pct(share)} |")
    lines += [
        "",
        "## Share of residents within the acceptable walk",
        "",
        "| Category | Summer | Winter (typical) | Winter (severe) | Expected winter day* | Loss vs summer (pp) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for cat, r in cc.sort_values("summer", ascending=False).iterrows():
        lines.append(
            f"| {labels.get(cat, cat)} | {_pct(r.summer)} | {_pct(r.winter_typical)} | {_pct(r.winter_severe)} "
            f"| {_pct(r.winter_expected)} | −{r.loss_expected_pp:.1f} |"
        )
    lines += [
        "",
        f"\\* Expected winter day = {1 - p_sev:.3f} · typical + {p_sev:.3f} · severe "
        "(shares of December–February days from Open-Meteo 2015–2024).",
        "",
        "## Sensitivity to the assumed severe-cold walk (10 min)",
        "",
        "| Category | ≤ 8 min | ≤ 10 min (assumed) | ≤ 12 min | Range (pp) |",
        "|---|---:|---:|---:|---:|",
    ]
    for cat, r in sens.sort_values("within_10", ascending=False).iterrows():
        lines.append(
            f"| {labels.get(cat, cat)} | {_pct(r.within_8)} | {_pct(r.within_10)} | {_pct(r.within_12)} "
            f"| {r.range_pp:.1f} |"
        )
    d = t["districts"]
    d = d[d.district != "—"]
    piv = d.pivot(index="district", columns="season", values="index")
    pop = d.drop_duplicates("district").set_index("district")["population"]
    lines += [
        "",
        "## 15-minute index by district (share of 7 categories within the walk)",
        "",
        "| District | Population (calibrated) | Summer | Winter | Severe cold |",
        "|---|---:|---:|---:|---:|",
    ]
    for name in piv.sort_values("summer", ascending=False).index:
        r = piv.loc[name]
        lines.append(
            f"| {name} | {pop[name]:,.0f} | {r.get('summer', float('nan')):.2f} | "
            f"{r.get('winter', float('nan')):.2f} | {r.get('winter_severe', float('nan')):.2f} |"
        )
    lines += [
        "",
        "## Caveats",
        "",
        "1. OSM completeness is not verified. Missing facilities in OSM make accessibility look worse than it is.",
        "2. Population: one city-wide calibration factor. District totals from BNS would capture uneven growth.",
        "3. Walking-speed factors are transferred from Norwegian observations (Fossum & Ryeng, 2021).",
        "4. The 10-minute severe-cold walk is an assumption; see the sensitivity table above.",
        "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")
    return out
