"""Leave-one-race-out cross-validation for the degradation model.

Leakage rules enforced here:

- The test race NEVER appears in the training data (asserted, not assumed).
- Driver-race intercepts cannot transfer to an unseen race, so evaluation is
  on the *within-stint shape*: both actual and predicted lap times are
  demeaned per stint, and the model is scored on how well it predicts how a
  stint evolves — which is exactly the quantity the Phase 4 simulator needs
  ("how much slower will these tyres be in N laps").

The within-stint R² is therefore the honest headline metric; the overall R²
of the full fit is inflated by the fixed effects and is reported only as a
sanity check.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.degradation.model import fit_circuit, predict_shape


@dataclass(frozen=True)
class FoldResult:
    """CV metrics for one held-out race."""

    circuit: str
    degree: int
    test_race: str
    rmse_s: float
    r2_within: float
    n_laps: int
    n_stints: int
    n_unseen_compound_laps: int


def _demean_by_stint(values: pd.Series, stint_ids: pd.Series) -> pd.Series:
    return values - values.groupby(stint_ids).transform("mean")


def leave_one_race_out(df: pd.DataFrame, circuit: str, degree: int) -> list[FoldResult]:
    """Run LORO CV over all races of one circuit."""
    folds: list[FoldResult] = []
    for test_race in sorted(df["race"].unique()):
        train = df[df["race"] != test_race]
        test = df[df["race"] == test_race]
        if train.empty or test.empty:
            continue
        assert test_race not in set(train["race"]), "leakage: test race in training data"

        fit = fit_circuit(train, circuit, degree=degree)
        shape = predict_shape(fit, test)
        unseen = int(shape.isna().sum())
        valid = shape.notna()
        test_valid = test[valid]
        shape_valid = shape[valid]

        actual = _demean_by_stint(test_valid["lap_time_s"], test_valid["stint_id"])
        predicted = _demean_by_stint(shape_valid, test_valid["stint_id"])

        err = actual - predicted
        ss_res = float((err**2).sum())
        ss_tot = float((actual**2).sum())  # actual is already demeaned
        folds.append(
            FoldResult(
                circuit=circuit,
                degree=degree,
                test_race=test_race,
                rmse_s=float(np.sqrt((err**2).mean())),
                r2_within=1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan"),
                n_laps=int(valid.sum()),
                n_stints=test_valid["stint_id"].nunique(),
                n_unseen_compound_laps=unseen,
            )
        )
    return folds


def mean_rmse(folds: list[FoldResult]) -> float:
    """Average CV RMSE across folds (model-selection criterion)."""
    return float(np.mean([f.rmse_s for f in folds])) if folds else float("nan")
