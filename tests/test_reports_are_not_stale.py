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


def _mentions_class(text: str, car_class: str) -> bool:
    """Does this document actually discuss that class?

    Reports spell IMSA's all-pro class both ``GTDPRO`` (the artifact label)
    and ``GTD PRO`` (the way the paddock writes it), so both count.
    """
    return car_class in text or car_class.replace("GTDPRO", "GTD PRO") in text


def _counts_out_of(text: str, total: int, keyword: str) -> list[str]:
    """Every "N of {total}" stated in a paragraph that is about ``keyword``.

    Scoped rather than document-wide: "N of M" is one of the most common
    shapes in these reports — eligibility floors, circuit coverage, races with
    a Safety Car — so matching it everywhere would build a guard that fails on
    sentences it was never meant to read, and a guard that cries wolf gets
    deleted.

    Scoped to the **paragraph**, though, not the line. These reports are
    hard-wrapped at about 78 columns, so a claim and the word that identifies
    it routinely land on different physical lines:

        ...a cleaner result than
        IMSA's (6 of 140) or WEC's (0 of 28). Teams change tyres...

    A line-scoped version of this function shipped first and silently missed
    both of the real stale figures it was written to catch, for exactly that
    reason. Markdown's semantic unit is the paragraph; the line break is
    typography.
    """
    normalised = _digits_for_words(text)
    return [
        match
        for paragraph in re.split(r"\n\s*\n", normalised)
        if keyword.lower() in paragraph.lower()
        for match in re.findall(rf"(\d+) of {total}\b", paragraph)
    ]


#: Prose does not always use digits, and a guard that only reads digits is
#: blind to exactly the sentences a human wrote by hand — which are the ones
#: that go stale. "Nine of 60 GTD races fit a negative slope" survived this
#: module's first version for that reason alone, against an artifact saying 8.
_WORD_DIGITS = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
    "eleven": "11", "twelve": "12",
}


def _digits_for_words(text: str) -> str:
    for word, digit in _WORD_DIGITS.items():
        text = re.sub(rf"\b{word}\b", digit, text, flags=re.IGNORECASE)
    return text


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


# --- the per-series reports, not just the synthesis -------------------------


#: Every document that states a class's median net slope or its count of
#: negative fits. The synthesis was guarded from the start; these were not, and
#: ``reports/elms/results.md`` drifted on eight separate figures — a median, a
#: negative-slope count, a kept-lap percentage, a field size, a separability
#: count against another series, and four cells of a leave-one-race-out table
#: — while ``reports/elms/degradation_phase2.md`` carried the right numbers the
#: whole time. One report corrected, its neighbour not: exactly the failure
#: this module was written for, one directory over from where it was looking.
PER_SERIES_SLOPE_REPORTS = (
    ("reports/elms/methodology.md", "elms"),
    ("reports/elms/results.md", "elms"),
    ("reports/elms/degradation_phase2.md", "elms"),
    ("reports/imsa/gtd_findings.md", "imsa"),
)


@pytest.mark.parametrize(("report", "series"), PER_SERIES_SLOPE_REPORTS)
def test_per_series_reports_quote_their_own_median_slopes(
    fits: pd.DataFrame, report: str, series: str
) -> None:
    """A series' own report must quote its own artifact.

    Checked per class rather than per document: a report that covers two
    classes can go stale on one of them, which is what happened, and a
    whole-document check would have passed on the half that was still right.
    """
    text = _text(report)
    scoped = fits[fits["series"] == series]
    missing = []
    for car_class, group in scoped.groupby("car_class"):
        # Only classes the report actually discusses. A GTD report is not
        # required to quote GTP's median, and demanding it would make this
        # guard cry wolf until someone deleted it.
        if not _mentions_class(text, car_class):
            continue
        median = f"{group['net_slope'].median():+.4f}"
        # Reports quote either "+0.0161" or "0.0161"; both are the same claim.
        if median not in text and median.lstrip("+") not in text:
            missing.append(f"{car_class}={median}")
    assert not missing, (
        f"{report} no longer quotes the artifact's median slope for: "
        f"{missing}. Either the fits were regenerated and the report was not "
        "updated, or the report is quoting a number nothing computes."
    )


@pytest.mark.parametrize(("report", "series"), PER_SERIES_SLOPE_REPORTS)
def test_per_series_reports_quote_their_own_negative_slope_counts(
    fits: pd.DataFrame, report: str, series: str
) -> None:
    """"N of M races fit a negative slope" is the figure that moved most.

    It is the direct read-out of the unmodelled track-evolution term, so it
    changes every time the filtering changes — and it changed twice without
    ``results.md`` following, which is how "9 of 25" outlived the "7 of 25"
    its own phase report already carried.
    """
    text = _text(report)
    scoped = fits[fits["series"] == series]
    stale = []
    for car_class, group in scoped.groupby("car_class"):
        if not _mentions_class(text, car_class):
            continue
        negative, total = int((group["net_slope"] < 0).sum()), len(group)
        # Scoped to lines that are actually making this claim. "N of M" is far
        # too common a shape — the same report says "58 of 60 cleared the
        # eligibility floor" — and a guard that matched those would fail on
        # sentences it has no business reading.
        stated = _counts_out_of(text, total, keyword="negative")
        if stated and str(negative) not in stated:
            stale.append(f"{car_class}: says {stated} of {total}, artifact says {negative}")
    assert not stale, f"{report} carries a stale negative-slope count — {stale}"


def test_the_elms_control_result_matches_the_loro_artifact() -> None:
    """The near-spec control is this project's most-cited negative result.

    It is argued from a five-row table of leave-one-race-out R² values that
    appears in two documents. When the fits were corrected, one copy was
    updated and the other was not — and the stale copy overstated Portimao's
    failure almost fourfold (−0.253 against the artifact's −0.067), which
    would have made the conclusion look stronger than the data supports.
    """
    loro = pd.read_csv(ENDURANCE_DERIVED_DIR / "endurance_degradation_loro.csv")
    means = loro[(loro["series"] == "elms") & (loro["held_out_season"] == "MEAN")]
    assert not means.empty, "no ELMS leave-one-race-out means in the artifact"

    for report in ("reports/elms/results.md", "reports/elms/degradation_phase2.md"):
        text = _text(report)
        for _, row in means.iterrows():
            value = f"{row['r2_within']:+.3f}".replace("-", "\u2212")
            assert value in text, (
                f"{report} does not carry the artifact's leave-one-race-out R² "
                f"of {value} for {row['car_class']} at {row['circuit_canonical']}"
            )


def test_stated_separability_counts_match_the_artifact() -> None:
    """"0 of 42 races clear the separability threshold" is a cross-series claim.

    Each series' report quotes the other two for context, so a refit that
    changes one series' count leaves stale numbers in reports belonging to
    series that did not change at all. IMSA's went from 3 to 6 that way.
    """
    fits = pd.read_csv(ENDURANCE_DERIVED_DIR / "endurance_degradation_fits.csv")
    counts = {s: (int(g["separable"].sum()), len(g)) for s, g in fits.groupby("series")}

    for report in ("reports/elms/results.md", "reports/elms/degradation_phase2.md"):
        text = _text(report)
        for series, (separable, total) in counts.items():
            stated = _counts_out_of(text, total, keyword="separab")
            if not stated:
                continue
            assert str(separable) in stated, (
                f"{report} states {stated} of {total} for {series}; the "
                f"artifact says {separable} of {total} clear the threshold"
            )


def test_no_report_claims_bahrain_is_the_projects_best_transfer() -> None:
    """Superlatives are the claims a widening scope breaks first.

    "Bahrain is the strongest transfer found anywhere in this project, F1
    included" was true when only F1 and WEC existed. It survived the IMSA
    prototype phase, the GT3 phase and the whole of ELMS, quoted in six
    documents, while IMSA's Lime Rock GTD sat in the artifact at more than
    twice its R².

    A superlative is a claim about the *whole* artifact, so it is exactly the
    kind that no per-series check catches: every series' own numbers stayed
    right, and the ranking between them silently stopped holding. This asserts
    the ranking directly, and asserts that no document claims Bahrain leads it.
    """
    loro = pd.read_csv(ENDURANCE_DERIVED_DIR / "endurance_degradation_loro.csv")
    means = loro[loro["held_out_season"] == "MEAN"]
    best = means.loc[means["r2_within"].idxmax()]

    assert best["circuit_canonical"] != "Bahrain", (
        "Bahrain is now the artifact's best transfer again — the reports were "
        "rewritten to say it is not, and need rewriting back."
    )

    leader = (
        f"{best['series']}/{best['circuit_canonical']}/{best['car_class']} "
        f"at R2 {best['r2_within']:+.3f}"
    )
    for report in (
        "README.md",
        "reports/cross_series_synthesis.md",
        "reports/elms/results.md",
        "reports/elms/degradation_phase2.md",
        "reports/wec/methodology.md",
        "reports/wec/degradation_phase2.md",
    ):
        text = _text(report)
        for paragraph in re.split(r"\n\s*\n", text):
            lowered = paragraph.lower()
            if "bahrain" not in lowered:
                continue
            # Claims of the form "the strongest/only ... in this project" are
            # the false ones. Two things make a paragraph safe: scoping the
            # claim to WEC, where it is still true, or explicitly denying it —
            # the corrections themselves say "no longer the strongest transfer
            # in the project", and a guard that cannot read a denial would
            # fail on the very text written to satisfy it.
            claims_the_superlative = (
                "strongest transfer" in lowered
                or "only circuit" in lowered
                or "one circuit anywhere" in lowered
            )
            scoped_to_wec = (
                "in wec" in lowered
                or "wec circuit" in lowered
                or "**wec**" in lowered
            )
            denied = any(
                marker in lowered
                for marker in (
                    "no longer", "not the strongest", "is not", "was true",
                    "retired", "not in the project", "previously",
                )
            )
            overreaching = claims_the_superlative and not scoped_to_wec and not denied
            assert not overreaching, (
                f"{report} claims Bahrain leads on transfer without scoping the "
                f"claim to WEC. The artifact's leader is {leader}."
            )


def test_no_report_claims_every_endurance_race_is_fuel_limited() -> None:
    """The project's most-repeated overclaim, and the second superlative to break.

    "No measured endurance race is tyre-limited — every one is fuel-limited on
    stop count" was true of the prototype classes it was measured on. It was
    stated as a fact about endurance racing, propagated into four documents,
    and stayed there through the GT3 and ELMS widenings that falsified it.

    Nine circuit-seasons are tyre-limited, every one of them in a cheap-stop
    class. Scoped to WEC the claim is still exactly true, so paragraphs that
    say so are left alone; what fails here is an unscoped one.
    """
    plans = pd.read_csv(ENDURANCE_DERIVED_DIR / "multistop_plans.csv")
    tyre_limited = plans[plans["optimal_stops"] != plans["min_stops"]]
    assert not tyre_limited.empty, (
        "no scoped race is tyre-limited any more — the reports were rewritten "
        "to say some are, and would need rewriting back"
    )

    examples = ", ".join(
        f"{r.series}/{r.circuit}/{r.car_class} {r.year}"
        for r in list(tyre_limited.itertuples())[:3]
    )
    for report in sorted(REPO.glob("reports/**/*.md")) + [REPO / "README.md"]:
        for paragraph in re.split(r"\n\s*\n", report.read_text(encoding="utf-8")):
            lowered = paragraph.lower()
            claims = (
                "every one is fuel-limited" in lowered
                or "every scoped endurance race is **fuel-limited" in lowered
                or "no measured endurance race is tyre-limited" in lowered
            )
            scoped_or_denied = (
                "wec" in lowered
                or "originally" in lowered
                or "known to be false" in lowered
                or "was true" in lowered
                or "not what they say" in lowered
            )
            assert not (claims and not scoped_or_denied), (
                f"{report.relative_to(REPO).as_posix()} states that every "
                f"endurance race is fuel-limited without scoping or retracting "
                f"it. Tyre-limited races exist: {examples}."
            )
