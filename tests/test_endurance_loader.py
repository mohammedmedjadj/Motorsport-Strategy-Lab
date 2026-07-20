"""Endurance loader: normalisation contract and the real-data invariants that
distinguish endurance strategy from F1 (pit visits vs tyre changes vs driver
stints). Runs offline against the materialised races in data/derived/endurance.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.data.base_loader import LAP_COLUMNS
from src.data.endurance_loader import (
    EnduranceLoader,
    green_lap_times,
    slugify,
)
from src.data.unified_loader import get_loader

IMSA = ("imsa", 2023, "Watkins Glen", "GTP")
WEC = ("wec", 2024, "Spa", "HYPERCAR")


@pytest.fixture(scope="module")
def imsa_laps() -> pd.DataFrame:
    series, year, event, cls = IMSA
    return EnduranceLoader(series).load_laps(year, event, cls)


@pytest.fixture(scope="module")
def wec_laps() -> pd.DataFrame:
    series, year, event, cls = WEC
    return EnduranceLoader(series).load_laps(year, event, cls)


def test_both_series_normalise_to_the_same_schema(imsa_laps, wec_laps) -> None:
    assert tuple(imsa_laps.columns) == LAP_COLUMNS
    assert tuple(wec_laps.columns) == LAP_COLUMNS


def test_only_race_laps_are_present(imsa_laps, wec_laps) -> None:
    """Practice/qualifying laps in the source must never leak in — mixing them
    silently duplicates lap numbers across sessions."""
    for laps, expected_cars in ((imsa_laps, 8), (wec_laps, 19)):
        assert laps["car"].nunique() == expected_cars
        # One row per (car, lap): duplicates would mean several sessions merged.
        assert not laps.duplicated(subset=["car", "lap"]).any()


def test_pit_visits_exceed_tyre_changes(imsa_laps) -> None:
    """The endurance signature: cars stop for fuel without changing tyres, so
    pit visits must outnumber tyre changes."""
    pit_visits = int(imsa_laps["is_pit_lap"].sum())
    tyre_changes = int(imsa_laps["is_tyre_change"].sum())
    assert pit_visits > tyre_changes > 0


def test_driver_stints_track_driver_changes(imsa_laps) -> None:
    """driver_stint must increment exactly when the driver changes."""
    car = imsa_laps[imsa_laps["car"] == "01"].sort_values("lap")
    assert car["driver"].nunique() >= 2
    changed_driver = car["driver"].ne(car["driver"].shift(1)) & car["driver"].shift(1).notna()
    new_stint = car["driver_stint"].ne(car["driver_stint"].shift(1)) & car["driver_stint"].shift(1).notna()
    assert changed_driver.sum() > 0
    # Every driver change opens a new driver stint.
    assert (changed_driver & ~new_stint).sum() == 0


def test_flags_and_green_flag_consistency(imsa_laps) -> None:
    assert set(imsa_laps["flag"].unique()) <= {"GF", "FCY", "FF", "RF"}
    assert imsa_laps["is_green"].equals(imsa_laps["flag"].eq("GF"))
    assert imsa_laps["is_green"].any() and (~imsa_laps["is_green"]).any()


def test_temperatures_converted_to_celsius(wec_laps) -> None:
    """Source is Fahrenheit; normalised frame must be Celsius and physical.
    Checked on WEC Spa, which has full weather coverage."""
    air = wec_laps["air_temp_c"].dropna()
    track = wec_laps["track_temp_c"].dropna()
    assert not air.empty and air.between(-10, 55).all()
    assert not track.empty and track.between(-10, 80).all()
    # 71.42F -> 21.9C, spot-checking the conversion rather than trusting it.
    assert air.iloc[0] == pytest.approx((71.42 - 32) * 5 / 9, abs=1e-6)


def test_missing_weather_stays_missing(imsa_laps) -> None:
    """IMSA Watkins Glen 2023 ships no weather on the race session. The loader
    must surface that as NaN rather than imputing it — a documented coverage
    gap, not a silent fill."""
    assert imsa_laps["air_temp_c"].isna().all()
    assert imsa_laps["track_temp_c"].isna().all()
    # Lap timing, tyre age and race length are unaffected.
    assert imsa_laps["lap_time_s"].notna().any()
    assert imsa_laps["tyre_age"].notna().all()
    assert imsa_laps["race_duration_min"].notna().all()


def test_green_lap_times_excludes_pit_and_neutralised_laps(imsa_laps) -> None:
    green = green_lap_times(imsa_laps)
    assert green["is_green"].all()
    assert not green["is_pit_lap"].any()
    assert green["lap_time_s"].notna().all()
    assert len(green) < len(imsa_laps)


def test_normalise_rejects_mixed_sessions() -> None:
    raw = pd.DataFrame({
        "series_code": ["imsa"], "year": ["2023"], "event": ["X"],
        "circuit_name": ["X"], "session": ["practice"], "session_id": [1],
        "car": ["1"], "class": ["GTP"], "driver_name": ["A"], "driver_id": ["a"],
        "lap": [1], "stint_number": [1], "stint_lap": [0], "lap_time": [90.0],
        "lap_time_s1": [30.0], "lap_time_s2": [30.0], "lap_time_s3": [30.0],
        "pit_time": [None], "flags": ["GF"], "est_tire_age": [0],
        "air_temp_f": [70.0], "track_temp_f": [80.0], "humidity_percent": [50.0],
        "raining": [False], "race_duration_minutes": [360],
    })
    with pytest.raises(ValueError, match="race laps only"):
        EnduranceLoader.normalise(raw)


def test_factory_and_validation() -> None:
    assert isinstance(get_loader("wec"), EnduranceLoader)
    assert get_loader("IMSA").series == "imsa"
    with pytest.raises(NotImplementedError, match="FastF1"):
        get_loader("f1")
    with pytest.raises(ValueError, match="unknown series"):
        get_loader("nascar")
    with pytest.raises(ValueError, match="unsupported series"):
        EnduranceLoader("motogp")
    with pytest.raises(ValueError, match="car_class is required"):
        EnduranceLoader("imsa").load_laps(2023, "Watkins Glen")


def test_slugify() -> None:
    assert slugify("Watkins Glen") == "watkins_glen"
    assert slugify("Le Mans 24h") == "le_mans_24h"
