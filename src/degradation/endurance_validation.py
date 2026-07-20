"""Leave-one-race-out cross-validation for the endurance degradation model.

The endurance analogue of ``src/degradation/validation.py``: fit the net-slope
model (``endurance.fit_endurance_degradation``) on every race of a series
except one, then score how well the pooled net slope predicts the held-out
race's *within-driver-stint shape* — car-driver intercepts cannot transfer to
an unseen race, exactly as in the F1 model, so both actual and predicted lap
times are demeaned per (car, driver_stint) before scoring.

Leakage rule enforced here: the test race's own frame contributes nothing to
the pooled fit (asserted, not assumed).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.degradation.endurance import Coefficient


@dataclass(frozen=True)
class EnduranceFoldResult:
    """CV metrics for one held-out endurance race."""

    series: str
    test_event: str
    pooled_slope: float
    own_slope: float
    rmse_s: float
    r2_within: float
    n_laps: int


def _fit_net_slope(frames: list[pd.DataFrame]) -> Coefficient:
    """Net-slope-only OLS over several races' frames, with event-qualified
    car-driver fixed effects so no intercept is shared across events."""
    pooled = pd.concat(
        [f.assign(unit=f["event"].astype(str) + "::" + f["unit"].astype(str)) for f in frames],
        ignore_index=True,
    )
    fe = pd.get_dummies(pooled["unit"]).to_numpy(dtype=float)
    age = pooled["tyre_age"].to_numpy(dtype=float)
    y = pooled["lap_time_s"].to_numpy(dtype=float)
    design = np.hstack([fe, age[:, None]])
    beta, _, rank, _ = np.linalg.lstsq(design, y, rcond=None)
    resid = y - design @ beta
    dof = max(len(y) - rank, 1)
    se = float(np.sqrt(np.clip(
        np.linalg.pinv(design.T @ design)[-1, -1] * (resid @ resid) / dof, 0.0, None
    )))
    return Coefficient(float(beta[-1]), se)


def leave_one_race_out_endurance(
    frames: dict[str, pd.DataFrame],
) -> list[EnduranceFoldResult]:
    """Run LORO CV over every race of one series.

    ``frames`` maps event name -> the frame from ``build_endurance_frame`` for
    that race (already green/non-pit/traffic-trimmed).
    """
    from src.degradation.endurance import fit_endurance_degradation

    folds: list[EnduranceFoldResult] = []
    events = sorted(frames)
    if len(events) < 2:
        raise ValueError("need at least 2 races to leave one out")

    for test_event in events:
        train = [frames[e] for e in events if e != test_event]
        assert test_event not in {e for e in events if e != test_event}, "leakage"

        pooled_slope = _fit_net_slope(train)
        test = frames[test_event]

        key = test["car"].astype(str) + "|" + test["driver_stint"].astype(str)
        actual = test["lap_time_s"].to_numpy(dtype=float)
        predicted = pooled_slope.value * test["tyre_age"].to_numpy(dtype=float)

        def demean(values: np.ndarray) -> np.ndarray:
            s = pd.Series(values, index=test.index)
            return (s - s.groupby(key.values).transform("mean")).to_numpy()

        a_dm, p_dm = demean(actual), demean(predicted)
        err = a_dm - p_dm
        ss_res = float((err**2).sum())
        ss_tot = float((a_dm**2).sum())

        own_slope = fit_endurance_degradation(test).net_slope.value
        folds.append(EnduranceFoldResult(
            series=str(test["series"].iloc[0]),
            test_event=test_event,
            pooled_slope=pooled_slope.value,
            own_slope=own_slope,
            rmse_s=float(np.sqrt((err**2).mean())),
            r2_within=1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan"),
            n_laps=len(test),
        ))
    return folds


def mean_r2(folds: list[EnduranceFoldResult]) -> float:
    return float(np.mean([f.r2_within for f in folds])) if folds else float("nan")
