"""Adversarial rival for endurance (WEC / IMSA).

The endurance counterpart of ``adversarial.py``: the same two-player pit-stop
game — the rival covers instead of following a fixed plan — but built on the
endurance engine (``simulator/endurance.py``): a single net degradation slope,
FCY/Safety-Car neutralisations, a hard fuel-range constraint on the candidate
pit laps, and track-position stickiness measured from reconstructed positions
(``track_position.adjacent_swap_rate_endurance``).

The game-solving core is shared with the F1 model — ``win_probability_matrix``
and ``solve_pit_game`` in ``adversarial.py`` operate on cumulative lap times and
know nothing about a series. Only how those cumulative times are built differs,
and that is the endurance engine.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.simulator.adversarial import (
    DEFAULT_PASSING_WINDOW_S,
    DuelResult,
    solve_pit_game,
    win_probability_matrix,
)
from src.simulator.endurance import (
    FCY,
    GREEN,
    SC,
    EnduranceRaceModel,
    EnduranceScenario,
    _sample_status,
)


@dataclass(frozen=True)
class EnduranceRival:
    """A rival in an endurance duel, at the decision point."""

    gap_s: float               # > 0 => the rival is ahead on track
    tyre_age: int
    laps_since_refuel: int
    pit_lap: int               # its announced next stop (the naive assumption)


def _lap_times(
    model: EnduranceRaceModel, laps: np.ndarray, current_lap: int, is_green: np.ndarray,
    ratio: np.ndarray, slope: np.ndarray, noise: np.ndarray, tyre_age: int, pit_lap: int,
) -> np.ndarray:
    """Per-lap time for one endurance car, ``(n_draws, n_laps)`` — the un-summed
    form of ``endurance.simulate``'s inner computation. ``pit_lap == 0`` means no
    further stop."""
    if pit_lap == 0:
        age = tyre_age + (laps - current_lap)
    else:
        before = laps <= pit_lap
        age = np.where(before, tyre_age + (laps - current_lap),
                       np.maximum(laps - pit_lap, 0))
    per_lap = model.green_pace_s * ratio + np.where(is_green, slope * age.astype(float), 0.0)
    per_lap = per_lap + np.where(is_green, noise, 0.0)
    if pit_lap != 0:
        k = int(pit_lap - current_lap - 1)
        per_lap[:, k] = per_lap[:, k] + model.pit_loss_s / ratio[:, k]
    return per_lap


def _candidates(model: EnduranceRaceModel, current_lap: int, total_laps: int,
                laps_since_refuel: int) -> tuple[int, ...]:
    """Feasible next-stop laps for a car, bounded by its fuel range (mirrors
    ``EnduranceScenario.candidate_pit_laps``, but for either car)."""
    scen = EnduranceScenario(current_lap, total_laps, tyre_age=0,
                             laps_since_refuel=laps_since_refuel)
    return scen.candidate_pit_laps(model)


def duel_endurance(
    scenario: EnduranceScenario,
    rival: EnduranceRival,
    model: EnduranceRaceModel,
    swap_rate: float,
    n_draws: int = 2000,
    seed: int = 20260712,
    passing_window_s: float = DEFAULT_PASSING_WINDOW_S,
) -> DuelResult:
    """Solve the endurance pit-stop game between the ego car and one rival.

    ``swap_rate`` is the circuit's measured endurance overtaking difficulty
    (``track_position.adjacent_swap_rate_endurance``). The two cars can face
    different fuel-bound candidate windows (different ``laps_since_refuel``), so
    the payoff matrix need not be square.
    """
    rng = np.random.default_rng(seed)
    laps = np.arange(scenario.current_lap + 1, scenario.total_laps + 1)
    n_laps = len(laps)
    if n_laps == 0:
        raise ValueError("race already finished at this decision point")

    ego_laps = scenario.candidate_pit_laps(model)
    rival_laps = _candidates(model, scenario.current_lap, scenario.total_laps,
                             rival.laps_since_refuel)

    # Shared realisation for both cars (common random numbers): status timeline
    # and the degradation slope; independent lap noise each.
    status = _sample_status(model, n_laps, n_draws, rng)
    is_green = status == GREEN
    ratio = np.where(status == FCY, model.fcy_pace_ratio,
                     np.where(status == SC, model.sc_pace_ratio, 1.0))
    slope = rng.normal(model.net_slope_s, model.net_slope_se, size=(n_draws, 1))
    ego_noise = rng.normal(0.0, model.lap_noise_s, size=(n_draws, n_laps))
    rival_noise = rng.normal(0.0, model.lap_noise_s, size=(n_draws, n_laps))

    def cum(noise, age, cands):
        return np.stack([
            _lap_times(model, laps, scenario.current_lap, is_green, ratio, slope,
                       noise, age, p).cumsum(axis=1)
            for p in cands
        ])

    ego_cum = cum(ego_noise, scenario.tyre_age, ego_laps)
    riv_cum = cum(rival_noise, rival.tyre_age, rival_laps) - rival.gap_s

    # No-stop candidates (lap 0) never pit: their "exchange" resolves at the end.
    k_ego = np.array([p - scenario.current_lap - 1 if p != 0 else n_laps - 1 for p in ego_laps])
    k_riv = np.array([p - scenario.current_lap - 1 if p != 0 else n_laps - 1 for p in rival_laps])

    win_prob = win_probability_matrix(ego_cum, riv_cum, k_ego, k_riv, swap_rate,
                                      passing_window_s, rng)
    return solve_pit_game(win_prob, ego_laps, rival_laps, rival.pit_lap)
