"""The 2026 regulation era is held out of the fitted coefficients. Prove it.

F1's 2026 rules change the power unit, the aerodynamics, the car mass and the
tyres. Pooling a 2026 race into a pre-2026 fit produces coefficients that
describe neither era — measured, not assumed: it halves Suzuka's HARD tyre-age
slope (+0.131 to +0.066 s/lap) and flips the cross-validated degree selection.
So `PRE_ERA_SEASONS` bounds every fit whose coefficients describe car or tyre
behaviour, and `ERA_SEASONS` is evaluated only as a held-out transfer test.

Two failure modes, and this file watches both.

**Leakage.** A 2026 lap entering a fitted coefficient invalidates that
coefficient and everything downstream of it — the simulator, the audit, the
slope-bias check. Most artifacts here record no season at all, so leakage cannot
be detected by reading them; it has to be bounded another way. A fit cannot use
laps it did not count, so if a circuit's reported `n_laps` is within what the
pre-era window can supply, no 2026 lap reached it. That is a one-sided bound
rather than a proof of provenance, and it is cheap enough to run on every
commit — the alternative is refitting 25 circuits to compare.

**A holdout that is never evaluated.** Holding data out and never testing on it
is not caution, it is discarded data plus an unsupported claim. `run_degradation
.py` must actually train on the pre-era window and score each new-era race.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest

from src.ingestion.config import (
    ERA_SEASONS,
    F1_DERIVED_DIR,
    PRE_ERA_SEASONS,
    REGULATION_ERA_START,
)

REPO = Path(__file__).resolve().parents[1]
COEFFICIENTS = F1_DERIVED_DIR / "degradation_coefficients.csv"
REPORT = REPO / "reports" / "f1" / "degradation_phase2.md"


def _laps_available(circuit: str, seasons: tuple[int, ...]) -> int:
    """Committed laps for a circuit across the given seasons, before filtering."""
    total = 0
    for season in seasons:
        path = F1_DERIVED_DIR / f"laps_{season}_{circuit}.csv"
        if path.exists():
            total += len(pd.read_csv(path, usecols=[0]))
    return total


def _fitted() -> pd.DataFrame:
    if not COEFFICIENTS.exists():
        pytest.skip("degradation coefficients not generated")
    return pd.read_csv(COEFFICIENTS)


def test_the_era_boundary_is_where_the_project_says_it_is() -> None:
    """A silent move of the boundary would invalidate every guard below."""
    assert REGULATION_ERA_START == 2026
    assert ERA_SEASONS, "the new era holds no seasons — nothing is being held out"
    assert PRE_ERA_SEASONS, "the fitting window is empty"
    assert max(PRE_ERA_SEASONS) < min(ERA_SEASONS), (
        f"the windows overlap: pre-era {PRE_ERA_SEASONS}, era {ERA_SEASONS}"
    )


def test_no_fit_uses_more_laps_than_the_pre_era_window_supplies() -> None:
    """The leakage bound, on every fitted circuit.

    Reported `n_laps` counts laps after the modelling frame drops in/out laps
    and outliers, so it is always below the raw supply. What matters is that it
    never *exceeds* what the pre-era seasons hold — that could only happen if
    new-era laps had been pooled in.
    """
    fitted = _fitted()
    offenders = []
    for circuit, group in fitted.groupby("circuit"):
        used = int(group["n_laps"].iloc[0])
        available = _laps_available(str(circuit), PRE_ERA_SEASONS)
        if used > available:
            offenders.append(
                f"{circuit}: fit used {used} laps, pre-era seasons "
                f"{PRE_ERA_SEASONS} hold only {available}"
            )
    assert not offenders, (
        "these fits use more laps than the pre-era window can supply, which "
        f"means new-era data was pooled in: {offenders}. Every coefficient for "
        "those circuits is describing two regulation eras at once, and so is "
        "the simulator, the decision audit and the slope-bias check."
    )


def test_the_bound_is_meaningful_where_it_matters() -> None:
    """A guard that only covers circuits with no 2026 data proves nothing.

    If the ingestion has not reached the new era yet, the test above passes
    trivially everywhere. This records how much of it is doing real work, and
    fails only if the era exists in the data and no fitted circuit overlaps it
    — which would mean the guard has silently stopped applying.
    """
    fitted = _fitted()
    circuits = sorted(str(c) for c in fitted["circuit"].unique())
    with_era = [c for c in circuits if _laps_available(c, ERA_SEASONS) > 0]
    era_ingested = any(
        _laps_available(c, ERA_SEASONS) > 0 for c in circuits
    )
    if not era_ingested:
        pytest.skip(
            f"no {REGULATION_ERA_START} laps ingested yet — the leakage bound "
            "is vacuous until a new-era race exists"
        )
    assert with_era, (
        "new-era laps exist but no fitted circuit overlaps them, so the "
        "leakage bound checks nothing. Either the fits lost those circuits or "
        "the file naming changed."
    )


def test_the_holdout_is_actually_evaluated() -> None:
    """Held-out data must be tested on, or it is discarded data and a claim."""
    if not REPORT.exists():
        pytest.skip("degradation report not generated")
    text = REPORT.read_text(encoding="utf-8")
    heading = f"Does a pre-{REGULATION_ERA_START} fit predict the {REGULATION_ERA_START} era?"
    assert heading in text, (
        f"the report has no new-era holdout section. {ERA_SEASONS} is being "
        "excluded from every fit and then never scored, which is not a "
        "holdout — it is ingested data thrown away, plus an unsupported claim "
        "in src/ingestion/config.py that it is 'used as a held-out transfer "
        "test'."
    )
    section = text.split(heading, 1)[1].split("\n## ", 1)[0]
    scored = [
        line for line in section.splitlines()
        if line.startswith("|") and any(str(s) in line for s in ERA_SEASONS)
    ]
    assert scored, f"the holdout section scores no {REGULATION_ERA_START} race"


def test_the_holdout_caveat_counts_what_the_table_shows() -> None:
    """The limitation paragraph must describe the table above it.

    It said "two races at two circuits" under a table of twelve for as long as
    it took someone to read both. Deriving the sentence fixed that; this keeps
    it fixed, because the next scope widening will be just as quiet.
    """
    if not REPORT.exists():
        pytest.skip("degradation report not generated")
    text = REPORT.read_text(encoding="utf-8")
    heading = f"Does a pre-{REGULATION_ERA_START} fit predict the {REGULATION_ERA_START} era?"
    if heading not in text:
        pytest.skip("holdout section absent — covered by the test above")
    section = text.split(heading, 1)[1].split("\n## ", 1)[0]

    rows = [
        line for line in section.splitlines()
        if line.startswith("| ") and any(str(s) in line for s in ERA_SEASONS)
    ]
    circuits = {line.split("|")[1].strip() for line in rows}

    claim = re.search(
        r"this is (\d+) races? at (\d+) circuits?", section
    )
    assert claim, (
        "the holdout section states no limitation on how much was tested. A "
        "table of new-era scores without one invites a conclusion the sample "
        "cannot support."
    )
    stated_races, stated_circuits = int(claim.group(1)), int(claim.group(2))
    assert (stated_races, stated_circuits) == (len(rows), len(circuits)), (
        f"the caveat says {stated_races} races at {stated_circuits} circuits; "
        f"the table above it lists {len(rows)} races at {len(circuits)}. The "
        "table regenerates and the sentence has to as well."
    )
