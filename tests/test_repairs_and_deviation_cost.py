"""The compound table, the Friday long runs and the deviation cost hold together.

Three layers feed Section "Two repairs a team would try first" and "What the
remaining gap costs". Each test here checks a property the paper relies on
without rerunning the layer: the compound table is a valid nomination for every
race the model is fitted on, each summary recomputes from its own rows, and the
deviation-cost windows are what the script says they are.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
F1 = REPO / "data" / "derived" / "f1"
ALLOCATION = REPO / "data" / "reference" / "pirelli_compounds.csv"


@pytest.fixture(scope="module")
def allocation() -> pd.DataFrame:
    return pd.read_csv(ALLOCATION)


def _summary(name: str) -> dict:
    return json.loads((F1 / f"{name}_summary.json").read_text(encoding="utf-8"))


def test_every_fitted_race_has_a_nomination(allocation):
    raced = {
        p.stem[len("laps_"):] for p in F1.glob("laps_*.csv") if 2022 <= int(p.stem[5:9]) <= 2025
    }
    nominated = set(allocation["season"].astype(str) + "_" + allocation["circuit"])
    assert raced <= nominated, sorted(raced - nominated)


def test_nominations_are_three_distinct_compounds_hard_to_soft(allocation):
    for r in allocation.itertuples():
        numbers = [int(c[1]) for c in (r.hard, r.medium, r.soft)]
        assert numbers == sorted(set(numbers)), (r.season, r.circuit)
        assert all(0 <= n <= 6 for n in numbers)


def test_c6_only_exists_from_2025(allocation):
    early = allocation[allocation["season"] < 2025]
    assert not (early[["hard", "medium", "soft"]] == "C6").any().any()


def test_compound_identity_summary_recomputes():
    frame = pd.read_csv(F1 / "compound_identity.csv")
    s = _summary("compound_identity")
    changed = frame[frame["allocation_changed"]]
    assert s["n_circuits"] == len(frame)
    assert s["n_changed"] == len(changed)
    assert s["changed"]["median_difference"] == pytest.approx(
        np.median(changed["difference"]), abs=1e-6
    )
    assert s["changed"]["n_better"] == int((changed["difference"] > 0).sum())
    assert s["changed"]["n_worse"] == int((changed["difference"] < 0).sum())


def test_codings_coincide_where_the_allocation_never_changed():
    frame = pd.read_csv(F1 / "compound_identity.csv")
    same = frame[~frame["allocation_changed"]]
    assert np.allclose(same["r2_relative"], same["r2_real"])


def test_practice_summary_recomputes():
    frame = pd.read_csv(F1 / "practice_long_runs.csv")
    s = _summary("practice_long_runs")
    assert s["n_races"] == len(frame)
    for col in ("r2_other_seasons", "r2_friday", "r2_friday_corrected", "r2_both"):
        assert s[col] == pytest.approx(frame[col].median(), abs=1e-6)
    diff = frame["r2_friday"] - frame["r2_other_seasons"]
    assert s["friday_minus_other"]["n_worse"] == int((diff < 0).sum())


def test_practice_laps_cover_only_the_practice_window():
    laps = pd.read_csv(F1 / "practice_laps.csv")
    assert set(laps["season"]) <= {2023, 2024, 2025}
    assert set(laps["session"]) <= {"Practice 1", "Practice 2"}


def test_deviation_windows_are_consistent():
    frame = pd.read_csv(F1 / "deviation_cost.csv")
    assert (frame["window_laps"] > 0).all()
    assert np.allclose(
        frame["excess_s"], frame["elapsed_s"] - frame["window_laps"] * frame["pace_s"]
    )
    assert (frame["deviation_laps"] == frame["real_pit_lap"] - frame["planner_pit_lap"]).all()
    s = _summary("deviation_cost")
    assert s["n_cars"] == len(frame)
    assert s["n_races"] == frame["race"].nunique()
