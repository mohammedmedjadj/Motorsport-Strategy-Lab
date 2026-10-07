"""The answer to the circularity objection, and the ways it could become one.

Result 2 says the strategy regime is set by the cost of the stop. The objection
is that the optimiser decides by comparing the stop cost against the tyre, so
pit loss predicting the regime is pit loss predicting one side of its own
criterion. The report answers that with two AUCs rather than an argument, and
the numbers it quotes are load-bearing in the manuscript.

The trap this walked into once is worth naming. A third candidate,
``slope_headroom_x``, scored a perfect 1.000 and was nearly reported as the
strongest discriminator. It is the label: the breakeven slope is found by
searching upward from the measured one until the optimum takes an extra stop,
so a race that already takes one has a ratio of exactly 1 and every other race
is strictly above. Publishing that in a report written to rebut circularity
would have handed a reviewer the objection in a stronger form than they asked
it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
TABLE = REPO / "data" / "derived" / "cross_series" / "regime_decomposition.csv"
PLANS = REPO / "data" / "derived" / "endurance" / "multistop_plans.csv"
REPORT = REPO / "reports" / "cross_series" / "regime_decomposition.md"
NUMBERS = REPO / "paper" / "numbers.tex"


@pytest.fixture(scope="module")
def table():
    pandas = pytest.importorskip("pandas")
    if not TABLE.exists():
        pytest.skip("run scripts/run_regime_decomposition.py first")
    return pandas.read_csv(TABLE)


@pytest.fixture(scope="module")
def plans():
    pandas = pytest.importorskip("pandas")
    frame = pandas.read_csv(PLANS)
    frame["tyre_limited"] = frame["optimal_stops"] != frame["min_stops"]
    return frame


@pytest.fixture(scope="module")
def report() -> str:
    if not REPORT.exists():
        pytest.skip("run scripts/run_regime_decomposition.py first")
    return REPORT.read_text(encoding="utf-8")


def test_only_the_two_honest_discriminators_are_reported(table) -> None:
    """A third candidate scored 1.000 by construction and must stay out."""
    assert set(table["quantity"]) == {"pit loss", "net degradation slope"}, (
        f"the table reports {sorted(table['quantity'])}. Anything else has to "
        "be shown not to be a restatement of the label before it goes in."
    )


def test_slope_headroom_is_still_a_restatement_of_the_label(plans) -> None:
    """Why that third candidate is excluded, recomputed rather than asserted.

    If this ever stopped holding, headroom would become a real discriminator
    and the exclusion would be wrong rather than careful.
    """
    limited = plans[plans["tyre_limited"]]["slope_headroom_x"]
    fuel = plans[~plans["tyre_limited"]]["slope_headroom_x"]
    assert (limited.dropna() == 1.0).all(), (
        "a tyre-limited race-season no longer has a headroom of exactly 1, so "
        "the quantity is no longer determined by the label and the report's "
        "reason for excluding it has changed"
    )
    assert (fuel.dropna() > 1.0).all(), (
        "a fuel-limited race-season now has a headroom at or below 1"
    )


def test_pit_loss_outranks_the_slope_and_both_beat_a_coin_toss(table) -> None:
    """The finding. Both halves matter, in opposite directions.

    If the slope dropped to chance, the regime really would be pit loss alone
    and the circularity objection would land. If pit loss stopped dominating,
    the headline claim of Result 2 would be wrong.
    """
    scores = dict(zip(table["quantity"], table["auc"]))
    assert scores["net degradation slope"] > 0.6, (
        f"the degradation slope is down to {scores['net degradation slope']}, "
        "near chance. Result 2 would then rest on pit loss alone, which is the "
        "circularity the report exists to rule out."
    )
    assert scores["pit loss"] > scores["net degradation slope"], (
        "the degradation slope now orders the regimes better than pit loss "
        f"does ({scores}). That reverses Result 2."
    )


def test_the_intervals_exclude_chance(table) -> None:
    assert (table["ci_low"] > 0.5).all(), (
        "a discriminator's interval now reaches a coin toss, so it should not "
        "be quoted as ordering the regimes at all"
    )
    assert (table["ci_low"] <= table["auc"]).all()
    assert (table["auc"] <= table["ci_high"]).all()


def test_the_sample_is_every_race_season(table, plans) -> None:
    """A silently narrowed sample would change the comparison, not just the n."""
    for _, row in table.iterrows():
        total = int(row["n_tyre_limited"]) + int(row["n_fuel_limited"])
        assert total == len(plans), (
            f"{row['quantity']} is scored on {total} race-seasons against "
            f"{len(plans)} in the plans table"
        )


def test_the_macros_match_the_artifact(table) -> None:
    """The manuscript quotes these. A drift here is a wrong published number."""
    import re

    if not NUMBERS.exists():
        pytest.skip("paper/numbers.tex not generated")
    macros = dict(
        re.findall(r"\\newcommand\{\\(\w+)\}\{([^}]*)\}",
                   NUMBERS.read_text(encoding="utf-8"))
    )
    wanted = {"pit loss": "RegimeAucPitLoss",
              "net degradation slope": "RegimeAucSlope"}
    for _, row in table.iterrows():
        name = wanted[row["quantity"]]
        assert macros.get(name) == f"{row['auc']:.3f}", (
            f"\\{name} is {macros.get(name)} but the artifact says "
            f"{row['auc']:.3f}"
        )


def test_the_report_says_what_the_measurement_does_not_settle(report: str) -> None:
    """The claim is asymmetry in practice, not causation, and must read that way."""
    assert "does not establish that pit loss" in report or (
        "not show" in report and "causes" in report
    ), (
        "the report should state plainly that this does not show pit loss "
        "causes the regime"
    )
    assert "tautology" in report, (
        "the excluded discriminator should be named as a tautology rather "
        "than dropped without explanation"
    )
    assert "n(n+1)/2" in report, (
        "the closed-form condition should appear, with the note that the "
        "implementation is the exact solver instead"
    )
