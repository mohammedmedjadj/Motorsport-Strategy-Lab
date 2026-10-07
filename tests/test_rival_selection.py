"""Four readings of the word "rival", and what the comparison must keep saying.

The published replay chose the rival by classified-position distance, which
Thraves objected leaves the choice to row order whenever a car ahead and a car
behind are equally close. He then supplied a criterion. The comparison answers
two questions at once, and they point opposite ways, so both are guarded:
the rules disagree about which car to model on most decisions, and none of them
moves Result 3.

If either half flipped, the paper would be wrong in a different place. A
comparison that found the rules agreeing would mean the selection hardly
matters and the section is overstated. One that found a rule closing the gap
would mean Result 3 has an explanation, which is the thing this project has
been looking for and has not found.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
TABLE = REPO / "data" / "derived" / "f1" / "rival_selection.csv"
AUDIT = REPO / "data" / "derived" / "f1" / "systematic_audit.csv"
REPORT = REPO / "reports" / "f1" / "rival_selection.md"

METHODS = {"position", "pi_window", "d1", "thraves"}


@pytest.fixture(scope="module")
def table():
    pandas = pytest.importorskip("pandas")
    if not TABLE.exists():
        pytest.skip("run scripts/run_rival_selection.py first")
    return pandas.read_csv(TABLE)


@pytest.fixture(scope="module")
def report() -> str:
    if not REPORT.exists():
        pytest.skip("run scripts/run_rival_selection.py first")
    return REPORT.read_text(encoding="utf-8")


def test_every_rule_sees_every_decision(table) -> None:
    """A rule quietly scored on fewer decisions would not be comparable."""
    pandas = pytest.importorskip("pandas")
    audit = pandas.read_csv(AUDIT)
    assert set(table["method"]) == METHODS
    counts = table.groupby("method").size()
    assert (counts == len(audit)).all(), (
        f"the rules see {counts.to_dict()} decisions against {len(audit)} "
        "audited. Each rule must be offered every decision, even where it "
        "declines to name a rival."
    )


def test_the_position_ahead_rule_declines_where_it_should(table) -> None:
    """A race leader has no car ahead, so one rule must score fewer.

    Equal coverage across all four would mean the clock-based rule had found a
    rival for a car that is leading, which it cannot.
    """
    scored = table.dropna(subset=["adversarial_lap"])
    per_rule = scored.groupby("method").size()
    assert per_rule["d1"] < per_rule["position"], (
        "the car-ahead rule now scores as many decisions as the position "
        "rule, which would mean it named a rival for a race leader"
    )


def test_the_rules_disagree_about_which_car_to_model(table) -> None:
    """Half the finding. If they agreed, the selection would hardly matter."""
    wide = table.pivot_table(
        index=["season", "circuit", "driver"], columns="method",
        values="rival", aggfunc="first",
    ).dropna()
    assert not wide.empty
    agree = float((wide.nunique(axis=1) == 1).mean())
    assert agree < 0.5, (
        f"all four rules now name the same car on {100 * agree:.0f}% of "
        "decisions. The paper says the choice is consequential; at this level "
        "of agreement it is not."
    )


def test_no_rule_rescues_result_three(table) -> None:
    """The other half. A rule that closed the gap would be a finding, not a fix.

    Result 3 is that the optimiser stops later than teams do. The cover-aware
    model was built to explain that and does not. If some selection rule made
    it explain it, the paper's central unresolved result would be resolved and
    the prose around it would be wrong.
    """
    scored = table.dropna(subset=["adversarial_lap"])
    for method, part in scored.groupby("method"):
        assert float(part["adversarial_error"].median()) > 0, (
            f"the {method} rule now gives a cover-aware recommendation at or "
            "before the real stop. That contradicts Result 3 rather than "
            "qualifying it."
        )
        assert float(part["closed"].median()) <= 0, (
            f"the {method} rule now moves the cover-aware recommendation "
            "toward the real stop by a positive median. The adversarial model "
            "would then be an improvement on the single-car one, which is the "
            "opposite of what the paper reports."
        )


def test_the_thraves_rule_is_the_least_bad(table) -> None:
    """What his heuristic actually bought, which the paper credits him with."""
    scored = table.dropna(subset=["adversarial_lap"])
    means = scored.groupby("method")["closed"].mean()
    assert means["thraves"] == means.max(), (
        f"his rule is no longer the best of the four on mean closed: {means.to_dict()}. "
        "The paper says it removes the penalty the published selection carries."
    )


def test_the_endogeneity_is_stated_rather_than_dropped(report: str) -> None:
    """He named the limit of his own proposal; it is the kind that goes missing."""
    assert "endogenous" in report, (
        "the report no longer states that the choice of rival becomes "
        "endogenous at the extreme, which Thraves raised himself"
    )
    assert "approximation" in report
    assert "Thraves" in report


def test_the_heuristic_sorts_on_something_measurable(table) -> None:
    """The standalone times must actually differ, or the rule is arbitrary."""
    gaps = table[table["method"] == "thraves"]["standalone_delta_s"].dropna()
    assert not gaps.empty, "no standalone race times were estimated at all"
    assert float(gaps.median()) > 0, (
        "the selected rival's estimated standalone race time is identical to "
        "the audited car's, so the rule is not discriminating between cars"
    )
