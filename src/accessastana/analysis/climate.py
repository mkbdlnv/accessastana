"""Climate statistics → season profiles.

Walking speeds and acceptable times per profile come from config/seasons.yaml
(with literature references). This module only:
1. computes the wind-chill index per day, and
2. classifies each winter day into a profile and reports the share of days,
   so "expected winter accessibility" can be a day-weighted mix of profiles.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from accessastana.config import SeasonsConfig


def wind_chill(temp_c: np.ndarray | pd.Series, wind_kmh: np.ndarray | pd.Series) -> np.ndarray:
    """Wind-chill index (ECCC / US NWS 2001 formula, °C-equivalent).

        WCI = 13.12 + 0.6215 T − 11.37 V^0.16 + 0.3965 T V^0.16

    with T = air temperature (°C) and V = wind speed at 10 m (km/h). The
    formula is defined only for T ≤ 10 °C and V ≥ 4.8 km/h; outside that range
    the air temperature itself is returned.
    """
    t = np.asarray(temp_c, dtype=float)
    v = np.asarray(wind_kmh, dtype=float)
    v16 = np.power(np.clip(v, 0, None), 0.16)
    wci = 13.12 + 0.6215 * t - 11.37 * v16 + 0.3965 * t * v16
    valid = (t <= 10) & (v >= 4.8)
    return np.where(valid, wci, t)


def classify_days(daily: pd.DataFrame, seasons: SeasonsConfig) -> pd.Series:
    """Assign each day to a season profile.

    `daily` needs a datetime index (or a 'time' column), 'temperature_2m_min'
    and 'wind_speed_10m_mean'. Profiles are tried in config order; within the
    profiles that share a month, the first one whose `day_rule` matches wins,
    and a profile with an empty rule is the fallback.
    Supported rule keys: `wind_chill_max` (day matches if WCI <= value).
    """
    df = daily.copy()
    if "time" in df.columns:
        df.index = pd.to_datetime(df["time"])
    wci = pd.Series(wind_chill(df["temperature_2m_min"], df["wind_speed_10m_mean"]), index=df.index)
    result = pd.Series(pd.NA, index=df.index, dtype="object")
    months = df.index.month
    # Specific rules first, fallbacks (empty/None rule) last.
    ordered = sorted(seasons.profiles.items(), key=lambda kv: 0 if kv[1].day_rule else 1)
    for key, prof in ordered:
        mask = np.isin(months, prof.months) & result.isna().to_numpy()
        rule = prof.day_rule or {}
        if "wind_chill_max" in rule:
            mask &= (wci <= rule["wind_chill_max"]).to_numpy()
        result[mask] = key
    return result


def profile_shares(labels: pd.Series, months: list[int]) -> dict[str, float]:
    """Share of days per profile among days in `months` (e.g. DJF)."""
    sub = labels[np.isin(pd.DatetimeIndex(labels.index).month, months)].dropna()
    if sub.empty:
        return {}
    return {str(k): round(float(v), 4) for k, v in sub.value_counts(normalize=True).items()}


def climate_summary(daily: pd.DataFrame, months: list[int]) -> dict[str, float]:
    df = daily.copy()
    if "time" in df.columns:
        df.index = pd.to_datetime(df["time"])
    sub = df[np.isin(df.index.month, months)]
    wci = wind_chill(sub["temperature_2m_min"], sub["wind_speed_10m_mean"])
    return {
        "days": len(sub),
        "temp_mean_c": round(float(sub["temperature_2m_mean"].mean()), 1),
        "temp_min_p10_c": round(float(sub["temperature_2m_min"].quantile(0.1)), 1),
        "wind_mean_kmh": round(float(sub["wind_speed_10m_mean"].mean()), 1),
        "wind_chill_p10": round(float(np.nanpercentile(wci, 10)), 1),
        "days_wind_chill_le_-28": int((wci <= -28).sum()),
        "snowfall_days": int((sub.get("snowfall_sum", pd.Series(dtype=float)) > 0).sum()),
    }
