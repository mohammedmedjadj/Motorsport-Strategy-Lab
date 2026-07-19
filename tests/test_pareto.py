"""Exact multi-objective Pareto front over candidate pit laps."""

from __future__ import annotations

import numpy as np
import pytest

from src.simulator.engine import RivalSpec, simulate
from src.simulator.recommend import pareto_front, summarise
from tests.test_simulator import make_model, make_scenario


def _rec():
    rivals = (
        RivalSpec("car_ahead", gap_s=2.5, compound="SOFT", tyre_age=15,
                  pit_lap=30, target_compound="HARD"),
        RivalSpec("car_behind", gap_s=-3.0, compound="SOFT", tyre_age=15,
                  pit_lap=28, target_compound="HARD"),
    )
    scenario = make_scenario(rivals=rivals)
    return summarise(scenario, simulate(scenario, make_model(), n_draws=2000, seed=11))


def test_single_objective_front_is_the_optimum() -> None:
    rec = _rec()
    front = pareto_front(rec, {"median_s": "min"})
    # With one objective the non-dominated set is exactly the row(s) at the min.
    assert front["median_s"].min() == rec.table["median_s"].min()
    assert set(front["pit_lap"]) <= set(rec.table["pit_lap"])
    assert rec.best_lap in set(front["pit_lap"])


def test_front_points_are_mutually_non_dominated() -> None:
    rec = _rec()
    objs = {"mean_s": "min", "p_ahead_car_ahead": "max"}
    front = pareto_front(rec, objs)
    v = front[list(objs)].to_numpy(float) * np.array([-1.0, 1.0])  # larger = better
    for i in range(len(v)):
        for j in range(len(v)):
            if i == j:
                continue
            # No front point may dominate another front point.
            assert not (np.all(v[j] >= v[i]) and np.any(v[j] > v[i]))


def test_every_off_front_lap_is_dominated_by_the_front() -> None:
    rec = _rec()
    objs = {"mean_s": "min", "p_ahead_car_ahead": "max"}
    front_laps = set(pareto_front(rec, objs)["pit_lap"])
    signs = np.array([-1.0, 1.0])
    tab = rec.table
    front_vals = tab[tab["pit_lap"].isin(front_laps)][list(objs)].to_numpy(float) * signs
    for _, row in tab[~tab["pit_lap"].isin(front_laps)].iterrows():
        p = np.array([row[c] for c in objs]) * signs
        dominated = np.any(
            np.all(front_vals >= p, axis=1) & np.any(front_vals > p, axis=1)
        )
        assert dominated, f"lap {int(row['pit_lap'])} is off-front but not dominated"


def test_conflicting_objectives_surface_a_real_tradeoff() -> None:
    """When two objectives genuinely disagree, both extremes must appear on the
    front and interior dominated points must be dropped. Built on a hand-made
    table so the trade-off is guaranteed (real simulator scenarios may have no
    trade-off at all — e.g. when undercutting early dominates on every axis,
    the front honestly collapses to a single lap)."""
    import pandas as pd

    from src.simulator.recommend import Recommendation

    table = pd.DataFrame({
        "pit_lap": [10, 11, 12, 13],
        "mean_s": [100.0, 101.0, 101.0, 103.0],   # fastest = lap 10
        "p_ahead_x": [0.10, 0.15, 0.20, 0.90],     # best position = lap 13
    })
    rec = Recommendation(scenario=make_scenario(), table=table, best_lap=10, window=(10,))
    front = pareto_front(rec, {"mean_s": "min", "p_ahead_x": "max"})
    laps = set(front["pit_lap"])
    assert 10 in laps and 13 in laps          # both extremes are non-dominated
    assert 11 not in laps                      # lap 11 is dominated by lap 12 (=mean, better pos)
    assert len(laps) >= 2                      # a real trade-off, not a single point


def test_invalid_objectives_are_rejected() -> None:
    rec = _rec()
    with pytest.raises(ValueError, match="at least one objective"):
        pareto_front(rec, {})
    with pytest.raises(ValueError, match="unknown objective"):
        pareto_front(rec, {"nonexistent_col": "min"})
    with pytest.raises(ValueError, match="min.*max|direction"):
        pareto_front(rec, {"median_s": "lowest"})
