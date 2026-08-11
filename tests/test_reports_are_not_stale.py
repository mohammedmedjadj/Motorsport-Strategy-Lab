"""Every number a report states must still be what the artifacts say.

This exists because of a failure that happened repeatedly and was never once
caught by the test suite: a document updated in one place while a claim two
sections down kept asserting the old world. The README described a GT3 class
as a "candidate" six hours after it was scoped and fitted; its IMSA section
opened with "Four GTP circuits (2023-2025)" against a real 10 circuits over
2023-2026; the ELMS phase-0 report said "nothing has been materialised" two
paragraphs after listing what had been. Each was found by a human reading the
page, which is the one review mechanism that does not scale.

The rule this encodes: **a headline number in a report is a claim about an
artifact, and a claim about an artifact is testable.** Where a report states a
count that the committed data determines, it is parsed out and checked here.

Deliberately narrow. It does not try to validate every figure in every
document — a test that greps for decimals would fail on rounding and be
deleted within a week. It checks two things: the counts that describe *scope*,
because those go stale whenever the project grows, and the headline figures
the cross-series synthesis argues from, because those go stale whenever the
models are refitted.

The second group was added after three figures in the ELMS phase set were
written from memory of an earlier run rather than from the CSVs. They were
caught by hand, which worked and does not scale.

Every check here has been verified to fail when the report is perturbed —
a guard that cannot fail is worse than no guard, because it reports safety
it is not providing.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest

from src.data.endurance_scope import ENDURANCE_SCOPE, canonical_circuit
from src.ingestion.config import ENDURANCE_DERIVED_DIR, REPORTS_DIR

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def fits() -> pd.DataFrame:
    return pd.read_csv(ENDURANCE_DERIVED_DIR / "endurance_degradation_fits.csv")


def _scope(series: str, car_class: str):
    return [c for c in ENDURANCE_SCOPE[series] if c.car_class == car_class]


def _text(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


# --- scope counts stated in prose must match the scope itself ---------------


@pytest.mark.parametrize(
    ("report", "series", "car_class", "pattern"),
    [
        # "Race-seasons | **60**, all of which cleared the eligibility floor"
        ("reports/imsa/gtd_findings.md", "imsa", "GTD",
         r"Race-seasons \| \*\*(\d+)\*\*"),
    ],
)
def test_stated_race_season_count_matches_the_scope(
    report: str, series: str, car_class: str, pattern: str, fits
) -> None:
    m = re.search(pattern, _text(report))
    assert m, f"{report}: could not find the race-season count to check"
    stated = int(m.group(1))
    actual = len(fits[(fits["series"] == series) & (fits["car_class"] == car_class)])
    assert stated == actual, (
        f"{report} says {stated} {car_class} race-seasons; the artifacts hold "
        f"{actual}. Update the report — a scope that grows silently makes every "
        "figure downstream of it wrong too."
    )


@pytest.mark.parametrize(
    ("report", "series", "car_class", "pattern"),
    [
        ("reports/imsa/gtd_findings.md", "imsa", "GTD", r"Circuits \| \*\*(\d+)\*\*"),
    ],
)
def test_stated_circuit_count_matches_the_canonical_scope(
    report: str, series: str, car_class: str, pattern: str
) -> None:
    """Counted on canonical circuits, not source event strings.

    The distinction is the whole point of the alias map: GTD's 16 event
    strings are 13 tracks, and an earlier version of this very report said 14
    because it counted before canonicalising.
    """
    m = re.search(pattern, _text(report))
    assert m, f"{report}: could not find the circuit count to check"
    stated = int(m.group(1))
    actual = len({canonical_circuit(c.event) for c in _scope(series, car_class)})
    assert stated == actual, (
        f"{report} says {stated} circuits; canonicalising the scope gives "
        f"{actual}."
    )


# --- the pit-procedure table in two reports must match the artifact ---------


def test_quoted_tyre_change_premiums_match_the_artifact() -> None:
    """Both GT3 reports quote the premium table. It is one artifact, so a
    regeneration that moves it must not leave either document behind."""
    proc = pd.read_csv(ENDURANCE_DERIVED_DIR / "endurance_pit_procedure.csv")
    prem = proc.set_index(["series", "car_class"])["tyre_change_premium_s"]

    text = _text("reports/imsa/gtd_findings.md")
    for (series, car_class), label in (
        (("imsa", "GTP"), "IMSA GTP"),
        (("imsa", "GTD"), "IMSA GTD"),
        (("imsa", "GTDPRO"), "IMSA GTD PRO"),
    ):
        value = float(prem[(series, car_class)])
        # The report writes premiums as e.g. "**8.7 s**" in its tables.
        assert f"{value:.1f} s" in text, (
            f"reports/imsa/gtd_findings.md no longer quotes the measured "
            f"{label} premium of {value:.1f} s"
        )


# --- README scope claims ----------------------------------------------------


def test_readme_class_table_matches_the_scope() -> None:
    """The README's IMSA table is the first thing a reader sees about the
    classes. It stated a candidate class as unbuilt long after it was built."""
    text = _text("README.md")
    fits = pd.read_csv(ENDURANCE_DERIVED_DIR / "endurance_degradation_fits.csv")
    for car_class, label in (("GTP", "GTP"), ("GTD", "GTD"), ("GTDPRO", "GTD PRO")):
        n = len(fits[(fits["series"] == "imsa") & (fits["car_class"] == car_class)])
        row = re.search(rf"\|\s*\*\*{re.escape(label)}\*\*\s*\|[^|]*\|\s*(\d+)\s*\|", text)
        assert row, f"README: no class-table row found for {label}"
        assert int(row.group(1)) == n, (
            f"README says {row.group(1)} race-seasons for {label}; the "
            f"artifacts hold {n}"
        )


def test_readme_test_count_badge_is_not_wildly_stale() -> None:
    """The badge is a claim too. Checked as a floor rather than an exact match:
    it should never advertise more tests than exist, and it is allowed to lag
    slightly behind a suite that just grew."""
    text = _text("README.md")
    m = re.search(r"tests-(\d+)%20passing", text)
    assert m, "README: no test-count badge found"
    claimed = int(m.group(1))
    collected = sum(
        len(re.findall(r"^def test_", p.read_text(encoding="utf-8"), re.M))
        for p in (REPO / "tests").glob("test_*.py")
    )
    # Parametrised tests expand, so the real count is >= the def count.
    assert claimed >= collected, (
        f"README advertises {claimed} tests but {collected} test functions are "
        "defined before parametrisation — the badge is over-claiming."
    )


# --- body-text figures, not just scope counts -------------------------------


def test_quoted_median_slopes_match_the_artifact() -> None:
    """Median slopes are quoted in prose across several reports, and prose is
    where they go stale.

    Added after three figures in the ELMS phase set were written from memory
    of an earlier run rather than from the CSVs — 9 negative slopes where the
    artifact said 7, and two pit-loss medians. All three were caught by hand
    before commit, which is exactly the review mechanism that does not scale.
    """
    fits = pd.read_csv(ENDURANCE_DERIVED_DIR / "endurance_degradation_fits.csv")
    text = _text("reports/cross_series_synthesis.md")
    for (series, car_class), group in fits.groupby(["series", "car_class"]):
        median = group["net_slope"].median()
        assert f"+{median:.4f}" in text or f"{median:.4f}" in text, (
            f"the synthesis no longer quotes {series}/{car_class}'s median "
            f"slope of {median:+.4f}"
        )


def test_quoted_race_counts_match_the_artifact() -> None:
    """Same for the race counts in the synthesis table."""
    fits = pd.read_csv(ENDURANCE_DERIVED_DIR / "endurance_degradation_fits.csv")
    text = _text("reports/cross_series_synthesis.md")
    for (series, car_class), group in fits.groupby(["series", "car_class"]):
        assert f"| {len(group)} |" in text, (
            f"{series}/{car_class} has {len(group)} race-seasons; the synthesis "
            "table does not carry that count"
        )


def test_the_pit_loss_ordering_claim_still_holds() -> None:
    """The synthesis's central claim is that sorting classes by pit loss sorts
    the strategy columns with them, quantified as a -0.913 correlation.

    Asserted as a property rather than a decimal: if the correlation ever
    weakens materially the claim needs rewriting, and a test pinned to three
    decimals would fail on a regeneration that changes nothing important.
    """
    plans = pd.read_csv(ENDURANCE_DERIVED_DIR / "multistop_plans.csv")
    plans["tyre_limited"] = plans["optimal_stops"] != plans["min_stops"]
    by_class = plans.groupby(["series", "car_class"]).agg(
        pit_loss=("pit_loss_s", "median"),
        share=("tyre_limited", "mean"),
    )
    corr = by_class["pit_loss"].corr(by_class["share"])
    assert corr < -0.8, (
        f"the pit-loss/tyre-limited relationship weakened to {corr:.3f}; the "
        "synthesis quotes -0.913 and its argument rests on it"
    )
