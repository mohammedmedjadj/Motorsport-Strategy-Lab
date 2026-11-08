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
    moved = frame[frame["allocation_changed"] & frame["verdict"].notna()]
    changed = moved[moved["sane"].fillna(False).astype(bool)]
    assert s["n_circuits"] == len(frame)
    assert s["n_moved"] == len(moved)
    assert s["n_changed"] == len(changed)
    # The degenerate fits are excluded exactly as Result 1 excludes them.
    assert (moved.loc[~moved["sane"].fillna(False).astype(bool), "verdict"] == "degenerate fit, excluded").all()
    unstable = changed[changed["verdict"] == "slope unstable"]
    assert s["unstable"]["n"] == len(unstable)
    assert s["unstable"]["min_difference"] == pytest.approx(unstable["difference"].min(), abs=1e-6)
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


def test_one_stop_retest_matches_the_committed_one_stop_set():
    committed = pd.read_csv(F1 / "committed_strategy.csv")
    one = committed[(committed["n_stops"] == 1) & committed["committed_delta_laps"].notna()]
    s = _summary("one_stop_retest")
    assert s["n_one_stop"] == len(one)
    assert all(r["n"] == len(one) for r in s["rules"].values())
    assert s["salminen"]["closer"] + s["salminen"]["further"] <= s["salminen"]["predicted"]


def test_design_checks_reproduce_the_published_committed_replay():
    checks = pd.read_csv(F1 / "audit_design_checks.csv")
    published = pd.read_csv(F1 / "committed_strategy.csv").dropna(subset=["committed_pit_lap"])
    base = checks[(checks["lookback"] == 5) & checks["top"]]
    merged = base.merge(published, on=["season", "circuit", "driver", "real_pit_lap"])
    # Same planner, same seed, same horizon: the same lap wherever both exist.
    assert len(merged) >= 0.9 * len(published)
    assert (merged["planner_pit_lap"] == merged["committed_pit_lap"]).mean() > 0.99


def test_design_check_bound_is_the_earliest_allowed_lap():
    checks = pd.read_csv(F1 / "audit_design_checks.csv")
    assert (checks["planner_pit_lap"] > checks["decision_lap"]).all()
    assert (checks["at_bound"] == (checks["planner_pit_lap"] == checks["decision_lap"] + 1)).all()


def test_every_reported_f1_coefficient_is_estimable():
    s = _summary("estimability")
    assert s["f1_non_estimable"] == 0
    assert s["f1_coefficients_checked"] > 0


def test_regime_index_shares_sum_to_one():
    s = json.loads((REPO / "data" / "derived" / "cross_series" / "regime_index_summary.json").read_text())
    assert sum(s["shares"].values()) == pytest.approx(1.0, abs=1e-4)


def test_ceiling_uses_only_the_pre_rule_change_seasons():
    ceiling = pd.read_csv(F1 / "transfer_ceiling.csv")
    assert (ceiling["seasons"] <= 4).all()
    sane = ceiling[ceiling["sane"].astype(bool)]
    # Per-season residuals carry no slope movement, so they never lower the ceiling much.
    assert (sane["ceiling_mean"] - sane["ceiling_pooled_resid"]).min() > -0.05


def test_endurance_ceiling_summary_recomputes():
    frame = pd.read_csv(REPO / "data" / "derived" / "endurance" / "endurance_ceiling.csv")
    s = json.loads((REPO / "data" / "derived" / "endurance" / "endurance_ceiling_summary.json").read_text())
    sane = frame[frame["verdict"] != "degenerate fit, excluded"]
    assert s["n"] == len(sane)
    assert s["n_ceiling_below_threshold"] == int((sane["ceiling_mean"] < 0.2).sum())
    assert sum(s["verdicts"].values()) == len(sane)


def test_estimation_checks_are_internally_consistent():
    s = _summary("estimation_checks")
    rc = s["race_clustering"]
    assert rc["zero_driver_race"] <= rc["zero_race"] <= rc["n_slopes"]
    rf = s["refuelling"]
    assert abs(rf["tyre_limited_marginal"] - rf["tyre_limited_published"]) <= rf["n_changed"]
