"""GP degradation curve: recovers a linear truth as well as OLS, honours the
unseen-compound NaN contract, and skips compounds with too few distinct ages."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.degradation.dataset import build_modelling_frame, load_circuit_laps
from src.degradation.gp_model import fit_circuit_gp, predict_shape_gp
from src.degradation.model import fit_circuit, predict_shape
from src.ingestion.config import F1_REPORTS_DIR
from tests.test_degradation import make_synthetic


def _within_stint_rmse(frame: pd.DataFrame, pred: pd.Series) -> float:
    def demean(v: pd.Series, s: pd.Series) -> pd.Series:
        return v - v.groupby(s).transform("mean")

    valid = pred.notna()
    actual = demean(frame.loc[valid, "lap_time_s"], frame.loc[valid, "stint_id"])
    predicted = demean(pred[valid], frame.loc[valid, "stint_id"])
    err = actual - predicted
    return float(np.sqrt((err**2).mean()))


def test_gp_matches_ols_on_a_linear_truth() -> None:
    """When degradation is truly linear the GP must not do worse than OLS on the
    within-stint shape — both should sit near the synthetic noise floor."""
    frame, _ = build_modelling_frame(make_synthetic(noise_s=0.05), "synth")
    gp = fit_circuit_gp(frame, "synth")
    ols = fit_circuit(frame, "synth", degree=1)
    rmse_gp = _within_stint_rmse(frame, predict_shape_gp(gp, frame))
    rmse_ols = _within_stint_rmse(frame, predict_shape(ols, frame))
    assert rmse_gp < 0.10  # at the 0.05 noise floor
    assert rmse_gp <= rmse_ols + 0.01  # no meaningful regression vs OLS


def test_gp_predict_nan_for_unseen_compound() -> None:
    frame, _ = build_modelling_frame(make_synthetic(), "synth")
    gp = fit_circuit_gp(frame, "synth")
    probe = frame.head(3).copy()
    probe.loc[probe.index[0], "Compound"] = "UNSEEN"
    shape = predict_shape_gp(gp, probe)
    assert shape.isna().tolist() == [True, False, False]


def test_gp_skips_compounds_with_too_few_ages() -> None:
    frame, _ = build_modelling_frame(make_synthetic(), "synth")
    # Collapse every HARD lap onto two tyre ages -> < 3 distinct ages -> skipped.
    frame = frame.copy()
    hard = frame["Compound"] == "HARD"
    frame.loc[hard, "TyreLife"] = np.where(
        frame.loc[hard, "TyreLife"] % 2 == 0, 1.0, 2.0
    )
    gp = fit_circuit_gp(frame, "synth")
    assert "HARD" not in gp.curves
    assert "SOFT" in gp.curves  # unaffected compounds still fit


# --- committed report: drift guard for a section no script regenerates ------
#
# reports/f1/degradation_phase2.md carries a "GP robustness check" section
# (OLS vs GP on leave-one-race-out) that was written once by hand -- no
# script in scripts/ produces that text, unlike every other number in this
# project's reports. run_degradation.py (the post-race-refresh workflow's
# actual degradation step) overwrites the whole file and does NOT know this
# section exists, so it silently disappears the next time that script runs
# for real (confirmed locally: it did, before this test existed). This test
# doesn't fix the reproducibility gap -- it turns "silently deleted" into
# "a failing test," and separately checks the section's own numeric claim is
# still true, not just present.

_CIRCUITS = ("monaco", "singapore", "barcelona", "suzuka")


def _gp_vs_ols_loro(circuit: str) -> tuple[float, float]:
    """Mean within-stint LORO RMSE (s), OLS degree-1 vs GP, one circuit."""
    laps = load_circuit_laps(circuit)
    races = sorted(laps["race"].unique())
    ols_rmses, gp_rmses = [], []
    for held_out in races:
        train_laps = laps[laps["race"] != held_out]
        test_laps = laps[laps["race"] == held_out]
        train, _ = build_modelling_frame(train_laps, circuit)
        test, _ = build_modelling_frame(test_laps, circuit)
        if train.empty or test.empty:
            continue

        ols_fit = fit_circuit(train, circuit, degree=1)
        gp_fit = fit_circuit_gp(train, circuit)

        for pred, bucket in ((predict_shape(ols_fit, test), ols_rmses),
                              (predict_shape_gp(gp_fit, test), gp_rmses)):
            valid = pred.notna()
            if not valid.any():
                continue
            actual = test.loc[valid, "lap_time_s"] - test.loc[valid].groupby("stint_id")["lap_time_s"].transform("mean")
            predicted = pred[valid] - pred[valid].groupby(test.loc[valid, "stint_id"]).transform("mean")
            err = actual - predicted
            bucket.append(float(np.sqrt((err**2).mean())))
    return float(np.mean(ols_rmses)), float(np.mean(gp_rmses))


@pytest.mark.skipif(
    not (F1_REPORTS_DIR / "degradation_phase2.md").exists(),
    reason="degradation_phase2.md not generated",
)
def test_committed_report_still_has_the_gp_robustness_section() -> None:
    text = (F1_REPORTS_DIR / "degradation_phase2.md").read_text(encoding="utf-8")
    assert "GP robustness check" in text, (
        "the hand-written GP-vs-OLS section is missing from "
        "degradation_phase2.md -- most likely run_degradation.py was "
        "re-run and silently dropped it (no script regenerates this "
        "section; see this test's module-level comment)"
    )


def test_gp_is_not_meaningfully_better_than_ols_out_of_sample() -> None:
    """The report's claim: GP is statistically indistinguishable from OLS on
    real leave-one-race-out folds -- extra functional flexibility does not
    recover cross-season predictability. Re-measured directly, not just read
    off the committed text."""
    diffs = []
    for circuit in _CIRCUITS:
        ols_rmse, gp_rmse = _gp_vs_ols_loro(circuit)
        diffs.append(ols_rmse - gp_rmse)
    mean_abs_diff = float(np.mean(np.abs(diffs)))
    # The committed report measured a 0.006s mean improvement (0.025s mean
    # absolute per-fold difference) on a ~0.84s/lap error -- generously
    # bounded here since this reruns on whatever seasons are ingested today.
    assert mean_abs_diff < 0.10
