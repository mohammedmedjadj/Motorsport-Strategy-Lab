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
    a = FuelLimitedAudit("wec", "test", "HYPERCAR", 2024, "7", fuel_range_laps=32,
                         longest_stint=32, n_full_stints=4, n_stints=8)
    assert a.ran_fuel_limited is True
    # a winner whose longest stint falls well short is not fuel-limited.
    b = FuelLimitedAudit("imsa", "test", "GTP", 2023, "5", fuel_range_laps=50,
                         longest_stint=43, n_full_stints=0, n_stints=4)
    assert b.ran_fuel_limited is False


@pytest.mark.skipif(
    not (ENDURANCE_DERIVED_DIR / "multistop_plans.csv").exists(),
    reason="multistop artifact not generated",
)
def test_fuel_limited_verdict_survives_the_strictest_tolerance() -> None:
    """Regression guard for the sensitivity sweep
    (scripts/run_fuel_limited_sensitivity.py): the headline 3-lap-tolerance
    number moves a lot across tolerances (64%-97%), but the *qualitative*
    claim -- a clear majority ran fuel-limited, in both series -- must hold
    even at the strictest possible reading (0 laps, exact reach only). If a
    future data refresh ever drops this below a majority, the report's
    "the qualitative claim is not sensitive" line becomes false and must be
    rewritten, not silently left stale."""
    from src.audit.endurance_state import audit_fuel_limited
    from src.data.endurance_loader import slugify
    from src.data.endurance_scope import scoped_race_seasons

    plans = pd.read_csv(ENDURANCE_DERIVED_DIR / "multistop_plans.csv")
    ranges = {(r["series"], r["circuit"]): int(r["fuel_range_laps"]) for _, r in plans.iterrows()}

    rows = []
    for series, event, car_class, season in scoped_race_seasons():
        circuit = slugify(event)
        fuel_range = ranges.get((series, circuit))
        if fuel_range is None:
            continue
        # slugify, not .lower() — this test carried the same bug the script
        # did, so it would have re-verified the strict-tolerance claim on a
        # scope silently missing every class whose name has a space or slash.
        slug = f"{season}_{circuit}_{slugify(car_class)}"
        try:
            audit = audit_fuel_limited(series, circuit, car_class, season, slug, fuel_range,
                                       tolerance_laps=0)
        except FileNotFoundError:
            continue
        rows.append({"series": series, "ran_fuel_limited": audit.ran_fuel_limited})

    art = pd.DataFrame(rows)
    assert art["ran_fuel_limited"].mean() > 0.5
    by_series = art.groupby("series")["ran_fuel_limited"].mean()
    assert (by_series > 0.5).all()


@pytest.mark.skipif(not _ARTIFACT.exists(), reason="audit artifact not generated")
def test_committed_audit_most_winners_ran_fuel_limited() -> None:
    """The real-data corroboration, pinned: a clear majority of scoped-race
    winners ran at least one full-fuel-range stint.

    On the original 4+4 hand-picked circuits, *every* WEC winner did — but that
    was 6 WEC circuit-seasons; on the widened 28-race WEC sample (every eligible
    circuit the source carries) three winners fall short (COTA 2024, Fuji 2022,
    Fuji 2023), each with a longest stint at 85-87% of the fuel range, plausibly
    explained by neutralisation-shortened stints (see the report's "Reading the
    exceptions"). The honest bound is therefore a strong majority per series,
    not "always" — asserting "always" on the small sample would have been
    exactly the kind of small-N overclaim this widening was meant to catch."""
    art = pd.read_csv(_ARTIFACT)
    assert "car_class" in art.columns, (
        "the audit must identify the class: IMSA fields three at the same "
        "circuit-year and pooling them hides the finding below"
    )

    # Stated per class, because pooling makes it false. Running the fuel
    # minimum is a *prototype* behaviour, not a universal one -- the same
    # mechanism as reports/when_tyres_beat_fuel.md. Where the stop is cheap,
    # winners stop more often than the tank requires:
    #
    #   ELMS LMP2 1.00, LMP2 Pro/Am 0.94, WEC HYPERCAR 0.89
    #   IMSA GTD PRO 0.77, GTP 0.64, GTD 0.63
    #
    # The series-level average was 0.75 and hid a 0.63-to-1.00 spread.
    by_class = art.groupby(["series", "car_class"])["ran_fuel_limited"].mean()
    prototypes = by_class.loc[[("elms", "LMP2"), ("elms", "LMP2 Pro/Am"),
                               ("wec", "HYPERCAR")]]
    assert (prototypes > 0.85).all(), f"prototype winners stopped running to the tank: {prototypes}"
    gt3 = by_class.loc[[("imsa", "GTD"), ("imsa", "GTDPRO")]]
    assert (gt3 < 0.85).all(), f"GT3 winners now run fuel-limited like prototypes: {gt3}"
    assert art["ran_fuel_limited"].mean() > 0.7
