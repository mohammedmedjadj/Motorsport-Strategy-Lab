"""The overcut measurement, and the three ways it could quietly become wrong.

This report goes to Salminen, whose model it measures, so the failure modes
that matter are the ones that would make it look careless rather than the ones
that make it inaccurate.

The first draft had two. It divided by unresolved slopes, which handed
Singapore's soft tyre a requirement of four thousand laps out of a slope of
0.0001 s/lap and put it at the top of the headline table. And it took the
median of `a` over one population while taking `a` at the median of `theta`
over another, so two tables one after the next disagreed about the same number.
Both are guarded here, because both read as arithmetic errors to anyone
checking.

The third is the direction of the bound. Every figure in the report is claimed
to understate the difficulty: epsilon is set to zero, which is the case most
favourable to the defence. If that ever flipped, the report would be overstating
its case to the one reader who can check it line by line.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
TABLE = REPO / "data" / "derived" / "f1" / "overcut_feasibility.csv"
REPORT = REPO / "reports" / "f1" / "overcut_feasibility.md"
COEFS = REPO / "data" / "derived" / "f1" / "degradation_coefficients.csv"


@pytest.fixture(scope="module")
def table():
    pandas = pytest.importorskip("pandas")
    if not TABLE.exists():
        pytest.skip("run scripts/run_overcut_feasibility.py first")
    return pandas.read_csv(TABLE)


@pytest.fixture(scope="module")
def report() -> str:
    if not REPORT.exists():
        pytest.skip("run scripts/run_overcut_feasibility.py first")
    return REPORT.read_text(encoding="utf-8")


def test_unresolved_slopes_are_never_divided_by(table) -> None:
    """The four-thousand-lap bug, which was in the first headline table."""
    unresolved = table[~table["resolved"]]
    assert not unresolved.empty, (
        "no unresolved slopes at all now, which would make this report's "
        "central caveat obsolete rather than satisfied"
    )
    assert unresolved["d2_unreachable"].all(), (
        "an unresolved slope is being treated as one where D2 can be reached. "
        "No tyre advantage is identified there, so there is nothing to build "
        "the overcut from."
    )


def test_the_headline_tables_share_a_denominator(table, report) -> None:
    """Two medians of the same quantity, disagreeing, in adjacent tables."""
    pandas = pytest.importorskip("pandas")
    main = table[table["o_s"] == 0.55]
    resolved = main[main["resolved"]]
    median_of_a = float(resolved["a_laps"].median())
    a_of_median_theta = 0.55 / float(resolved["deg_p1"].median())
    assert round(median_of_a) == round(a_of_median_theta), (
        f"the median required advantage is {median_of_a:.1f} laps, while the "
        f"requirement at the median slope is {a_of_median_theta:.1f}. Both "
        "are right on their own population and together they read as an "
        "error. Whatever the report prints, it must print one of them."
    )
    assert f"**{round(median_of_a)}**" in report, (
        f"the report does not state {round(median_of_a)} as the median"
    )


def test_every_figure_understates_the_difficulty(table) -> None:
    """The report claims a lower bound. This is what makes the claim true.

    epsilon is fixed at zero. Any positive raw-pace deficit raises the numerator
    of (o + epsilon) / theta, so the required advantage can only grow.
    """
    main = table[table["o_s"] == 0.55]
    resolved = main[main["resolved"]]
    implied = 0.55 / resolved["deg_p1"]
    assert (resolved["a_laps"] - implied).abs().max() < 1e-9, (
        "the required advantage no longer equals o / theta, so epsilon is not "
        "zero any more and the report's claim that every figure is a lower "
        "bound on the difficulty is no longer the right way round"
    )


def test_the_interval_on_a_runs_the_right_way(table) -> None:
    """`a` falls as theta rises, so theta's upper bound gives a's lower one."""
    numpy = pytest.importorskip("numpy")
    rows = table[table["resolved"]]
    assert (rows["a_low"] <= rows["a_laps"]).all(), (
        "the lower bound on the required advantage exceeds the point "
        "estimate, so the interval has been inverted"
    )
    finite = rows[numpy.isfinite(rows["a_high"])]
    assert (finite["a_high"] >= finite["a_laps"]).all()


def test_salminen_theta_sits_high_in_the_measured_distribution(table) -> None:
    """The whole point of the report. If this stopped holding it would be moot."""
    main = table[table["o_s"] == 0.55]
    resolved = main[main["resolved"]]
    share = float((resolved["deg_p1"] < 0.10).mean())
    assert share > 0.5, (
        f"only {100 * share:.0f}% of resolved slopes now degrade more slowly "
        "than the 0.1 s/lap of the worked example. The report's argument is "
        "that his example sits near the top of the real distribution, and at "
        "this share it no longer does."
    )


def test_the_report_names_rather_than_only_summarising(report) -> None:
    """Five quantiles are not checkable by the person receiving them."""
    for circuit in ("jeddah", "baku", "singapore"):
        assert circuit in report, (
            f"{circuit} is not named anywhere, so the distribution is "
            "reported only as summary statistics"
        )
    assert "not identified" in report, (
        "the report should say plainly where the rate is not identified "
        "rather than printing a number there"
    )


def test_the_table_covers_every_fitted_slope(table) -> None:
    pandas = pytest.importorskip("pandas")
    coefs = pandas.read_csv(COEFS)
    per_threshold = table.groupby("o_s").size()
    assert (per_threshold == len(coefs)).all(), (
        f"the table holds {per_threshold.to_dict()} rows per threshold for "
        f"{len(coefs)} fitted slopes; some circuit-compound dropped out"
    )
