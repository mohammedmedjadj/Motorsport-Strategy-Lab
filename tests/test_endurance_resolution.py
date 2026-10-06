"""What the endurance degradation fits resolve, and the claims made about it.

The Formula 1 figure has never been shown without its share of unresolved
slopes. The endurance figure was, until this report, and the numbers it now
carries are worse than the Formula 1 ones — so they are exactly the numbers a
later refactor would quietly improve.

Three things are re-derived here rather than read from the reports:

- the counts each report states, against the fits table they claim to summarise;
- that fuel and tyre age remain inseparable, because the whole decision to
  publish a *net* slope rests on it;
- that the three championships are never pooled, and that no report quotes
  another's numbers.

The last one is a standing rule in this repository rather than a statistical
claim: WEC, IMSA and ELMS run different calendars with different classes, and a
figure averaged over the three describes none of them.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
FITS = REPO / "data" / "derived" / "endurance" / "endurance_degradation_fits.csv"
SUMMARY = REPO / "data" / "derived" / "endurance" / "endurance_slope_resolution.csv"
NUMBERS = REPO / "paper" / "numbers.tex"

REPORTS = {
    "wec": REPO / "reports" / "wec" / "slope_resolution.md",
    "imsa": REPO / "reports" / "imsa" / "slope_resolution.md",
    "elms": REPO / "reports" / "elms" / "slope_resolution.md",
}
SUFFIX = {"wec": "Wec", "imsa": "Imsa", "elms": "Elms"}


@pytest.fixture(scope="module")
def fits():
    pandas = pytest.importorskip("pandas")
    if not FITS.exists():
        pytest.skip("run scripts/run_endurance_models.py first")
    frame = pandas.read_csv(FITS)
    frame["crosses_zero"] = (frame["ci_low"] <= 0) & (frame["ci_high"] >= 0)
    return frame


@pytest.fixture(scope="module")
def reports() -> dict[str, str]:
    missing = [name for name, path in REPORTS.items() if not path.exists()]
    if missing:
        pytest.skip("run scripts/run_endurance_resolution.py first")
    return {
        name: path.read_text(encoding="utf-8") for name, path in REPORTS.items()
    }


@pytest.fixture(scope="module")
def macros() -> dict[str, str]:
    if not NUMBERS.exists():
        pytest.skip("paper/numbers.tex not generated")
    text = NUMBERS.read_text(encoding="utf-8")
    return dict(re.findall(r"\\newcommand\{\\(\w+)\}\{([^}]*)\}", text))


def test_each_report_states_its_own_counts(fits, reports) -> None:
    """The headline count, recomputed rather than trusted."""
    for series, text in reports.items():
        part = fits[fits["series"] == series]
        crossing = int(part["crosses_zero"].sum())
        expected = f"**{crossing} of {len(part)}**"
        assert expected in text, (
            f"{series}: the report should state {expected} slopes with an "
            "interval containing zero, recomputed from the fits table"
        )


def test_the_macros_agree_with_the_reports(fits, macros) -> None:
    """A paper that disagrees with its own report is the drift this prevents."""
    for series, suffix in SUFFIX.items():
        part = fits[fits["series"] == series]
        assert macros.get(f"NFits{suffix}") == str(len(part))
        assert macros.get(f"NSlopeZero{suffix}") == str(
            int(part["crosses_zero"].sum())
        )
        assert macros.get(f"NSlopeNegative{suffix}") == str(
            int((part["net_slope"] < 0).sum())
        )


def test_there_is_no_pooled_endurance_figure(macros) -> None:
    """One number for all three championships would describe none of them."""
    pooled = sorted(
        name
        for name in macros
        if re.fullmatch(r"(NFits|NSlopeZero|PctSlopeZero|NSeparable)", name)
    )
    assert not pooled, (
        f"these macros pool WEC, IMSA and ELMS into one figure: {pooled}. The "
        "three run different calendars and different classes; report them "
        "separately or not at all."
    )


def test_no_report_quotes_another_series(reports) -> None:
    """Each championship's report is readable on its own and only its own.

    A mention of another series in prose is fine and sometimes necessary. A
    *bolded count* belonging to another series is how two reports start
    drifting into one.
    """
    for series, text in reports.items():
        others = [name for name in REPORTS if name != series]
        for other in others:
            label = other.upper()
            offending = re.findall(
                rf"\*\*[^*]*\d[^*]*\*\*[^.]*\b{label}\b", text
            )
            assert not offending, (
                f"the {series.upper()} report attributes a count to {label}: "
                f"{offending}"
            )


def test_fuel_and_tyre_age_are_still_inseparable(fits) -> None:
    """The reason the published quantity is a net slope and not a tyre slope.

    If this ever flipped, publishing only the net slope would stop being the
    honest choice and start being a missing result.
    """
    for series, part in fits.groupby("series"):
        share = part["separable"].mean()
        assert share < 0.25, (
            f"{series}: fuel and tyre age now separate in "
            f"{100 * share:.0f}% of fits. The net-slope-only framing, and the "
            "paragraph in src/degradation/endurance.py that justifies it, "
            "both need revisiting."
        )


def test_negative_slopes_are_named_as_a_defect_not_a_finding(reports) -> None:
    """A car that gets faster on older tyres is an omitted variable, not news."""
    for series, text in reports.items():
        assert "track evolution" in text, (
            f"{series}: the report reports negative slopes without naming the "
            "omitted variable that produces them"
        )
        assert "track_evolution_omitted_variable.md" in text, (
            f"{series}: the report should point at the diagnosis rather than "
            "restate it"
        )


def test_the_summary_table_covers_every_series_and_class(fits) -> None:
    pandas = pytest.importorskip("pandas")
    if not SUMMARY.exists():
        pytest.skip("run scripts/run_endurance_resolution.py first")
    summary = pandas.read_csv(SUMMARY)
    expected = fits.groupby(["series", "car_class"]).ngroups
    assert len(summary) == expected, (
        f"the summary has {len(summary)} rows for {expected} series-classes; "
        "a class dropped out silently"
    )
    assert summary["n_fits"].sum() == len(fits)
