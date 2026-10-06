"""The position-keeping defence test, and the ways it could flatter itself.

This is a negative result, which makes it a different kind of thing to guard.
A positive result rots when the data moves; a negative one rots when somebody
later makes it come out positive. Three of these fix the arithmetic that keeps
it honest.

Two defects in the first pass were real and both inflated the window, which is
the direction that would have made the conclusion look stronger than it is:

- the rival was found by cumulative race time with no bound, so a car a lap
  down read as 910 seconds "ahead";
- the expiry is a tyre age and was compared against a lap number, which agree
  only for a car on a tyre fitted at the start, true for 78% of the decisions.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
TABLE = REPO / "data" / "derived" / "f1" / "d1_defence.csv"
DECISIONS = REPO / "data" / "derived" / "f1" / "undercut_hypothesis.csv"
REPORT = REPO / "reports" / "f1" / "d1_defence.md"


@pytest.fixture(scope="module")
def table():
    pandas = pytest.importorskip("pandas")
    if not TABLE.exists():
        pytest.skip("run scripts/run_d1_defence.py first")
    return pandas.read_csv(TABLE)


@pytest.fixture(scope="module")
def report() -> str:
    if not REPORT.exists():
        pytest.skip("run scripts/run_d1_defence.py first")
    return REPORT.read_text(encoding="utf-8")


def test_every_audited_decision_is_accounted_for(table) -> None:
    """A decision that silently vanishes narrows the sample without saying so."""
    pandas = pytest.importorskip("pandas")
    decisions = pandas.read_csv(DECISIONS)
    assert len(table) == len(decisions), (
        f"{len(table)} rows against {len(decisions)} audited decisions. "
        "Every one should appear, including the race leaders that carry no "
        "prediction."
    )
    assert set(table["role"]) == {"chaser", "race leader"}


def test_no_rival_is_a_lapped_car(table) -> None:
    """The 910-second bug. A car a lap down is not an opponent in this fight."""
    chasers = table[table["role"] == "chaser"]
    worst = float(chasers["gap_to_leader_s"].max())
    assert worst < 60.0, (
        f"the nearest car ahead is {worst:.0f} s away on some decision, which "
        "is a car on a different lap of the race rather than a rival. The "
        "one-lap bound on the rival search has stopped working."
    )
    assert (chasers["gap_to_leader_s"] > 0).all(), (
        "a leader is not ahead, so the sign convention has inverted"
    )


def test_the_expiry_is_mapped_through_tyre_age_not_lap_number(table) -> None:
    """Salminen's l_u counts laps of tyre use; the comparison is a lap number."""
    rows = table[
        (table["role"] == "chaser")
        & table["euu_lap"].notna()
        & table["stint_start_lap"].notna()
    ]
    assert not rows.empty
    implied = rows["euu_lap"] - rows["stint_start_lap"]
    assert (implied >= 1).all(), (
        "a predicted undercut lands before the tyre went on, so the expiry "
        "is being added to the wrong origin"
    )
    differing = rows[rows["stint_start_lap"] != 0]
    assert not differing.empty, (
        "every decision now has a stint starting at lap zero, which would "
        "make this guard vacuous"
    )


def test_the_result_is_still_negative(table) -> None:
    """The finding itself. If this ever flips it is a result, not a fix.

    The point of the report is that D1 fed with measured parameters predicts
    worse than the existing single-car optimiser. Anyone making it come out
    better has either found something real or broken the comparison, and both
    deserve to be noticed here rather than in the prose.
    """
    rows = table[(table["role"] == "chaser") & table["euu_lap"].notna()]
    closer = int((rows["euu_error"].abs() < rows["single_car_error"].abs()).sum())
    further = int((rows["euu_error"].abs() > rows["single_car_error"].abs()).sum())
    assert further > closer, (
        f"D1 is now closer to the real stop than the optimiser on {closer} "
        f"decisions against {further}. That reverses the report's conclusion "
        "and the prose has to change with it."
    )
    assert float(rows["euu_error"].median()) > 0, (
        "D1 no longer predicts a later stop than teams made, which is the "
        "direction the whole argument rests on"
    )


def test_the_implied_degradation_rate_exceeds_the_measured_one(table) -> None:
    """The report's explanation, as a number rather than a story."""
    rows = table[
        (table["role"] == "chaser")
        & table["theta_resolved"].astype(bool)
        & table["theta_ratio"].notna()
    ]
    assert not rows.empty
    assert float(rows["theta_ratio"].median()) > 1.0, (
        "the degradation rate that would make D1 expire at the real stop is "
        "no longer larger than the measured rate, which is the report's "
        "whole account of why the prediction fails"
    )


def test_epsilon_is_zero_in_the_published_table(table) -> None:
    """The headline refuses the flattering direction. This is what enforces it.

    A measured epsilon reads the chaser's pace in dirty air, which inflates it,
    and a larger epsilon expires D1 earlier and so moves the prediction toward
    the real stop.
    """
    # Race-leader rows carry none of the model's quantities, epsilon among
    # them, because the game does not arise for a car with nobody ahead.
    chasers = table[table["role"] == "chaser"]
    assert (chasers["epsilon"] == 0.0).all(), (
        "the committed table was built with a non-zero epsilon. The "
        "sensitivity belongs in its own section of the report, not in the "
        "headline numbers."
    )
    assert table[table["role"] == "race leader"]["epsilon"].isna().all(), (
        "a race-leader row now carries an epsilon, so it is being fed through "
        "a model that does not apply to it"
    )


def test_the_report_credits_thraves_and_leaves_the_published_result_alone(
    report: str,
) -> None:
    assert "Thraves" in report, (
        "the switch from position distance to seconds came from his objection"
    )
    assert "published replay is untouched" in report, (
        "the report should say plainly that it does not revise the published "
        "undercut result"
    )
    assert "negative" in report, (
        "the report should state its own conclusion rather than leaving it to "
        "be inferred from a table"
    )
