"""Tests for the endurance per-decision audit: state reconstruction and case
construction (the endurance analogue of ``tests/test_audit.py``)."""

from __future__ import annotations

import pandas as pd
import pytest

from src.audit.endurance_case_state import pit_stops, race_length, state_at
from src.audit.endurance_cases import build_cases, build_imsa_cases, build_wec_cases


def make_laps() -> pd.DataFrame:
    """Two cars, one pit stop each, a tyre change on the stop lap."""
    rows = []
    for car, stop_lap in (("1", 3), ("2", 4)):
        age = 0
        for lap in range(1, 6):
            is_pit = lap == stop_lap
            rows.append({
                "car": car, "lap": lap, "tyre_age": age,
                "is_pit_lap": is_pit, "flag": "GF",
            })
            age = 0 if is_pit else age + 1
    return pd.DataFrame(rows)


def test_state_at_tracks_tyre_age_and_fuel_clock() -> None:
    laps = make_laps()
    # Decision point: the lap BEFORE car 1's real stop (lap 3) — what an
    # audit case actually reconstructs.
    before = state_at(laps, "1", 2)
    assert before.tyre_age == 1
    assert before.laps_since_refuel == 1
    # The pit lap itself still carries the OLD (about-to-be-changed) tyre age
    # — matching the source schema, where age resets on the following lap —
    # but the fuel clock (cumsum of is_pit_lap) already rolls over here, the
    # same convention build_endurance_frame uses.
    at_stop = state_at(laps, "1", 3)
    assert at_stop.tyre_age == 2
    assert at_stop.laps_since_refuel == 0


def test_state_at_missing_lap_or_car_raises() -> None:
    laps = make_laps()
    with pytest.raises(LookupError):
        state_at(laps, "1", 99)
    with pytest.raises(LookupError):
        state_at(laps, "XXX", 1)


def test_pit_stops_and_race_length() -> None:
    laps = make_laps()
    assert pit_stops(laps, "1") == [3]
    assert pit_stops(laps, "2") == [4]
    assert race_length(laps, "1") == 5


def test_race_length_missing_car_raises() -> None:
    laps = make_laps()
    with pytest.raises(LookupError):
        race_length(laps, "XXX")


@pytest.mark.parametrize("series,builder", [("wec", build_wec_cases), ("imsa", build_imsa_cases)])
def test_build_cases_reconstructs_real_states(series, builder) -> None:
    """Every case's scenario is consistent with its own real pit lap and
    fuel/tyre state, and the model builds without error (offline, committed
    derived data + race_flags.csv only)."""
    cases = builder()
    assert len(cases) == 3
    for case in cases:
        assert case.series == series
        assert case.scenario.current_lap == case.real_pit_lap - 1
        assert case.scenario.tyre_age >= 0
        assert case.scenario.laps_since_refuel >= 0
        assert case.scenario.total_laps > case.scenario.current_lap
        assert case.model.fuel_range_laps > 0
        # The real pit lap must be a feasible candidate in the model's own
        # search space, or the audit script cannot look up its row.
        candidates = case.scenario.candidate_pit_laps(case.model)
        assert case.real_pit_lap in candidates


def test_build_cases_dispatches_by_series() -> None:
    assert len(build_cases("wec")) == 3
    assert len(build_cases("imsa")) == 3
    with pytest.raises(ValueError):
        build_cases("f1")
