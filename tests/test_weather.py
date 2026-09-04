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


# --- the window the "race day" actually means -------------------------------
#
# Open-Meteo interprets start_date/end_date in the *requested* timezone and
# defaults to GMT. Omitting the parameter therefore asks for a 24-hour UTC
# slice, not the circuit's local race day — and the returned timestamps are
# labelled identically either way ("2024-04-07T00:00 .. 23:00"), so nothing in
# the response reveals the mistake. Only the values differ.
#
# It ran that way for the whole history. Re-fetching all 286 races with the
# local day changed the precipitation total for **79 of them (28%)**, by up to
# 53.5 mm, and flipped the wet flag on **12**. Suzuka 2014 read 71.6 mm on the
# UTC slice against 18.1 mm on the local day; Suzuka 2016 read 1.3 mm — dry —
# where the local day had 17.0 mm.
#
# The flag is not decorative: it drops whole race-seasons from the Kaggle
# breadth degradation fit, which is the independent source the slope-bias check
# compares the core fits against. A misaligned window corrupts precisely the
# comparison whose value is that it is independent.


def test_the_fetcher_asks_for_a_local_day_not_a_utc_slice() -> None:
    """`timezone` must be sent, and must mean the circuit's own day."""
    import inspect

    from src.weather import archive

    source = inspect.getsource(archive.fetch_open_meteo)
    assert '"timezone"' in source, (
        "fetch_open_meteo sends no timezone parameter, so Open-Meteo defaults "
        "to GMT and start_date/end_date select a 24-hour UTC slice instead of "
        "the local race day. This was wrong for the entire weather history "
        "once and nothing in the API response showed it."
    )
    assert '"auto"' in source, (
        "the timezone is pinned to something other than 'auto'. It must "
        "resolve from the circuit's own coordinates — a fixed zone is right "
        "for at most one circuit on the calendar."
    )


def test_every_committed_weather_row_records_which_window_produced_it() -> None:
    """Provenance, because the fetcher resumes and resuming hides fixes.

    `run_f1_weather.py` skips races already in the output so a large fetch can
    be done in passes. That also means a corrected fetcher never reaches the
    rows already on disk: re-running after the timezone fix reported success
    and changed nothing, which looks exactly like the fix having no effect.
    Stamping the window lets the resume path tell the two apart.
    """
    import pandas as pd

    from src.ingestion.config import F1_DERIVED_DIR

    path = F1_DERIVED_DIR / "weather.csv"
    if not path.exists():
        pytest.skip("weather layer not fetched")
    table = pd.read_csv(path)
    assert "fetch_window" in table.columns, (
        "weather.csv records no fetch_window, so nothing can tell rows built "
        "by the current fetcher from rows built by an older one, and the "
        "resume path will trust both."
    )
    windows = set(table["fetch_window"].astype(str))
    assert windows == {"local-day"}, (
        f"weather.csv mixes fetch windows: {sorted(windows)}. Rows from "
        "different windows are not comparable — the wet flag is a threshold "
        "on a 24-hour total and the two windows cover different 24 hours."
    )
