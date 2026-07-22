"""Endurance retrospective audit: winner selection and stint reconstruction from
real pit visits (synthetic), plus the committed-artifact finding that the large
majority of real winners ran fuel-limited — corroborating the multi-stop model."""

from __future__ import annotations

import pandas as pd
import pytest

from src.audit.endurance_state import (
    FuelLimitedAudit,
    stint_lengths,
    winning_car,
)
from src.ingestion.config import ENDURANCE_DERIVED_DIR

_ARTIFACT = ENDURANCE_DERIVED_DIR / "fuel_limited_audit.csv"


def _laps() -> pd.DataFrame:
    """Two cars: #7 runs 30 laps with pit visits on 10 and 20 (stints 10,10,10),
    #9 retires after 12 laps. Winner is #7 (most laps)."""
    rows = []
    for lap in range(1, 31):
        rows.append({"car": 7, "lap": lap,
                     "pit_time": 25.0 if lap in (10, 20) else None})
    for lap in range(1, 13):
        rows.append({"car": 9, "lap": lap, "pit_time": None})
    return pd.DataFrame(rows)


def test_winner_is_the_car_with_most_laps() -> None:
    assert winning_car(_laps()) == 7


def test_stint_lengths_segmented_by_pit_visits() -> None:
    # pit visits on 10 and 20 → stints of 10, 10, 10.
    assert stint_lengths(_laps(), 7) == [10, 10, 10]


def test_fuel_limited_flag_logic() -> None:
    # longest stint reaches the range and >=1 full stint → fuel-limited.
    a = FuelLimitedAudit("wec", "test", 2024, "7", fuel_range_laps=32,
                         longest_stint=32, n_full_stints=4, n_stints=8)
    assert a.ran_fuel_limited is True
    # a winner whose longest stint falls well short is not fuel-limited.
    b = FuelLimitedAudit("imsa", "test", 2023, "5", fuel_range_laps=50,
                         longest_stint=43, n_full_stints=0, n_stints=4)
    assert b.ran_fuel_limited is False


@pytest.mark.skipif(not _ARTIFACT.exists(), reason="audit artifact not generated")
def test_committed_audit_most_winners_ran_fuel_limited() -> None:
    """The real-data corroboration, pinned: the large majority of scoped-race
    winners ran at least one full-fuel-range stint."""
    art = pd.read_csv(_ARTIFACT)
    assert art["ran_fuel_limited"].mean() > 0.8
    # every WEC winner is fuel-limited (WEC has the tightest fuel windows).
    wec = art[art["series"] == "wec"]
    assert wec["ran_fuel_limited"].all()
