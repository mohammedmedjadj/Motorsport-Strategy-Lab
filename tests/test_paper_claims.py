"""Every headline number, recomputed from its artifact and found in its text.

This project's most persistent defect is not a wrong model. It is that **prose
does not recompute.** The pattern has now happened often enough to be named:

- "every scoped endurance race is fuel-limited" stayed in a report for months
  after widening the scope made it false;
- a paragraph asserted a -6.330 within-stint R2 directly beneath a table that
  said -1.490, because the table was generated and the sentence was typed;
- the safety-car layer said "152 editions" after it loaded 153;
- "Bahrain is the strongest transfer in the project" survived the measurement
  that found four circuit-classes above it.

Each was found by hand, late, and only because someone happened to look. This
file is the mechanism that makes looking unnecessary: for each published claim
it **recomputes the value from the committed artifact** and asserts that the
formatted result actually appears in the document that publishes it.

That is deliberately stricter than recomputing alone. A test that only checks
`correlation == -0.982` passes happily while the README says -0.913. What has
to hold is that the number in the *text* matches the number in the *data*, so
each claim below carries the exact string a reader would see.

When one of these fails, the artifact is right and the prose is stale. Fix the
prose — or, if the finding genuinely changed, fix both and say so in the report.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
DERIVED = REPO / "data" / "derived"


# --------------------------------------------------------------------------
# Recomputations. Each returns the string exactly as it should appear in text.
# --------------------------------------------------------------------------

def _plans() -> pd.DataFrame:
    frame = pd.read_csv(DERIVED / "endurance" / "multistop_plans.csv")
    frame["tyre_limited"] = frame["optimal_stops"] != frame["min_stops"]
    return frame


def class_correlation() -> str:
    """R2: pit loss against tyre-limited share, across the six classes."""
    plans = _plans()
    by_class = plans.groupby(["series", "car_class"]).agg(
        pit_loss=("pit_loss_s", "median"), share=("tyre_limited", "mean")
    )
    return f"{by_class['pit_loss'].corr(by_class['share']):.3f}".replace("-", "−")


def tyre_limited_count() -> str:
    plans = _plans()
    return f"{int(plans['tyre_limited'].sum())} of {len(plans)}"


def cheap_stop_edge() -> str:
    """The largest pit loss at which any race is still tyre-limited."""
    plans = _plans()
    return f"{plans.loc[plans['tyre_limited'], 'pit_loss_s'].max():.1f} s"


def audit_total() -> str:
    """Every replayed first-stop decision, all four series."""
    f1 = pd.read_csv(DERIVED / "f1" / "systematic_audit.csv")
    endurance = pd.read_csv(DERIVED / "endurance" / "systematic_audit.csv")
    return f"{len(f1) + len(endurance):,}"


def f1_audit_decisions() -> str:
    return f"{len(pd.read_csv(DERIVED / 'f1' / 'systematic_audit.csv'))} decisions"


def best_transfer() -> str:
    """The strongest circuit-class transfer anywhere in the project."""
    loro = pd.read_csv(DERIVED / "endurance" / "endurance_degradation_loro.csv")
    mean = loro[loro["held_out_season"].astype(str) == "MEAN"]
    return f"+{mean['r2_within'].max():.3f}"


def safety_car_editions() -> list[str]:
    """Two documents word this differently; both must carry both numbers.

    Returned as alternatives rather than one string because "153 editions" and
    "153 race editions" are the same claim, and a guard that forces one house
    style would be edited away the first time it got in the way.
    """
    events = pd.read_csv(DERIVED / "f1" / "sc_events.csv")
    model = pd.read_csv(DERIVED / "f1" / "sc_model.csv")
    editions, count = int(model["n_editions"].sum()), len(events)
    return [f"{editions} editions, {count} events",
            f"{editions} race editions, {count} events"]


def neutralisation_races() -> str:
    """Races behind the F1 neutralisation calibration."""
    calibration = pd.read_csv(DERIVED / "prediction" / "neutralisation_calibration.csv")
    f1_rows = calibration[calibration["target"].str.startswith("F1")]
    counts = set(f1_rows["n_races"])
    assert len(counts) == 1, f"F1 calibration rows disagree on race count: {counts}"
    return str(counts.pop())



def _cross_source() -> pd.DataFrame:
    """Core FastF1 slopes beside the independent Kaggle breadth slopes."""
    from src.ingestion.config import breadth_key

    core = pd.read_csv(DERIVED / "f1" / "degradation_coefficients.csv")
    breadth = pd.read_csv(DERIVED / "f1" / "history_degradation.csv")
    core_slope = core.groupby("circuit")["deg_p1"].median()
    breadth_slope = (
        breadth[breadth["era"] == "ground-effect"]
        .groupby("circuit")["tyre_slope_s"].median()
    )
    rows = [
        {"core": float(slope), "breadth": float(breadth_slope[breadth_key(circuit)])}
        for circuit, slope in core_slope.items()
        if breadth_key(circuit) in breadth_slope.index
    ]
    frame = pd.DataFrame(rows).dropna()
    frame["difference"] = frame["breadth"] - frame["core"]
    return frame


def cross_source_agreement() -> str:
    """How well the two independent tyre-slope estimates agree."""
    frame = _cross_source()
    return f"r = {frame['core'].corr(frame['breadth']):+.2f}"


def cross_source_difference() -> str:
    """The paired difference — the statistic that showed there was no bias."""
    return f"{_cross_source()['difference'].median():+.4f} s/lap"


# --------------------------------------------------------------------------
# The claims. Each one names the document a reader would find it in.
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Claim:
    """A published number, where it is published, and how to re-derive it."""

    name: str
    #: Returns the value as it should read, or several acceptable renderings
    #: of the same value when documents legitimately word it differently.
    recompute: Callable[[], str | list[str]]
    documents: tuple[str, ...]
    note: str


CLAIMS = (
    Claim(
        "class-level correlation between pit loss and tyre-limited share",
        class_correlation,
        ("README.md",
         "reports/cross_series/synthesis.md",
         "reports/cross_series/when_tyres_beat_fuel.md"),
        "went from -0.913 to -0.982 when the scope tripled; both numbers were "
        "in the repository at once for a while",
    ),
    Claim(
        "tyre-limited race-seasons",
        tyre_limited_count,
        ("README.md",),
        "the count that refuted 'every endurance race is fuel-limited'",
    ),
    Claim(
        "cheap-stop edge",
        cheap_stop_edge,
        ("README.md",
         "reports/cross_series/synthesis.md",
         "reports/cross_series/when_tyres_beat_fuel.md"),
        "a single race sets this maximum — see the caveat in "
        "when_tyres_beat_fuel.md before quoting it as a constant",
    ),
    Claim(
        "total replayed decisions",
        audit_total,
        ("README.md",),
        "F1 plus all three endurance series, one criterion",
    ),
    Claim(
        "F1 replayed decisions",
        f1_audit_decisions,
        ("README.md",),
        "grew from a four-circuit sample to the whole calendar",
    ),
    Claim(
        "strongest transfer in the project",
        best_transfer,
        ("README.md",),
        "'Bahrain is the strongest transfer' was published and was false",
    ),
    Claim(
        "cross-source agreement on tyre slopes",
        cross_source_agreement,
        ("README.md", "reports/f1/systematic_audit.md"),
        "this citation read +0.74 for a day after the weather timezone fix "
        "moved the breadth layer and the report it cites said +0.855",
    ),
    Claim(
        "cross-source paired difference",
        cross_source_difference,
        ("README.md", "reports/f1/systematic_audit.md"),
        "the paired statistic, not the difference of medians — comparing the "
        "two medians nearly published a durability bias that does not exist",
    ),
    Claim(
        "safety-car editions and events",
        safety_car_editions,
        ("README.md", "reports/f1/README.md"),
        "moved 152 -> 153 when a transient fetch failure cleared",
    ),
)


@pytest.mark.parametrize("claim", CLAIMS, ids=lambda c: c.name)
def test_published_number_matches_its_artifact(claim: Claim) -> None:
    """The number in the text is the number the data produces."""
    computed = claim.recompute()
    accepted = [computed] if isinstance(computed, str) else computed
    missing = []
    for document in claim.documents:
        path = REPO / document
        if not path.exists():
            missing.append(f"{document} (file not found)")
            continue
        text = path.read_text(encoding="utf-8")
        if not any(value in text for value in accepted):
            missing.append(document)

    assert not missing, (
        f"{claim.name}: the artifacts now give {accepted!r}, none of which "
        f"appears in {missing}. The data is authoritative — update the prose. "
        f"Context: {claim.note}."
    )


def test_f1_calibration_agrees_with_the_safety_car_layer() -> None:
    """The calibration must be rebuilt whenever the safety-car layer widens.

    These are two artifacts holding the same count, produced by two scripts.
    They disagreed for a full day after the safety-car scope widened, and the
    generalisation audit published the stale one.
    """
    model = pd.read_csv(DERIVED / "f1" / "sc_model.csv")
    editions = int(model["n_editions"].sum())
    calibrated = int(neutralisation_races())
    assert calibrated == editions, (
        f"sc_model.csv covers {editions} editions but the neutralisation "
        f"calibration was fitted on {calibrated}. Re-run "
        "`python scripts/run_prediction_backtest.py`, then "
        "`python scripts/run_generalization_audit.py`, which republishes it."
    )


def test_every_class_is_named_in_the_transfer_table() -> None:
    """A transfer score without its class is unreadable, and was published.

    The generalisation audit keyed its degradation table on (series, circuit),
    so IMSA printed three indistinguishable "Daytona" rows carrying GTP, GTD
    and GTD PRO. Separating the classes is a standing rule in this project, not
    a formatting preference: the same circuit is a different problem for a GT3
    car and a prototype, and the result the table exists to show is exactly
    that difference.
    """
    report = REPO / "reports" / "cross_series" / "generalization_audit.md"
    if not report.exists():
        pytest.skip("generalisation audit not generated")
    text = report.read_text(encoding="utf-8")
    loro = pd.read_csv(DERIVED / "endurance" / "endurance_degradation_loro.csv")
    classes = sorted(loro["car_class"].dropna().unique())
    absent = [name for name in classes if name not in text]
    assert not absent, (
        f"classes missing from the generalisation audit: {absent}. Every "
        "endurance transfer score belongs to one class and is meaningless "
        "without it."
    )
