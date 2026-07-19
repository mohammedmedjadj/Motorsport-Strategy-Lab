"""GP degradation curve: recovers a linear truth as well as OLS, honours the
unseen-compound NaN contract, and skips compounds with too few distinct ages."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.degradation.dataset import build_modelling_frame
from src.degradation.gp_model import fit_circuit_gp, predict_shape_gp
from src.degradation.model import fit_circuit, predict_shape
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
