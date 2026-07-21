"""The adversarial rival (two-car pit-stop game): internal correctness against
the engine, the game-theoretic invariants that must always hold, and the
racecraft behaviours (a cover costs the ego car; track stickiness matters)."""

from __future__ import annotations

import numpy as np
import pytest

from src.simulator.adversarial import _car_lap_times, duel
from src.simulator.artifacts import load_circuit_models
from src.simulator.engine import (
    RivalSpec,
    Scenario,
    _car_times,
    _sample_coef_batch,
    _sample_status,
)

MODELS = load_circuit_models()


def _scenario(circuit: str, total: int, gap_s: float, ego_age: int = 22,
              rival_age: int = 22) -> tuple[Scenario, RivalSpec]:
    rival = RivalSpec("R", gap_s=gap_s, compound="MEDIUM", tyre_age=rival_age,
                      pit_lap=48, target_compound="HARD")
    scen = Scenario(circuit, current_lap=38, total_laps=total, compound="MEDIUM",
                    tyre_age=ego_age, target_compound="HARD", rivals=(rival,))
    return scen, rival


def test_per_lap_times_sum_to_the_engine_total() -> None:
    """The lap-by-lap decomposition must be exactly the engine's total time —
    otherwise the on-track position it derives is not consistent with the
    win/loss the rest of the project computes."""
    m = MODELS["monaco"]
    rng = np.random.default_rng(1)
    n, cur, total = 400, 40, 78
    laps = np.arange(cur + 1, total + 1)
    status = np.stack([_sample_status(m, len(laps), rng) for _ in range(n)])
    fuel = _sample_coef_batch(rng, m.fuel_slope, n)
    deg = {c: tuple(_sample_coef_batch(rng, g, n) for g in cf)
           for c, cf in m.degradation.items()}
    noise = rng.normal(0.0, m.lap_noise_s, size=(n, len(laps)))
    per_lap = _car_lap_times(m, laps, status, noise, fuel, deg, "MEDIUM", 25, cur, 46, "HARD")
    total_engine = _car_times(m, laps, status, noise, fuel, deg, "MEDIUM", 25, cur, 46,
                              "HARD", m.pit_loss.median_s)
    assert np.allclose(per_lap.cumsum(axis=1)[:, -1], total_engine)


def test_result_is_reproducible_and_well_formed() -> None:
    scen, rival = _scenario("monaco", 78, gap_s=0.8)
    a = duel(scen, rival, MODELS["monaco"], swap_rate=0.004, n_draws=800, seed=3)
    b = duel(scen, rival, MODELS["monaco"], swap_rate=0.004, n_draws=800, seed=3)
    assert np.array_equal(a.win_prob, b.win_prob)
    assert a.win_prob.shape == (len(a.ego_pit_laps), len(a.rival_pit_laps))
    assert ((a.win_prob >= 0) & (a.win_prob <= 1)).all()


def test_covering_never_helps_the_ego_car() -> None:
    """Game invariant: the rival choosing its best cover can only lower (never
    raise) the ego car's win probability at the naive pit lap, and the
    cover-aware optimum is at least as good as being caught out."""
    scen, rival = _scenario("barcelona", 66, gap_s=1.2)
    r = duel(scen, rival, MODELS["barcelona"], swap_rate=0.037, n_draws=2000, seed=5)
    assert r.naive_win_prob >= r.naive_win_prob_if_covered - 1e-9
    assert r.adversarial_win_prob >= r.naive_win_prob_if_covered - 1e-9
    assert r.cost_of_ignoring_the_cover >= -1e-9


def test_a_clearly_faster_car_wins_regardless_of_the_cover() -> None:
    """A car far ahead on much fresher tyres wins with high probability whatever
    the rival does — the game only bites when the cars are close."""
    scen, rival = _scenario("barcelona", 66, gap_s=-8.0, ego_age=4, rival_age=30)
    r = duel(scen, rival, MODELS["barcelona"], swap_rate=0.037, n_draws=1500, seed=1)
    assert r.adversarial_win_prob > 0.85


def test_worked_example_in_the_report_holds() -> None:
    """Pin the report's headline: at Monaco the undercut works when uncovered,
    the cover meaningfully cuts it, and the naive plan overstates the win."""
    scen, rival = _scenario("monaco", 78, gap_s=1.2)
    r = duel(scen, rival, MODELS["monaco"], swap_rate=0.0038, n_draws=3000, seed=11)
    ego0 = 0  # earliest (undercut) lap
    j_plan = r.rival_pit_laps.index(min(r.rival_pit_laps, key=lambda x: abs(x - 48)))
    uncovered = r.win_prob[ego0, j_plan]
    covered = r.win_prob[ego0, int(r.rival_best_response[ego0])]
    assert uncovered > covered                       # covering denies the undercut
    assert r.naive_win_prob - r.naive_win_prob_if_covered > 0.03  # ~8 points reported


def test_track_stickiness_changes_the_defence() -> None:
    """A car defending a lead it already holds keeps it more easily at a stickier
    (lower-swap) circuit: the same scenario must give a higher win probability
    when position is harder to lose."""
    scen, rival = _scenario("monaco", 78, gap_s=-1.2)  # ego ahead, defending
    sticky = duel(scen, rival, MODELS["monaco"], swap_rate=0.004, n_draws=2500, seed=9)
    fluid = duel(scen, rival, MODELS["monaco"], swap_rate=0.060, n_draws=2500, seed=9)
    assert sticky.naive_win_prob > fluid.naive_win_prob
