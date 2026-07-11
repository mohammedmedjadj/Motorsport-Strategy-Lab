"""Tests for the degradation model: coefficient recovery on synthetic data
with known ground truth, and leakage-free cross-validation mechanics."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.degradation.dataset import build_modelling_frame
from src.degradation.model import fit_circuit, predict_shape
from src.degradation.validation import leave_one_race_out

TRUE_FUEL = -0.05  # s per race lap
TRUE_DEG = {"SOFT": 0.09, "MEDIUM": 0.055, "HARD": 0.03}


def make_synthetic(seed: int = 42, noise_s: float = 0.05) -> pd.DataFrame:
    """Two races x 4 drivers x 3 stints with known fuel/degradation slopes."""
    rng = np.random.default_rng(seed)
    rows: list[dict[str, object]] = []
    stint_plan = [("SOFT", 15), ("MEDIUM", 20), ("HARD", 22)]
    for race in ("2024_synth", "2025_synth"):
        for d, driver in enumerate(("AAA", "BBB", "CCC", "DDD")):
            base = 90.0 + 0.3 * d + (0.5 if race == "2025_synth" else 0.0)
            lap_number = 0
            for stint_no, (compound, length) in enumerate(stint_plan, start=1):
                for age in range(1, length + 1):
                    lap_number += 1
                    rows.append(
                        {
                            "race": race,
                            "Driver": driver,
                            "Stint": stint_no,
                            "LapNumber": lap_number,
                            "Compound": compound,
                            "TyreLife": age,
                            "lap_time_s": base
                            + TRUE_FUEL * lap_number
                            + TRUE_DEG[compound] * age
                            + rng.normal(0.0, noise_s),
                            "is_pace_lap": True,
                        }
                    )
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def frame() -> pd.DataFrame:
    df, _ = build_modelling_frame(make_synthetic(), "synth")
    return df


def test_fit_recovers_known_coefficients(frame: pd.DataFrame) -> None:
    fit = fit_circuit(frame, "synth", degree=1)
    assert fit.fuel_slope.value == pytest.approx(TRUE_FUEL, abs=0.005)
    for compound, true_slope in TRUE_DEG.items():
        assert fit.deg_coefs[compound][0].value == pytest.approx(true_slope, abs=0.005)


def test_confidence_intervals_cover_truth(frame: pd.DataFrame) -> None:
    fit = fit_circuit(frame, "synth", degree=1)
    for compound, true_slope in TRUE_DEG.items():
        coef = fit.deg_coefs[compound][0]
        assert coef.ci_low <= true_slope <= coef.ci_high


def test_predict_shape_nan_for_unseen_compound(frame: pd.DataFrame) -> None:
    fit = fit_circuit(frame, "synth", degree=1)
    probe = frame.head(3).copy()
    probe.loc[probe.index[0], "Compound"] = "UNSEEN"
    shape = predict_shape(fit, probe)
    assert shape.isna().tolist() == [True, False, False]


def test_loro_cv_has_no_leakage_and_near_perfect_on_synthetic(frame: pd.DataFrame) -> None:
    folds = leave_one_race_out(frame, "synth", degree=1)
    assert {f.test_race for f in folds} == {"2024_synth", "2025_synth"}
    for fold in folds:
        # noise_s = 0.05 -> RMSE at the noise floor is the best achievable;
        # the R2 bound follows from the synthetic signal/noise ratio, with
        # margin (observed ~0.85 when RMSE sits exactly on the floor).
        assert fold.rmse_s < 0.10
        assert fold.r2_within > 0.80
        assert fold.n_unseen_compound_laps == 0


def test_short_stints_are_dropped() -> None:
    df = make_synthetic()
    # Truncate one stint to 3 laps: it must not survive frame building.
    victim = (df["race"] == "2024_synth") & (df["Driver"] == "AAA") & (df["Stint"] == 1)
    df = df[~victim | (df["TyreLife"] <= 3)]
    frame, diag = build_modelling_frame(df, "synth")
    assert not ((frame["driver_race"] == "2024_synth_AAA") & (frame["Stint"] == 1)).any()
    assert diag.after_min_stint < diag.after_traffic_trim


def test_quadratic_fit_runs_and_exposes_two_coefficients(frame: pd.DataFrame) -> None:
    fit = fit_circuit(frame, "synth", degree=2)
    assert all(len(coefs) == 2 for coefs in fit.deg_coefs.values())
