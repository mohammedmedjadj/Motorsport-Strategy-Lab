"""Leave-one-season-out cross-validation for the endurance pit-loss estimator.

The endurance analogue of ``src/simulator/pit_loss_validation.py`` (F1), same
motivation: ``estimate_pit_loss`` (``src/simulator/endurance.py``) has always
been reported as a single number per circuit-season, never cross-validated
against a season it hadn't seen. WEC and IMSA pit stops also refuel and
usually change driver, so there is a second reason to expect worse transfer
than F1: a stop's cost depends on how much fuel a team chooses to add, which
can shift between seasons for reasons that have nothing to do with the
circuit (a regulation change to tank size, a team's strategy philosophy).

Leakage rule enforced here: the held-out season's own laps never enter the
training median (asserted, not assumed).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.simulator.endurance import estimate_pit_loss, trimmed_pit_loss_events


@dataclass(frozen=True)
class EndurancePitLossFoldResult:
    """CV metrics for one held-out season's pit loss."""

    series: str
    event: str
    held_out: str
    train_median_s: float
    test_median_s: float
    rmse_s: float
    n_train_events: int
    n_test_events: int


def leave_one_race_out_pit_loss_endurance(
    laps_by_season: dict[str, pd.DataFrame], series: str, event: str
) -> list[EndurancePitLossFoldResult]:
    """Run LORO CV over every season of one circuit.

    ``laps_by_season`` maps a season identifier (e.g. ``"2023"``) to that
    season's raw laps (``EnduranceLoader.load_laps`` output, before the
    degradation-specific ``build_endurance_frame`` filtering -- pit-loss
    needs the raw pit/green/flag columns, same as the F1 validator uses raw
    laps rather than the pace-lap-only degradation frame).
    """
    folds: list[EndurancePitLossFoldResult] = []
    keys = sorted(laps_by_season)
    if len(keys) < 2:
        return folds

    for held_out in keys:
        train_keys = [k for k in keys if k != held_out]
        assert held_out not in train_keys, "leakage: held-out season in training data"
        # estimate_pit_loss groups its green-pace baseline by "car" alone (it
        # is normally called on one race at a time); qualify car IDs by
        # season before pooling multiple seasons, so a car number reused
        # across seasons is never fused into one cross-season baseline pace
        # -- the same guard endurance_validation.py's _fit_net_slope applies
        # to driver-stint fixed effects, for the identical reason.
        train = pd.concat(
            [
                laps_by_season[k].assign(car=f"{k}::" + laps_by_season[k]["car"].astype(str))
                for k in train_keys
            ],
            ignore_index=True,
        )
        test = laps_by_season[held_out]

        try:
            train_median, _, n_train = estimate_pit_loss(train)
        except ValueError:
            continue

        # trimmed, not raw: a genuine repair/driver-change stop in the
        # held-out season would otherwise dominate the squared error and
        # measure "did we predict a rare outlier" rather than "did we
        # predict the routine stop cost", which is what estimate_pit_loss
        # actually models everywhere else in this project.
        test_events = trimmed_pit_loss_events(test)
        if test_events.size == 0:
            continue

        err = test_events - train_median
        folds.append(
            EndurancePitLossFoldResult(
                series=series,
                event=event,
                held_out=held_out,
                train_median_s=train_median,
                test_median_s=float(np.median(test_events)),
                rmse_s=float(np.sqrt((err**2).mean())),
                n_train_events=n_train,
                n_test_events=int(test_events.size),
            )
        )
    return folds


def mean_rmse(folds: list[EndurancePitLossFoldResult]) -> float:
    return float(np.mean([f.rmse_s for f in folds])) if folds else float("nan")
