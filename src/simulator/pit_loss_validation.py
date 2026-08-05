"""Leave-one-race-out cross-validation for the F1 pit-loss estimator.

The pit-loss analogue of ``src/degradation/validation.py``. The degradation
model has always been cross-validated this way; the pit-loss estimator
(``estimate_pit_loss``) never has been -- it has only ever been reported as a
single number pooled across all seasons of a circuit; whether that number
would have predicted a season it hadn't seen was never actually tested.

Unlike degradation, pit loss has no within-stint *shape* to predict -- it is
a single scalar per circuit (median green-flag stop cost). The honest LORO
test here is simpler and more direct: fit the median on every season but
one, then score how well that pooled median predicts each *individual*
clean pit event of the held-out season (RMSE), against the held-out
season's own median as a sanity comparison.

Leakage rule enforced here: the held-out race's own rows never enter the
training median (asserted, not assumed).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.simulator.pit_loss import estimate_pit_loss, trimmed_pit_loss_events


@dataclass(frozen=True)
class PitLossFoldResult:
    """CV metrics for one held-out race's pit loss."""

    circuit: str
    test_race: str
    train_median_s: float
    test_median_s: float
    rmse_s: float
    n_train_events: int
    n_test_events: int


def leave_one_race_out_pit_loss(laps: pd.DataFrame, circuit: str) -> list[PitLossFoldResult]:
    """Run LORO CV over every race (season) of one circuit.

    ``laps`` must carry a ``race`` column identifying each held-out unit --
    for F1 that is ``load_circuit_laps(circuit)``'s ``"{season}_{circuit}"``.
    """
    folds: list[PitLossFoldResult] = []
    for test_race in sorted(laps["race"].unique()):
        train = laps[laps["race"] != test_race]
        test = laps[laps["race"] == test_race]
        if train.empty or test.empty:
            continue
        assert test_race not in set(train["race"]), "leakage: test race in training data"

        try:
            train_est = estimate_pit_loss(train, circuit)
        except ValueError:
            continue  # no clean events in the training seasons either

        test_events = trimmed_pit_loss_events(test)
        if len(test_events) == 0:
            continue

        err = test_events - train_est.median_s
        folds.append(
            PitLossFoldResult(
                circuit=circuit,
                test_race=test_race,
                train_median_s=train_est.median_s,
                test_median_s=float(np.median(test_events)),
                rmse_s=float(np.sqrt((err**2).mean())),
                n_train_events=train_est.n_events,
                n_test_events=len(test_events),
            )
        )
    return folds


def mean_rmse(folds: list[PitLossFoldResult]) -> float:
    return float(np.mean([f.rmse_s for f in folds])) if folds else float("nan")
