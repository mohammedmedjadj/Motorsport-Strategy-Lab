"""The two objections to Result 2, and the claims made in answering them.

Wytze de Vries asked whether a class median pools distinct populations, and
whether the pit-loss correlation partly runs backwards. The report that answers
him makes three load-bearing claims, and all three are the kind that stop being
true quietly when the scope widens:

- the class *ordering* is unchanged whichever population the median is taken
  over, which is why the published six-row table survives objection 1;
- pit loss varies far more between circuits than between seasons of the same
  circuit, which is what makes it exogenous to the race outcome;
- holding the circuit constant, the reverse channel is small.

If any of those flips, the answer sent to a researcher becomes wrong, so each
is recomputed here rather than read from the report.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
EVENTS = REPO / "data" / "derived" / "cross_series" / "pit_loss_stop_events.csv"
PLANS = REPO / "data" / "derived" / "endurance" / "multistop_plans.csv"
REPORT = REPO / "reports" / "cross_series" / "pit_loss_measurement_check.md"


@pytest.fixture(scope="module")
def events():
    pandas = pytest.importorskip("pandas")
    if not EVENTS.exists():
        pytest.skip("run scripts/run_pit_loss_checks.py first")
    return pandas.read_csv(EVENTS)


@pytest.fixture(scope="module")
def plans():
    pandas = pytest.importorskip("pandas")
    frame = pandas.read_csv(PLANS)
    frame["tyre_limited"] = frame["optimal_stops"] != frame["min_stops"]
    return frame


@pytest.fixture(scope="module")
def report() -> str:
    if not REPORT.exists():
        pytest.skip("run scripts/run_pit_loss_checks.py first")
    return REPORT.read_text(encoding="utf-8")


def test_every_race_season_contributed_stops(events, plans) -> None:
    """A silent loader failure would quietly narrow the sample."""
    covered = events.groupby(["series", "car_class", "year", "circuit"]).ngroups
    assert covered == len(plans), (
        f"{covered} race-seasons produced stops but the plans table has "
        f"{len(plans)}. Some race failed to load and the report is measured on "
        "less than it says."
    )


def test_driver_changes_are_detected_at_a_plausible_rate(events) -> None:
    """The detection was wrong once, and silently.

    Reading the change against the following lap instead of the previous one
    found driver changes on 0.1% of green stops, which is impossible in
    endurance racing and looked like a finding rather than a bug.
    """
    share = events.groupby(["series", "car_class"])["driver_change"].mean()
    assert share.min() > 0.15, (
        f"a class has driver changes on only {100 * share.min():.1f}% of green "
        "stops, which is below anything endurance racing produces. The "
        "detection is probably reading the wrong lap again."
    )
    assert share.max() < 0.80, (
        f"a class has driver changes on {100 * share.max():.0f}% of green "
        "stops, which is too high to be real"
    )


def test_a_driver_change_costs_more_in_every_class(events) -> None:
    """Objection 1's premise. If this stopped holding, the report's framing is wrong."""
    for unit, part in events.groupby(["series", "car_class"]):
        with_change = part.loc[part["driver_change"], "loss_s"].median()
        without = part.loc[~part["driver_change"], "loss_s"].median()
        assert with_change > without, (
            f"{unit}: a driver change is not slower ({with_change:.1f} s vs "
            f"{without:.1f} s), which contradicts the report"
        )


def test_the_class_ordering_survives_every_decomposition(events, plans) -> None:
    """Why the published table stands despite objection 1 being correct."""
    pandas = pytest.importorskip("pandas")
    plans = plans.assign(
        unit=plans["series"].str.upper() + " " + plans["car_class"]
    )
    share = plans.groupby("unit")["tyre_limited"].mean()
    events = events.assign(
        unit=events["series"].str.upper() + " " + events["car_class"]
    )

    def class_median(frame):
        per_race = frame.groupby(["unit", "year", "circuit"])["loss_s"].median()
        return per_race.groupby("unit").median()

    variants = {
        "every stop": class_median(events),
        "no driver change": class_median(events[~events["driver_change"]]),
        "driver change only": class_median(events[events["driver_change"]]),
        "published": plans.groupby("unit")["pit_loss_s"].median(),
    }
    ranks = {}
    for name, values in variants.items():
        table = pandas.DataFrame({"loss": values, "share": share}).dropna()
        ranks[name] = table["loss"].corr(table["share"], method="spearman")

    assert all(value < -0.9 for value in ranks.values()), (
        f"the ordering no longer holds under every decomposition: {ranks}"
    )
    spread = max(ranks.values()) - min(ranks.values())
    assert spread < 0.05, (
        "the rank correlation now depends on which population the median is "
        f"taken over (spread {spread:.3f}): {ranks}. The report says it does "
        "not, and that is the whole answer to objection 1."
    )


def test_pit_loss_is_more_a_circuit_property_than_a_season_property(plans) -> None:
    """The argument that the correlation's driver is exogenous."""
    plans = plans.assign(
        unit=plans["series"].str.upper() + " " + plans["car_class"]
    )
    grouped = plans.groupby(["unit", "circuit_canonical"])["pit_loss_s"]
    across_seasons = grouped.std()[grouped.size() >= 3].median()
    between_circuits = (
        grouped.median().groupby("unit").std().median()
    )
    assert between_circuits > 3 * across_seasons, (
        f"pit loss now varies {between_circuits:.1f} s between circuits against "
        f"{across_seasons:.1f} s between seasons of the same circuit. The "
        "report's exogeneity argument needs the first to dominate."
    )


def test_the_reverse_channel_stays_small_with_the_circuit_held_constant(
    plans,
) -> None:
    """Objection 2's answer: the right sign, far too small to matter."""
    numpy = pytest.importorskip("numpy")
    plans = plans.assign(
        unit=plans["series"].str.upper() + " " + plans["car_class"]
    )
    differences = []
    for _, part in plans.groupby(["unit", "circuit_canonical"]):
        limited = part.loc[part["tyre_limited"], "pit_loss_s"]
        fuel = part.loc[~part["tyre_limited"], "pit_loss_s"]
        if limited.empty or fuel.empty:
            continue
        differences.append(float(limited.median() - fuel.median()))

    assert differences, "no circuit-class ran both kinds of season any more"
    median = float(numpy.median(differences))
    assert abs(median) < 10.0, (
        f"the within-circuit difference is now {median:+.1f} s, which is no "
        "longer small against the twenty-second spread between circuits. The "
        "reverse channel would then need quantifying rather than bounding."
    )


def test_de_vries_is_credited_and_nothing_published_was_edited(report: str) -> None:
    assert "Wytze de Vries" in report
    assert "Nothing published has been edited" in report, (
        "the report should say plainly that Result 2 was left alone"
    )
