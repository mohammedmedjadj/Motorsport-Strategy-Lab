"""Proper-scoring-rule correctness, the leave-one-race-out backtest, and the
drift guard + scientific finding on the committed calibration artifact."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.ingestion.config import (
    ENDURANCE_DERIVED_DIR,
    F1_DERIVED_DIR,
    PREDICTION_DERIVED_DIR,
)
from src.prediction.backtest import (
    endurance_race_table,
    f1_race_table,
    leave_one_race_out,
    outcomes_by,
    score_backtest,
)
from src.prediction.scoring import (
    brier_score,
    brier_skill_score,
    log_loss,
    reliability_curve,
)

# --- scoring rules: exact values on hand-computable inputs ------------------


def test_brier_score_is_mean_squared_error() -> None:
    # (0.2-0)^2 + (0.9-1)^2 + (0.5-0)^2 = 0.04 + 0.01 + 0.25, /3
    assert brier_score([0.2, 0.9, 0.5], [0, 1, 0]) == pytest.approx(0.30 / 3)


def test_perfect_and_worst_predictions() -> None:
    assert brier_score([1.0, 0.0], [1, 0]) == 0.0
    assert brier_score([0.0, 1.0], [1, 0]) == 1.0


def test_log_loss_matches_closed_form() -> None:
    # single correct-ish call: -log(0.8)
    assert log_loss([0.8], [1]) == pytest.approx(-np.log(0.8))


def test_log_loss_is_finite_at_the_boundary() -> None:
    # a confident miss is heavily but finitely penalised (clipped, not inf)
    assert np.isfinite(log_loss([0.0], [1]))


def test_skill_is_zero_for_the_climatology_predictor() -> None:
    # predicting the base rate everywhere must score exactly zero skill
    y = np.array([1, 1, 0, 1, 0, 0, 1, 0], dtype=float)
    assert brier_skill_score(np.full_like(y, y.mean()), y) == pytest.approx(0.0)


def test_skill_is_positive_for_a_better_than_base_predictor() -> None:
    y = np.array([1, 1, 0, 0], dtype=float)
    good = np.array([0.9, 0.9, 0.1, 0.1])   # tracks the outcomes
    assert brier_skill_score(good, y) > 0.5


def test_reliability_curve_bins_and_aggregates() -> None:
    p = np.array([0.1, 0.15, 0.85, 0.9])
    y = np.array([0, 0, 1, 1])
    bins = reliability_curve(p, y, n_bins=5)
    assert len(bins) == 2                       # only the first and last bins fill
    assert bins[0].observed == 0.0 and bins[0].count == 2
    assert bins[1].observed == 1.0 and bins[1].count == 2


@pytest.mark.parametrize("bad", [[-0.1, 0.5], [0.5, 1.2]])
def test_rejects_out_of_range_probabilities(bad) -> None:
    with pytest.raises(ValueError):
        brier_score(bad, [0, 1])


def test_rejects_non_binary_outcomes() -> None:
    with pytest.raises(ValueError):
        brier_score([0.5, 0.5], [0, 2])


# --- leave-one-race-out mechanics -------------------------------------------


def test_loo_predicts_a_race_from_the_others_only() -> None:
    # one circuit, outcomes [1,1,0]. Held-out race 0 (a 1) sees others k=1,n=2
    # -> (1+0.5)/(2+1)=0.5. Held-out race 2 (a 0) sees others k=2,n=2
    # -> (2+0.5)/(2+1)=0.8333.
    preds, obs = leave_one_race_out({"c": np.array([1.0, 1.0, 0.0])})
    assert preds[0] == pytest.approx(0.5)
    assert preds[2] == pytest.approx(2.5 / 3)
    assert list(obs) == [1.0, 1.0, 0.0]


def test_loo_single_edition_falls_back_to_uninformative_half() -> None:
    preds, _ = leave_one_race_out({"c": np.array([1.0])})
    assert preds[0] == pytest.approx(0.5)   # (0+0.5)/(0+1)


# --- adapters ---------------------------------------------------------------


def test_f1_race_table_expands_counts_to_one_row_per_edition() -> None:
    scm = pd.DataFrame([{"circuit": "x", "n_editions": 5,
                         "sc_races_with_event": 2, "vsc_races_with_event": 1}])
    tab = f1_race_table(scm)
    assert len(tab) == 5
    assert tab["sc"].sum() == 2 and tab["vsc"].sum() == 1


def test_endurance_race_table_is_one_row_per_race_with_binary_flags() -> None:
    laps = pd.DataFrame({
        "series_code": ["wec"] * 4,
        "event": ["Spa"] * 4,
        "year": [2024] * 4,
        "session_id": [1] * 4,
        "lap": [1, 2, 3, 4],
        "flags": ["GF", "FCY", "SF", "GF"],
    })
    tab = endurance_race_table(laps)
    assert len(tab) == 1
    assert tab.iloc[0]["fcy"] == 1.0 and tab.iloc[0]["sc"] == 1.0


# --- committed artifact: drift guard + the scientific finding ---------------


@pytest.mark.skipif(not (PREDICTION_DERIVED_DIR / "neutralisation_calibration.csv").exists(),
                    reason="calibration artifact not generated")
def test_committed_calibration_matches_a_fresh_backtest() -> None:
    art = pd.read_csv(PREDICTION_DERIVED_DIR / "neutralisation_calibration.csv")
    flags = pd.read_csv(ENDURANCE_DERIVED_DIR / "race_flags.csv")
    wec = endurance_race_table(flags).query("series == 'wec'")
    fresh = score_backtest("WEC FCY", outcomes_by(wec, "fcy", "circuit"))
    row = art.loc[art["target"] == "WEC FCY"].iloc[0]
    assert row["skill"] == pytest.approx(fresh.skill, abs=1e-3)
    assert row["brier"] == pytest.approx(fresh.brier, abs=1e-3)


@pytest.mark.skipif(not (PREDICTION_DERIVED_DIR / "neutralisation_calibration.csv").exists(),
                    reason="calibration artifact not generated")
def test_series_has_skill_but_circuit_does_not() -> None:
    """The headline honest finding, pinned: grouping by series (a real effect)
    beats the base rate; grouping by circuit (noise at these sample sizes) does
    not. If a future data refresh changes this, the test must be revisited
    deliberately, not silently."""
    art = pd.read_csv(PREDICTION_DERIVED_DIR / "neutralisation_calibration.csv")
    by_series = art.loc[art["level"] == "series", "skill"]
    by_circuit = art.loc[art["level"] == "circuit", "skill"]
    assert (by_series > 0).all()          # positive control fires
    assert (by_circuit <= 0.05).all()     # no circuit clears a trivial margin
