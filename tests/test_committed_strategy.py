"""The committed-strategy replay changes only what it says it changes.

The replay re-runs multi-stop decisions with the horizon at the team's second
stop. Its one-stop rows must be the published audit untouched, its deltas must
be its own laps minus the real stop, and every median the paper quotes from it
must be recomputable from its rows.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
F1 = REPO / "data" / "derived" / "f1"
END = REPO / "data" / "derived" / "endurance"


@pytest.fixture(scope="module")
def f1() -> pd.DataFrame:
    return pd.read_csv(F1 / "committed_strategy.csv")


def test_one_stop_rows_are_the_published_audit(f1):
    one = f1[f1["n_stops"] == 1]
    assert len(one) > 0
    assert (one["committed_pit_lap"] == one["model_pit_lap"]).all()
    assert one["second_pit_lap"].isna().all()


def test_rows_match_the_published_audit(f1):
    audit = pd.read_csv(F1 / "systematic_audit.csv")
    assert len(f1) == len(audit)
    assert (f1["model_pit_lap"].to_numpy() == audit["model_pit_lap"].to_numpy()).all()
    assert (f1["delta_laps"].to_numpy() == audit["delta_laps"].to_numpy()).all()


@pytest.mark.parametrize("path", [F1 / "committed_strategy.csv", END / "committed_strategy.csv"])
def test_committed_delta_is_committed_lap_minus_real(path):
    frame = pd.read_csv(path).dropna(subset=["committed_pit_lap"])
    assert (frame["committed_delta_laps"]
            == frame["committed_pit_lap"] - frame["real_pit_lap"]).all()


@pytest.mark.parametrize("path", [F1 / "committed_strategy.csv", END / "committed_strategy.csv"])
def test_second_stop_comes_after_the_first(path):
    frame = pd.read_csv(path).dropna(subset=["second_pit_lap"])
    assert (frame["second_pit_lap"] > frame["real_pit_lap"]).all()


def test_f1_summary_recomputes_from_rows(f1):
    summary = pd.read_csv(F1 / "committed_strategy_summary.csv").set_index("group")
    replayed = f1.dropna(subset=["committed_delta_laps"])
    for group, part in {
        "all decisions": replayed,
        "one stop": replayed[replayed["n_stops"] == 1],
        "two or more": replayed[replayed["n_stops"] >= 2],
    }.items():
        row = summary.loc[group]
        assert row["n_decisions"] == len(part)
        assert row["median_delta"] == pytest.approx(np.median(part["delta_laps"]))
        assert row["committed_median_delta"] == pytest.approx(
            np.median(part["committed_delta_laps"])
        )


def test_endurance_summary_recomputes_from_rows():
    rows = pd.read_csv(END / "committed_strategy.csv").dropna(subset=["committed_delta_laps"])
    summary = pd.read_csv(END / "committed_strategy_summary.csv")
    for r in summary.itertuples():
        part = rows[(rows["series"] == r.series) & (rows["car_class"] == r.car_class)]
        assert r.n_decisions == len(part)
        assert r.committed_median_delta == pytest.approx(
            np.median(part["committed_delta_laps"])
        )
