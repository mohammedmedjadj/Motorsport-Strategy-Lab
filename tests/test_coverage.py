"""Every modelling layer covers the scope it claims to, or says which it does not.

The defect this guards against is not a wrong number. It is a layer that runs
on part of the scope while its output is quoted as a fact about the project.

The multi-stop planner is the case that prompted it. It produces this project's
headline strategy conclusion — which races are fuel-limited, which are
tyre-limited, and the −0.913 correlation between a class's pit loss and its
share of tyre-limited circuits — and it ran on **65 of 209** modelled
race-seasons. One arbitrary season per circuit-class, justified in a comment on
the grounds that "fuel range and stop structure are circuit properties".

Fuel range is. The **degradation slope is not**, and the plan trades tyre loss
against pit loss, so whether a race comes out tyre-limited depends on that
season's fitted slope. Two reports over, this project's most-cited result is
that slopes fail to transfer between seasons. The justification was refuted by
the project's own central finding and nobody noticed, because nothing put the
two side by side.

That is what a coverage test is for: it is not checking arithmetic, it is
checking that the shape of the evidence matches the shape of the claim.
"""

from __future__ import annotations

import pytest

from src.data.coverage import ENDURANCE_LAYERS, Layer, measure, report

#: Layers allowed to be short of full coverage, and why. Every entry is a
#: statement that the gap is understood — not a way to silence the test.
#:
#: Keep this list adversarial: an entry here should name a *reason*, and if the
#: reason stops being true the entry must go rather than the number rise.
KNOWN_GAPS: dict[str, str] = {
    "multi-stop plan":
        "A race with neither a Full Course Yellow nor a Safety Car has no "
        "neutralised laps to measure a pace ratio from, so no race model can be "
        "built for it. Each such race is recorded in multistop_skipped.csv with "
        "its reason, and the test below checks that every gap is listed there.",
    "fuel-limited audit":
        "A race whose winner retired or was never classified has no winning "
        "stint sequence to reconstruct, so it cannot be audited.",
    "traffic cost":
        "Traffic is measured from a multi-class field. A round where only one "
        "class ran, or where the prime class has too few clear-air laps, has "
        "nothing to measure against.",
    "traffic stability":
        "Follows directly from traffic cost: a circuit with no measured season "
        "has no spread across seasons.",
}

#: How short a layer with a known gap is still allowed to be. A gap that grows
#: past this stops being an explained exception and becomes a coverage problem.
MIN_SHARE = 0.85


@pytest.fixture(scope="module")
def coverages():
    return measure()


def test_the_report_renders(coverages) -> None:
    """The table is quoted in reports/README.md, so it has to build."""
    text = report(coverages)
    assert "layer" in text and "covered" in text
    for coverage in coverages:
        assert coverage.layer.name in text


@pytest.mark.parametrize("layer", ENDURANCE_LAYERS, ids=lambda layer: layer.name)
def test_every_layer_covers_its_declared_scope(coverages, layer: Layer) -> None:
    """A layer covers the whole scope, or appears in KNOWN_GAPS with a reason."""
    coverage = next(c for c in coverages if c.layer.name == layer.name)

    if coverage.complete:
        return

    reason = KNOWN_GAPS.get(layer.name)
    assert reason, (
        f"'{layer.name}' covers {coverage.covered} of {coverage.expected} "
        f"({coverage.share:.0%}) at {layer.granularity} granularity, and no "
        f"reason is recorded for the gap.\n"
        f"Its stated rationale is: {layer.rationale}\n"
        f"Missing, first few: {coverage.missing[:5]}\n"
        "Either run the layer over the whole scope, or add an entry to "
        "KNOWN_GAPS saying why it cannot be run there."
    )
    assert coverage.share >= MIN_SHARE, (
        f"'{layer.name}' is down to {coverage.share:.0%} of its scope. The "
        f"recorded reason — {reason} — no longer accounts for a gap this "
        "large."
    )


def test_the_strategy_layer_covers_every_modelled_race(coverages) -> None:
    """Stated separately, because this is the one that was wrong.

    The multi-stop plan must be complete, with no KNOWN_GAPS escape hatch. Its
    output is the input to the cross-series pit-loss rule and to the
    fuel-limited-versus-tyre-limited headline, and a rule computed on an
    arbitrary third of the races is a rule about that third.
    """
    import pandas as pd

    from src.data.endurance_loader import slugify
    from src.data.endurance_scope import canonical_circuit
    from src.ingestion.config import ENDURANCE_DERIVED_DIR

    coverage = next(c for c in coverages if c.layer.name == "multi-stop plan")
    assert coverage.share >= 0.95, (
        f"the multi-stop plan covers {coverage.covered} of {coverage.expected} "
        f"modelled race-seasons ({coverage.share:.0%}). It used to cover 31%, "
        "one arbitrary season per circuit-class, and the headline strategy "
        "conclusions were computed on that sample.\n"
        f"Missing, first few: {coverage.missing[:5]}"
    )

    # Every gap must be an *explained* one. A race simply absent, with no
    # recorded reason, is the failure this module exists for: the 31% sample was
    # 144 absent races that nobody had ever listed.
    skipped = pd.read_csv(ENDURANCE_DERIVED_DIR / "multistop_skipped.csv")
    recorded = {
        (r.series, r.car_class, slugify(canonical_circuit(r.event)), r.year)
        for r in skipped.itertuples()
    }
    unexplained = [race for race in coverage.missing if race not in recorded]
    assert not unexplained, (
        f"{len(unexplained)} race-season(s) missing from the plan table with no "
        f"recorded reason: {unexplained[:5]}. Re-run scripts/run_multistop.py, "
        "which writes every skip and the reason for it."
    )


def test_race_level_layers_are_not_quietly_circuit_level(coverages) -> None:
    """A per-race layer must carry more rows than there are circuit-classes.

    The failure this catches is subtler than a missing artifact: a layer keyed
    per race that only ever *writes* one row per circuit looks complete on
    every column, and is a third of the evidence its consumers assume. The
    ratio is the tell.
    """
    per_race = [c for c in coverages if c.layer.granularity == "race-season"]
    circuit_level = next(
        c for c in coverages if c.layer.name == "overtaking difficulty"
    ).expected

    for coverage in per_race:
        assert coverage.expected > circuit_level, (
            f"'{coverage.layer.name}' is declared per race-season but expects "
            f"{coverage.expected} rows, no more than the {circuit_level} "
            "circuit-classes in scope — its granularity declaration and its "
            "data disagree."
        )
