"""The crew-rating comparison, pinned to the artifacts.

This test exists because its subject did not. The comparison was run by hand,
written into two reports and quoted in the README as a headline finding, with
no committed code behind it. The slopes underneath it then changed twice — the
traffic-trim correction and the field-wide hysteresis filter — and nothing
recomputed it, because there was nothing to recompute.

By the time anyone looked, the published ELMS p-value of 0.0093 had become
0.148 and the published IMSA p-value of 0.085 had become 0.032: the two
championships had **swapped** which one reached significance, and the README's
supporting sentence pointed the wrong way. The conclusion drawn from them —
that there is no consistent crew effect — happened to survive. It survived by
luck, not by construction, and these tests are what replaces the luck.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest

from src.degradation.crew_rating import (
    CREW_PAIRS,
    CrewPair,
    compare_crew_ratings,
    robustness,
)

REPO = Path(__file__).resolve().parents[1]
FITS = REPO / "data" / "derived" / "endurance" / "endurance_degradation_fits.csv"


@pytest.fixture(scope="module")
def fits() -> pd.DataFrame:
    return pd.read_csv(FITS)


def _text(relative: str) -> str:
    return (REPO / relative).read_text(encoding="utf-8")


def test_both_natural_experiments_still_pair(fits: pd.DataFrame) -> None:
    """Both comparisons must survive the scope, or the finding has no data.

    A pair count that quietly collapses — a renamed class label, a season
    dropped from the scope — would leave the reports quoting a test that no
    longer runs on anything.
    """
    results = {c.series: c for c in compare_crew_ratings(fits)}
    assert set(results) == {"imsa", "elms"}
    assert results["imsa"].n_pairs >= 40
    assert results["elms"].n_pairs >= 15


def test_pairs_are_keyed_on_the_race_not_the_circuit(fits: pd.DataFrame) -> None:
    """IMSA ran two distinct races at Watkins Glen in 2021.

    ``pivot_table`` averages duplicate keys by default and says nothing, so
    pairing on ``circuit_canonical`` would silently fuse two races into one
    and shrink the sample without any visible failure. This asserts the pair
    count equals the number of races where both classes ran, counted directly.
    """
    imsa = fits[(fits["series"] == "imsa") & (fits["season"] >= 2022)]
    by_race = imsa.groupby(["event", "season"])["car_class"].apply(set)
    expected = sum(1 for classes in by_race if {"GTD", "GTDPRO"} <= classes)

    result = next(c for c in compare_crew_ratings(fits) if c.series == "imsa")
    assert result.n_pairs == expected, (
        f"{result.n_pairs} pairs against {expected} races carrying both "
        "classes — the pairing key is losing or fusing races"
    )


def test_the_two_experiments_disagree_in_direction(fits: pd.DataFrame) -> None:
    """The project's actual finding, asserted as a property.

    Not pinned to decimals: the claim is that one championship's amateur crews
    look *steeper* and the other's look *shallower*, which is what makes "no
    consistent crew effect" the honest reading. If a regeneration ever brought
    both into line, that sentence would need rewriting and this should fail.
    """
    results = {c.series: c for c in compare_crew_ratings(fits)}
    imsa = results["imsa"].median_difference_s
    elms = results["elms"].median_difference_s
    assert imsa > 0 > elms, (
        f"the two tests no longer disagree (IMSA {imsa:+.4f}, ELMS {elms:+.4f}); "
        "the reports claim they do"
    )


@pytest.mark.parametrize("pair", CREW_PAIRS, ids=lambda p: p.series)
def test_no_crew_result_is_robustly_significant(fits: pd.DataFrame, pair: CrewPair) -> None:
    """Neither effect survives its own robustness checks.

    IMSA's headline test reaches p = 0.032, which read alone would license
    "amateur crews degrade faster". It does not survive dropping magnitudes
    for a sign test, dropping the partial current season, or dropping the
    races hit by the known track-evolution defect — all three put it back
    above 0.05.

    This is the assertion the reports rest on, so it is checked rather than
    described. If a future season ever made an effect hold up under every
    variant, this fails and the write-up has to change — which is the point.
    """
    variants = robustness(fits, pair)
    assert variants, f"no robustness variants ran for {pair.series}"
    fragile = [v for v in variants if v.p_value >= 0.05]
    assert fragile, (
        f"{pair.series}: every robustness variant now clears p < 0.05 "
        f"({[(v.label, round(v.p_value, 4)) for v in variants]}) — the reports "
        "call this effect fragile and would need rewriting"
    )


def test_the_primary_crew_documents_quote_both_results(fits: pd.DataFrame) -> None:
    """The three documents whose subject *is* this comparison must carry it.

    Kept separate from the sweep below because the failure modes differ: this
    catches a document that stopped reporting a result, the sweep catches one
    that reports a result nothing computes.
    """
    documents = [
        "reports/elms/crew_rating_findings.md",
        "reports/cross_series/synthesis.md",
        # The crew-rating results are per-series detail, so they live in the
        # long README. The short one carries the three headline results and
        # points here.
        "docs/full-readme.md",
    ]
    for result in compare_crew_ratings(fits):
        p_value = f"{result.p_value:.3f}"
        difference = f"{abs(result.median_difference_s):.4f}"
        for document in documents:
            text = _text(document)
            assert p_value in text, (
                f"{document} does not carry {result.series}'s p-value of {p_value}"
            )
            assert difference in text, (
                f"{document} does not carry {result.series}'s median "
                f"difference of {difference}"
            )


#: Words that mark a quoted figure as deliberately historical. The post-mortem
#: sections quote the superseded p-values on purpose — that is the whole point
#: of a post-mortem — so a sweep that flagged them would be unusable.
_HISTORICAL = ("previously", "originally", "used to", "before the", "superseded")

#: Everything that could carry a crew figure in front of a reader, including
#: the demo, which is not a report and was carrying the inverted numbers in its
#: user-facing caveat text after all four reports had been corrected.
_SWEPT = ("README.md", "docs/full-readme.md", "demo/app.py",
          "reports/**/*.md", "reports/*.md")


def _crew_paragraphs(text: str) -> list[str]:
    """Paragraphs that are talking about the crew comparison.

    Identified by a class pair plus the vocabulary of the test itself, so an
    unrelated p-value elsewhere in the same document is not swept up.
    """
    out = []
    for paragraph in re.split(r"\n\s*\n", text):
        lowered = paragraph.lower()
        if any(word in lowered for word in _HISTORICAL):
            continue
        names_a_pair = "pro/am" in lowered or "gtd pro" in lowered
        is_the_test = "wilcoxon" in lowered or "pair" in lowered or "sign test" in lowered
        if names_a_pair and is_the_test:
            out.append(paragraph)
    return out


def test_no_document_quotes_a_crew_p_value_the_code_cannot_produce(
    fits: pd.DataFrame,
) -> None:
    """A negative guard, so it costs nothing to point at every file.

    The positive form above ("this document must contain X") cannot be pointed
    at everything: a report that mentions ELMS once in passing is not obliged
    to quote ELMS's p-value, so demanding it produces false failures and the
    guard gets deleted. Asking instead that **no** document states a crew
    p-value the code does not produce scales to the whole repository and
    catches the real defect exactly.

    It is pointed at ``demo/app.py`` as well as the reports. When these numbers
    were corrected, the demo's user-facing caveat still read "shallower by
    0.0143 s/lap (p = 0.0093)" after all four reports had been fixed — the shop
    window outlived the documentation, which is the worst way round.
    """
    allowed = set()
    for result in compare_crew_ratings(fits):
        allowed.add(f"{result.p_value:.3f}")
        allowed.add(f"{result.p_value:.4f}")
        for pair in CREW_PAIRS:
            if pair.series != result.series:
                continue
            for variant in robustness(fits, pair):
                allowed.add(f"{variant.p_value:.3f}")
                allowed.add(f"{variant.p_value:.4f}")

    offenders = []
    for pattern in _SWEPT:
        for path in sorted(REPO.glob(pattern)):
            text = path.read_text(encoding="utf-8")
            for paragraph in _crew_paragraphs(text):
                for quoted in re.findall(r"p\s*=\s*(\d\.\d+)", paragraph):
                    if quoted not in allowed:
                        offenders.append(
                            f"{path.relative_to(REPO).as_posix()}: p = {quoted}"
                        )

    assert not offenders, (
        f"crew p-values quoted that the code does not produce: {offenders}. "
        f"Computable values are {sorted(allowed)}. If one of these is a "
        "deliberate historical reference, say so in the same paragraph."
    )
