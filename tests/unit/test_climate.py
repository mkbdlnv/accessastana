"""Wind chill and season-profile classification."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from accessastana.analysis.climate import classify_days, climate_summary, profile_shares, wind_chill
from accessastana.config import load_seasons


def test_wind_chill_matches_eccc_table() -> None:
    # ECCC wind-chill chart: T = -20 °C, V = 30 km/h → about -33
    assert wind_chill(np.array([-20.0]), np.array([30.0]))[0] == pytest.approx(-32.6, abs=0.1)
    # Outside the validity range the air temperature is returned
    assert wind_chill(np.array([15.0, -5.0]), np.array([30.0, 2.0])).tolist() == [15.0, -5.0]


def test_classify_days_and_shares() -> None:
    seasons = load_seasons()
    idx = pd.to_datetime(["2020-01-01", "2020-01-02", "2020-07-01", "2020-04-01"])
    daily = pd.DataFrame(
        {
            "temperature_2m_min": [-30.0, -5.0, 15.0, 0.0],
            "wind_speed_10m_mean": [20.0, 5.0, 5.0, 5.0],
            "temperature_2m_mean": [-25.0, 0.0, 20.0, 5.0],
        },
        index=idx,
    )
    labels = classify_days(daily, seasons)
    assert labels.tolist()[:3] == ["winter_severe", "winter", "summer"]
    assert pd.isna(labels.iloc[3])  # April is in no profile
    assert profile_shares(labels, [12, 1, 2]) == {"winter_severe": 0.5, "winter": 0.5}
    assert profile_shares(labels, [3]) == {}
    s = climate_summary(daily.reset_index(names="time"), [1])
    assert s["days"] == 2 and s["days_wind_chill_le_-28"] == 1
