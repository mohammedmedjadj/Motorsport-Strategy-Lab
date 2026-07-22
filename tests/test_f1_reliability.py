"""F1 reliability layer: finish classification, the permanent-vs-street positive
control, and the committed artifact (permanent beats street; the early hybrid era
is the most fragile — both on the real 2011-2024 data)."""

from __future__ import annotations

import pandas as pd
import pytest

from src.ingestion.config import F1_DERIVED_DIR
from src.reliability.f1_reliability import (
    _classified,
    reliability_improves_off_the_street,
)

_ARTIFACT = F1_DERIVED_DIR / "reliability.csv"


def test_classified_counts_flag_and_lapped_as_finishers() -> None:
    s = pd.Series(["Finished", "+1 Lap", "+3 Laps", "Engine", "Collision",
                   "Gearbox", "Disqualified"])
    assert list(_classified(s)) == [True, True, True, False, False, False, False]


def test_street_positive_control_on_a_fixture() -> None:
    df = pd.DataFrame({
        "classified": [True] * 9 + [False] + [True] * 6 + [False] * 4,
        "street": [False] * 10 + [True] * 10,   # permanent 9/10, street 6/10
    })
    assert reliability_improves_off_the_street(df) is True


def test_control_false_without_both_kinds() -> None:
    only_perm = pd.DataFrame({"classified": [True, False], "street": [False, False]})
    assert reliability_improves_off_the_street(only_perm) is False


@pytest.mark.skipif(not _ARTIFACT.exists(), reason="F1 reliability artifact not generated")
def test_committed_artifact_early_hybrid_is_most_fragile() -> None:
    art = pd.read_csv(_ARTIFACT)
    era = art[art["dimension"] == "era"].set_index("group")["finish_rate"]
    # The 2014 power-unit intro is the least reliable era; ground-effect the most.
    assert era["hybrid-v6"] == era.min()
    assert era["ground-effect"] == era.max()
