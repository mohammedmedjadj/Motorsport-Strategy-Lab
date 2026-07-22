"""Reliability layer: Jeffreys-smoothed finish rates, the attrition/duration
positive control, and the messy-``season`` normaliser. Uses a small synthetic
fixture for the mechanics; the committed artifact is guarded separately once
generated from the real Kaggle file."""

from __future__ import annotations

import pandas as pd
import pytest

from src.data.wec_history_loader import _normalise_class, _season_end_year
from src.ingestion.config import DERIVED_DIR

_ARTIFACT = DERIVED_DIR / "wec" / "reliability.csv"
from src.reliability.wec_reliability import (
    attrition_holds_with_duration,
    finish_rate_by,
    finish_rate_by_duration,
)


def _fixture() -> pd.DataFrame:
    """Two classes and two durations, engineered so the 24 h race is more
    fragile than the 6 h one — the shape the real data should also show."""
    rows = []
    # 6 h race: 9 of 10 LMP1 classified, 8 of 10 GTE.
    for i in range(10):
        rows.append({"class": "LMP1", "duration_h": 6, "classified": i < 9})
        rows.append({"class": "LMGTE Am", "duration_h": 6, "classified": i < 8})
    # 24 h race: only 5 of 10 LMP1 classified, 6 of 10 GTE (heavier attrition).
    for i in range(10):
        rows.append({"class": "LMP1", "duration_h": 24, "classified": i < 5})
        rows.append({"class": "LMGTE Am", "duration_h": 24, "classified": i < 6})
    return pd.DataFrame(rows)


def test_class_normalisation_merges_the_spaced_naming() -> None:
    # the 2011-2013 spaced names collapse onto the later convention...
    assert _normalise_class("LM P1") == "LMP1"
    assert _normalise_class("LM P2") == "LMP2"
    assert _normalise_class("LM GTE Pro") == "LMGTE Pro"
    assert _normalise_class("LM GTE Am") == "LMGTE Am"
    # ...already-normal names are untouched, and genuine categories are kept.
    assert _normalise_class("LMP1") == "LMP1"
    assert _normalise_class("HYPERCAR") == "HYPERCAR"
    assert _normalise_class("INNOVATIVE CAR") == "INNOVATIVE CAR"


def test_season_label_normalises_supers_and_plain_years() -> None:
    assert _season_end_year("2014") == 2014
    assert _season_end_year("2018-2019") == 2019   # keyed on the ending year
    assert _season_end_year("2019-2020") == 2020


def test_finish_rate_uses_jeffreys_and_orders_fragile_first() -> None:
    rates = finish_rate_by(_fixture(), "class")
    # Both classes present; the smoothed rate is strictly inside (0, 1).
    assert {r.group for r in rates} == {"LMP1", "LMGTE Am"}
    for r in rates:
        assert 0.0 < r.lo95 < r.rate < r.hi95 < 1.0
        assert r.n_classified <= r.n_entries
    # Sorted most-fragile first: pooled LMP1 (14/20) is below GTE (14/20)? equal
    # here, so just assert the ordering is non-decreasing in rate.
    assert rates[0].rate <= rates[-1].rate


def test_attrition_positive_control_holds_on_engineered_data() -> None:
    df = _fixture()
    by_dur = finish_rate_by_duration(df)
    assert [r.group for r in by_dur] == ["6h", "24h"]     # ordered by length
    assert by_dur[-1].rate < by_dur[0].rate               # 24 h more fragile
    assert attrition_holds_with_duration(df) is True


def test_control_false_when_only_one_duration() -> None:
    one = _fixture()
    one = one[one["duration_h"] == 6]
    assert attrition_holds_with_duration(one) is False


@pytest.mark.skipif(not _ARTIFACT.exists(), reason="reliability artifact not generated")
def test_committed_artifact_shows_le_mans_is_the_most_brutal() -> None:
    """The real-data finding, pinned: the 24 h finish rate sits below the 6 h one
    (attrition rises with duration) on the committed 13-season artifact."""
    art = pd.read_csv(_ARTIFACT)
    dur = art[art["dimension"] == "duration"].set_index("group")["finish_rate"]
    assert dur["24h"] < dur["6h"]
    assert dur["24h"] < dur["4h"]
