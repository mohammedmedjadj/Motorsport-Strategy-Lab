"""Unit tests for the lap-cleaning layer (pure functions, no network)."""

from __future__ import annotations

import pandas as pd
import pytest

from src.ingestion.cleaning import (
    EXCLUSION_FLAGS,
    add_exclusion_flags,
    add_pace_lap_flag,
    attach_weather,
    clean_laps,
    convert_lap_times,
    mark_red_flag_stints,
)


def td(seconds: float) -> pd.Timedelta:
    """Timedelta helper that avoids the numpy generic-unit deprecation."""
    return pd.to_timedelta(seconds, unit="s")


def make_laps(**overrides: list) -> pd.DataFrame:
    """Synthetic laps frame with sane defaults; override any column."""
    n = len(next(iter(overrides.values()))) if overrides else 3
    base: dict[str, list] = {
        "Driver": ["VER"] * n,
        "Stint": [1] * n,
        "LapNumber": list(range(1, n + 1)),
        "LapTime": [td(90)] * n,
        "Time": [td(120 * (i + 1)) for i in range(n)],
        "LapStartTime": [td(120 * i) for i in range(n)],
        "PitInTime": [pd.NaT] * n,
        "PitOutTime": [pd.NaT] * n,
        "IsAccurate": [True] * n,
        "Compound": ["MEDIUM"] * n,
        "TrackStatus": ["1"] * n,
        "Deleted": [False] * n,
    }
    base.update(overrides)
    return pd.DataFrame(base)


def clean(df: pd.DataFrame) -> pd.DataFrame:
    return add_pace_lap_flag(add_exclusion_flags(convert_lap_times(df)))


def test_default_lap_is_pace_lap() -> None:
    out = clean(make_laps())
    assert out["is_pace_lap"].all()


def test_lap_time_converted_to_seconds() -> None:
    out = convert_lap_times(make_laps(LapTime=[td(92.5)]))
    assert out.loc[0, "lap_time_s"] == pytest.approx(92.5)


def test_in_and_out_laps_are_excluded() -> None:
    out = clean(
        make_laps(
            PitInTime=[td(120), pd.NaT, pd.NaT],
            PitOutTime=[pd.NaT, td(180), pd.NaT],
        )
    )
    assert out["is_in_lap"].tolist() == [True, False, False]
    assert out["is_out_lap"].tolist() == [False, True, False]
    assert out["is_pace_lap"].tolist() == [False, False, True]


def test_missing_laptime_is_excluded() -> None:
    out = clean(make_laps(LapTime=[pd.NaT, td(90)]))
    assert out["is_pace_lap"].tolist() == [False, True]


def test_inaccurate_lap_is_excluded_and_nan_is_conservative() -> None:
    out = clean(make_laps(IsAccurate=[False, None, True]))
    # NaN accuracy is treated as inaccurate (conservative).
    assert out["is_inaccurate"].tolist() == [True, True, False]


def test_wet_compounds_are_excluded() -> None:
    out = clean(make_laps(Compound=["INTERMEDIATE", "WET", "SOFT"]))
    assert out["is_wet_compound"].tolist() == [True, True, False]
    assert out["is_pace_lap"].tolist() == [False, False, True]


def test_non_green_and_unknown_status_are_excluded_separately() -> None:
    out = clean(make_laps(TrackStatus=["1", "4", "", None]))
    assert out["is_non_green"].tolist() == [False, True, False, False]
    assert out["is_unknown_status"].tolist() == [False, False, True, True]
    assert out["is_pace_lap"].tolist() == [True, False, False, False]


def test_deleted_lap_is_excluded() -> None:
    out = clean(make_laps(Deleted=[True, False]))
    assert out["is_pace_lap"].tolist() == [False, True]


def test_red_flag_marks_whole_stint_but_only_that_stint() -> None:
    df = make_laps(
        Driver=["VER"] * 4,
        Stint=[1, 1, 2, 2],
        TrackStatus=["1", "5", "1", "1"],
    )
    out = mark_red_flag_stints(convert_lap_times(df))
    assert out["stint_crosses_red_flag"].tolist() == [True, True, False, False]


def test_red_flag_stint_is_per_driver() -> None:
    df = make_laps(
        Driver=["VER", "LEC"],
        Stint=[1, 1],
        TrackStatus=["5", "1"],
    )
    out = mark_red_flag_stints(convert_lap_times(df))
    assert out["stint_crosses_red_flag"].tolist() == [True, False]


def test_attach_weather_uses_latest_reading_before_lap_end() -> None:
    laps = make_laps(Time=[td(120), td(600)])
    weather = pd.DataFrame(
        {
            "Time": [td(0), td(540)],
            "AirTemp": [25.0, 27.0],
            "TrackTemp": [40.0, 44.0],
            "Humidity": [60.0, 55.0],
            "Rainfall": [False, False],
        }
    )
    out = attach_weather(laps, weather)
    assert out["air_temp_c"].tolist() == [25.0, 27.0]
    assert out["track_temp_c"].tolist() == [40.0, 44.0]


def test_attach_weather_with_empty_weather_gives_nan_columns() -> None:
    out = attach_weather(make_laps(), pd.DataFrame())
    assert out["air_temp_c"].isna().all()


def test_clean_laps_composes_everything() -> None:
    out = clean_laps(make_laps(), pd.DataFrame())
    for flag in (*EXCLUSION_FLAGS, "is_pace_lap", "stint_crosses_red_flag"):
        assert flag in out.columns
    assert out["is_pace_lap"].all()
