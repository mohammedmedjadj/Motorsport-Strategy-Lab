"""Tests for audit state reconstruction and the ongoing-neutralisation
engine extension it relies on."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.audit.state import compound_after, gap_between, pit_stops, state_at
from src.simulator.engine import SC, VSC, _sample_status
from tests.test_simulator import make_model


def make_laps() -> pd.DataFrame:
    rows = []
    t = {"VER": 0.0, "NOR": 2.0}  # NOR starts 2s back
    for lap in range(1, 6):
        for drv, pace in (("VER", 90.0), ("NOR", 90.5)):
            t[drv] += pace + (10.0 if drv == "NOR" and lap == 3 else 0.0)
            rows.append(
                {
                    "Driver": drv,
                    "LapNumber": lap,
                    "time_s": t[drv],
                    "Compound": "SOFT" if lap <= 3 or drv == "VER" else "HARD",
                    "TyreLife": lap if drv == "VER" else (lap if lap <= 3 else lap - 3),
                    "Position": 1 if drv == "VER" else 2,
                    "is_in_lap": drv == "NOR" and lap == 3,
                }
            )
    return pd.DataFrame(rows)


def test_state_and_stops_and_compound_after() -> None:
    laps = make_laps()
    s = state_at(laps, "NOR", 5)
    assert s.compound == "HARD"
    assert pit_stops(laps, "NOR") == [3]
    assert pit_stops(laps, "VER") == []
    assert compound_after(laps, "NOR", 3) == "HARD"


def test_gap_direction_and_growth() -> None:
    laps = make_laps()
    g1 = gap_between(laps, "VER", "NOR", 1)
    g5 = gap_between(laps, "VER", "NOR", 5)
    assert g1 == pytest.approx(2.5)  # initial 2s + 0.5s pace delta
    assert g5 > g1  # NOR lost more time (slower + stop)


def test_missing_lap_raises() -> None:
    laps = make_laps()
    with pytest.raises(LookupError):
        state_at(laps, "VER", 99)
    with pytest.raises(LookupError):
        gap_between(laps, "VER", "XXX", 1)


def test_ongoing_sc_forces_first_laps() -> None:
    model = make_model(sc_rate=0.0)
    rng = np.random.default_rng(11)
    for _ in range(20):
        status = _sample_status(model, 30, rng, ongoing=("SC", 0))
        assert status[0] == SC  # at least one more SC lap, always
    # Durations pool is (3,4,5): elapsed 4 -> remaining is 1 (only 5 works)
    status = _sample_status(model, 30, rng, ongoing=("SC", 4))
    assert status[0] == SC and status[1] != SC


def test_ongoing_vsc_uses_vsc_code() -> None:
    model = make_model(sc_rate=0.0)
    status = _sample_status(model, 30, np.random.default_rng(5), ongoing=("VSC", 0))
    assert status[0] == VSC
