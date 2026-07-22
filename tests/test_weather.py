"""Weather layer: the wet-flag and race-day summary logic, tested offline with
synthetic hourly blocks (the network fetch is isolated and not exercised here)."""

from __future__ import annotations

import pytest

from src.weather.archive import (
    ENDURANCE_CIRCUIT_COORDS,
    WET_PRECIP_MM,
    summarise_hourly,
)


def _hourly(temps, hums, precip):
    return {"temperature_2m": temps, "relative_humidity_2m": hums,
            "precipitation": precip}


def test_dry_day_is_not_wet_and_summarises_correctly() -> None:
    s = summarise_hourly("2023-03-05",
                         _hourly([20, 24, 32, 28], [40, 38, 30, 36], [0, 0, 0, 0]))
    assert s.wet is False
    assert s.precip_mm == 0.0
    assert s.temp_max_c == 32
    assert s.temp_mean_c == pytest.approx(26.0)


def test_rain_over_threshold_flags_wet() -> None:
    s = summarise_hourly("2021-08-29",
                         _hourly([12, 13, 14], [95, 96, 97], [2.0, 3.0, 2.1]))
    assert s.precip_mm == pytest.approx(7.1)
    assert s.wet is True                              # 7.1 mm > threshold


def test_threshold_is_exclusive_and_handles_missing_humidity() -> None:
    # exactly the threshold is not "wet" (strictly greater), and missing humidity
    # degrades to NaN rather than crashing.
    s = summarise_hourly("x", _hourly([15, 16], [], [WET_PRECIP_MM / 2,
                                                     WET_PRECIP_MM / 2]))
    assert s.precip_mm == pytest.approx(WET_PRECIP_MM)
    assert s.wet is False
    assert s.humidity_mean_pct != s.humidity_mean_pct   # NaN


def test_no_temperature_raises() -> None:
    with pytest.raises(ValueError):
        summarise_hourly("x", _hourly([], [], []))


def test_endurance_coords_cover_every_scoped_circuit() -> None:
    # The 4 IMSA + 4 WEC scoped circuits all have coordinates, so the same
    # fetcher can fill their weather gap.
    assert len(ENDURANCE_CIRCUIT_COORDS) == 8
    for (series, _), (lat, lng) in ENDURANCE_CIRCUIT_COORDS.items():
        assert series in {"imsa", "wec"}
        assert -90 <= lat <= 90 and -180 <= lng <= 180
