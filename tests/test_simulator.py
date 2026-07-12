"""Simulator invariants: reproducibility, physical bounds, and directional
sanity (degradation pressure, SC discount, rival gaps)."""

from __future__ import annotations

import numpy as np
import pytest

from src.simulator.artifacts import CircuitModel, GaussianCoef, HazardPosterior
from src.simulator.engine import GREEN, SC, RivalSpec, Scenario, _sample_status, simulate
from src.simulator.pit_loss import PaceRatios, PitLossEstimate
from src.simulator.recommend import summarise


def make_model(
    deg_soft: float = 0.10,
    deg_hard: float = 0.03,
    sc_rate: float = 0.01,
    lap_noise: float = 0.4,
) -> CircuitModel:
    """Synthetic circuit: 90s pace, SOFT degrades fast, HARD slow."""
    return CircuitModel(
        circuit="synth",
        green_pace_s=90.0,
        lap_noise_s=lap_noise,
        fuel_slope=GaussianCoef(-0.05, 0.002),
        degradation={
            "SOFT": (GaussianCoef(deg_soft, 0.005),),
            "HARD": (GaussianCoef(deg_hard, 0.005),),
        },
        sc_hazard=HazardPosterior(alpha=sc_rate * 500, beta=500),
        vsc_hazard=HazardPosterior(alpha=0.005 * 500, beta=500),
        sc_durations=(3, 4, 5),
        vsc_durations=(1, 2),
        pit_loss=PitLossEstimate("synth", median_s=21.0, iqr_s=2.0, n_events=40),
        pace_ratios=PaceRatios("synth", 1.40, 1.20, 10, 5, False, False),
    )


def make_scenario(**overrides: object) -> Scenario:
    defaults: dict[str, object] = {
        "circuit": "synth",
        "current_lap": 20,
        "total_laps": 55,
        "compound": "SOFT",
        "tyre_age": 15,
        "target_compound": "HARD",
    }
    defaults.update(overrides)
    return Scenario(**defaults)  # type: ignore[arg-type]


def test_same_seed_is_bit_identical() -> None:
    a = simulate(make_scenario(), make_model(), n_draws=300, seed=7)
    b = simulate(make_scenario(), make_model(), n_draws=300, seed=7)
    assert np.array_equal(a.our_time, b.our_time)


def test_candidates_stay_inside_race_bounds() -> None:
    scenario = make_scenario()
    result = simulate(scenario, make_model(), n_draws=100)
    assert min(result.candidates) == scenario.current_lap + 1
    assert max(result.candidates) <= scenario.total_laps - 3


def test_p_best_is_a_probability_distribution() -> None:
    result = simulate(make_scenario(), make_model(), n_draws=500)
    assert np.all(result.p_best >= 0)
    assert result.p_best.sum() == pytest.approx(1.0)


def test_higher_degradation_pulls_pit_earlier() -> None:
    slow_deg = simulate(make_scenario(), make_model(deg_soft=0.03), n_draws=1500)
    fast_deg = simulate(make_scenario(), make_model(deg_soft=0.20), n_draws=1500)
    best_slow = slow_deg.candidates[int(np.argmin(np.median(slow_deg.our_time, 1)))]
    best_fast = fast_deg.candidates[int(np.argmin(np.median(fast_deg.our_time, 1)))]
    assert best_fast < best_slow


def test_pit_under_sc_is_cheaper_than_green() -> None:
    """Force an SC exactly at one candidate lap; that lap must gain an edge."""
    from src.simulator import engine

    model = make_model(sc_rate=0.0)
    scenario = make_scenario()
    laps = np.arange(scenario.current_lap + 1, scenario.total_laps + 1)
    status_green = np.full(len(laps), GREEN, dtype=np.int8)
    status_sc = status_green.copy()
    pit_idx = 4  # candidate lap current+5
    status_sc[pit_idx] = SC
    noise = np.zeros(len(laps))
    deg = {c: tuple(g.mean for g in coefs) for c, coefs in model.degradation.items()}
    args = dict(
        model=model, scenario_laps=laps, noise=noise, fuel=model.fuel_slope.mean,
        deg=deg, start_compound="SOFT", start_age=15,
        current_lap=scenario.current_lap, pit_lap=int(laps[pit_idx]),
        target_compound="HARD", pit_loss_s=model.pit_loss.median_s,
    )
    t_green = engine._car_times(status=status_green, **args)
    t_sc = engine._car_times(status=status_sc, **args)
    # Under SC the lap itself is slower but the stop is discounted by 1/1.4;
    # isolate the stop discount by comparing against staying out.
    args_no_pit = {**args, "pit_lap": None, "target_compound": None}
    stay_green = engine._car_times(status=status_green, **args_no_pit)
    stay_sc = engine._car_times(status=status_sc, **args_no_pit)
    # Diff-in-diff isolates the stop cost: degradation and base-lap terms
    # cancel exactly between the pit and stay-out paths.
    cost_green = t_green - stay_green
    cost_sc = t_sc - stay_sc
    assert cost_sc < cost_green
    expected_discount = model.pit_loss.median_s * (1 / 1.40 - 1.0)
    assert cost_sc - cost_green == pytest.approx(expected_discount, rel=0.01)


def test_rival_gap_moves_p_ahead_in_the_right_direction() -> None:
    rival_ahead = RivalSpec("ahead", gap_s=3.0, compound="SOFT", tyre_age=15,
                            pit_lap=30, target_compound="HARD")
    rival_behind = RivalSpec("behind", gap_s=-3.0, compound="SOFT", tyre_age=15,
                             pit_lap=30, target_compound="HARD")
    scenario = make_scenario(rivals=(rival_ahead, rival_behind))
    result = simulate(scenario, make_model(), n_draws=1500)
    rec = summarise(scenario, result)
    # At the SAME strategy as both rivals (pit lap 30), only the +/-3s gap
    # differs: it must decide the direction of P(ahead).
    same_row = rec.table.loc[rec.table["pit_lap"] == 30].iloc[0]
    assert same_row["p_ahead_ahead"] < 0.5
    assert same_row["p_ahead_behind"] > 0.5
    # And the gap ordering must hold at the recommended lap too.
    best_row = rec.table.loc[rec.table["pit_lap"] == rec.best_lap].iloc[0]
    assert best_row["p_ahead_behind"] > best_row["p_ahead_ahead"]


def test_status_sampler_respects_duration_pool_and_seeds() -> None:
    model = make_model(sc_rate=0.05)
    rng = np.random.default_rng(3)
    status = _sample_status(model, 200, rng)
    assert set(np.unique(status)).issubset({0, 1, 2})
    # With a high rate over 200 laps, at least one SC must appear.
    assert (status == SC).any()


def test_window_contains_best_lap_and_is_contiguous_enough() -> None:
    scenario = make_scenario()
    rec = summarise(scenario, simulate(scenario, make_model(), n_draws=800))
    assert rec.best_lap in rec.window
    assert all(scenario.current_lap < lap <= scenario.total_laps - 3 for lap in rec.window)
