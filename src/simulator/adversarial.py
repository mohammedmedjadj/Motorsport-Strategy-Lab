"""Adversarial rival model — the pit-stop decision as a two-player game.

Every other layer of this project treats a rival as a fixed plan: it announces
a pit lap and sticks to it. Real strategy is not like that. If you pit, your
rival *covers* — pits the next lap to kill your undercut; if you stay out, they
might pit early to undercut *you*. Your best pit lap depends on what they do,
and theirs on what you do. It is a game, and this module solves it.

## The construction (all on measured primitives, nothing fabricated)

For a grid of ``(your pit lap, rival pit lap)`` pairs we run the Monte Carlo
engine head-to-head — both cars under the **same** resampled realisation
(degradation and fuel coefficients, neutralisation timeline, common random
numbers), each with its own lap noise — computing every car's time **lap by
lap**, and reduce each pair to one number:

    P[i, j] = P(you finish ahead of the rival | you pit lap i, rival pits lap j)

Two things decide "finishing ahead", and both matter:

1. **Who wins the pit exchange.** The undercut is resolved the lap *both* cars
   have finally stopped: whoever is ahead on the road then (from the cumulative
   lap times — the fresh-tyre out-lap against the rival's worn in-lap) has made
   the move. This is the discrete, binary heart of an undercut that a
   final-gap-only model smooths away.
2. **Whether track position then holds.** How sticky that lead is is the
   **measured** overtaking difficulty of the circuit (``track_position.py``):
   over the remaining laps the leader keeps the place with probability
   ``hold_probability(swap_rate, laps)`` when the two are within a passing
   window. So at Monaco a lead won in the pits is gold; at Barcelona it can
   still evaporate. When the final pace gap is clearly outside the window, pace
   decides and position stickiness is moot.

## Solving the game

- **Rival best response**: for each of your laps ``i`` the rival picks the lap
  ``j`` that *minimises* your win probability — the optimal cover.
- **Naive optimum**: your best lap assuming the rival keeps its announced plan
  (what every other layer of this project assumes).
- **Stackelberg optimum**: your best lap once the rival covers optimally.

The headline is the gap between them — *how much win probability you give away
by assuming the rival will not react* — exactly the objection a real strategist
raises against a frozen-rival simulator.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.simulator.artifacts import CircuitModel
from src.simulator.engine import (
    GREEN,
    SC,
    VSC,
    RivalSpec,
    Scenario,
    _poly,
    _sample_coef_batch,
    _sample_status,
)
from src.simulator.track_position import hold_probability

#: On-track gap (seconds) within which position is genuinely contestable — the
#: rough range a following car can attack from. The one racecraft constant not
#: measured from data; exposed as a parameter and sensitivity-checked in tests.
DEFAULT_PASSING_WINDOW_S = 1.0


def _car_lap_times(
    model: CircuitModel, laps: np.ndarray, status: np.ndarray, noise: np.ndarray,
    fuel: np.ndarray, deg: dict, start_compound: str, start_age: int,
    current_lap: int, pit_lap: int, target_compound: str | None,
) -> np.ndarray:
    """Per-lap time for one car, shape ``(n_draws, n_laps)`` — the un-summed
    counterpart of ``engine._car_times``. Cumulative-summed by the caller to get
    on-track position at any point in the race."""
    green = status == GREEN
    ratio = np.where(status == SC, model.pace_ratios.sc_ratio,
                     np.where(status == VSC, model.pace_ratios.vsc_ratio, 1.0))
    base = np.where(green, model.green_pace_s + fuel * laps + noise,
                    model.green_pace_s * ratio)
    k = int(pit_lap - current_lap - 1)  # index of the in-lap
    old_age = start_age + (laps - current_lap)
    new_age = np.maximum(laps - pit_lap, 0.0)
    deg_old = np.where(green, _poly(deg[start_compound], old_age.astype(float)), 0.0)
    deg_new = np.where(green, _poly(deg[target_compound or start_compound], new_age), 0.0)
    idx = np.arange(len(laps))
    per_lap = base + np.where(idx <= k, deg_old, deg_new)
    per_lap[:, k] = per_lap[:, k] + model.pit_loss.median_s / ratio[:, k]
    return per_lap


@dataclass(frozen=True)
class DuelResult:
    """Outcome of solving the two-car pit-stop game."""

    ego_pit_laps: tuple[int, ...]
    rival_pit_laps: tuple[int, ...]
    win_prob: np.ndarray            # P[i, j] = P(ego finishes ahead)
    rival_best_response: np.ndarray  # rival's covering lap index for each ego lap

    naive_pit_lap: int             # ego optimum assuming the rival keeps its plan
    naive_win_prob: float          # its win prob under that (optimistic) assumption
    naive_win_prob_if_covered: float  # what it really becomes once they cover
    adversarial_pit_lap: int       # ego optimum that anticipates the cover
    adversarial_win_prob: float

    @property
    def naive_overstatement(self) -> float:
        """Win probability the naive (frozen-rival) plan *overstates*: what you
        think you will get at the naive pit lap minus what you really get once
        the rival covers. The headline cost of ignoring the reaction."""
        return self.naive_win_prob - self.naive_win_prob_if_covered

    @property
    def cost_of_ignoring_the_cover(self) -> float:
        """Win probability recovered by switching from the naive pit lap (once
        covered) to the cover-aware optimum — the *value* of playing the game
        rather than the frozen-rival plan. Often small when the naive lap is
        already robust to a cover."""
        return self.adversarial_win_prob - self.naive_win_prob_if_covered


def win_probability_matrix(
    ego_cum: np.ndarray, riv_cum: np.ndarray, k_ego: np.ndarray, k_rival: np.ndarray,
    swap_rate: float, passing_window_s: float, rng: np.random.Generator,
) -> np.ndarray:
    """Series-agnostic payoff matrix from per-candidate cumulative lap times.

    ``ego_cum``/``riv_cum`` are ``(n_choice, n_draws, n_laps)`` cumulative-time
    arrays (the rival's already offset by any starting gap); ``k_ego``/``k_rival``
    are the in-lap indices per candidate. Returns ``P[i, j] = P(ego ahead)``.
    """
    n_laps = ego_cum.shape[2]
    ego_total, riv_total = ego_cum[:, :, -1], riv_cum[:, :, -1]
    leader_holds = rng.random(ego_cum.shape[1]) < hold_probability(swap_rate, n_laps)
    win = np.empty((ego_cum.shape[0], riv_cum.shape[0]))
    for i in range(ego_cum.shape[0]):
        for j in range(riv_cum.shape[0]):
            margin = riv_total[j] - ego_total[i]           # >0 => ego ahead on time
            resolve = min(max(k_ego[i], k_rival[j]) + 1, n_laps - 1)
            ego_won_exchange = ego_cum[i, :, resolve] < riv_cum[j, :, resolve]
            contested = np.abs(margin) < passing_window_s
            ego_ahead = np.where(contested,
                                 np.where(ego_won_exchange, leader_holds, ~leader_holds),
                                 margin > 0.0)
            win[i, j] = ego_ahead.mean()
    return win


def solve_pit_game(
    win_prob: np.ndarray, ego_laps: tuple[int, ...], rival_laps: tuple[int, ...],
    rival_plan_lap: int,
) -> DuelResult:
    """Solve the game from a payoff matrix: rival best-response, the naive
    optimum (rival keeps its plan) and the Stackelberg optimum (rival covers)."""
    rival_best = win_prob.argmin(axis=1)
    covered = win_prob[np.arange(len(ego_laps)), rival_best]
    j_plan = int(np.argmin([abs(c - rival_plan_lap) for c in rival_laps]))
    i_naive = int(win_prob[:, j_plan].argmax())
    i_adv = int(covered.argmax())
    return DuelResult(
        ego_pit_laps=ego_laps,
        rival_pit_laps=rival_laps,
        win_prob=win_prob,
        rival_best_response=rival_best,
        naive_pit_lap=ego_laps[i_naive],
        naive_win_prob=float(win_prob[i_naive, j_plan]),
        naive_win_prob_if_covered=float(covered[i_naive]),
        adversarial_pit_lap=ego_laps[i_adv],
        adversarial_win_prob=float(covered[i_adv]),
    )


def duel(
    scenario: Scenario,
    rival: RivalSpec,
    model: CircuitModel,
    swap_rate: float,
    n_draws: int = 2000,
    seed: int = 20260712,
    passing_window_s: float = DEFAULT_PASSING_WINDOW_S,
    min_final_stint: int = 3,
) -> DuelResult:
    """Solve the pit-stop game between the ego car and one rival.

    ``swap_rate`` is the circuit's measured adjacent-pair swap rate
    (``track_position.py``); it sets how sticky track position is.
    """
    rng = np.random.default_rng(seed)
    candidates = scenario.candidate_pit_laps(min_final_stint)  # both share the window
    laps = np.arange(scenario.current_lap + 1, scenario.total_laps + 1)
    n_laps = len(laps)

    # One shared realisation for both cars: status timeline, fuel & degradation
    # coefficients (common random numbers); independent lap noise each.
    status = np.stack([_sample_status(model, n_laps, rng, scenario.ongoing)
                       for _ in range(n_draws)])
    fuel = _sample_coef_batch(rng, model.fuel_slope, n_draws)
    deg = {c: tuple(_sample_coef_batch(rng, g, n_draws) for g in coefs)
           for c, coefs in model.degradation.items()}
    ego_noise = rng.normal(0.0, model.lap_noise_s, size=(n_draws, n_laps))
    rival_noise = rng.normal(0.0, model.lap_noise_s, size=(n_draws, n_laps))

    # Cumulative time per candidate pit lap for each car: (n_choices, n_draws, n_laps).
    def cum(noise, compound, age, target):
        return np.stack([
            _car_lap_times(model, laps, status, noise, fuel, deg, compound, age,
                           scenario.current_lap, p, target).cumsum(axis=1)
            for p in candidates
        ])
    ego_cum = cum(ego_noise, scenario.compound, scenario.tyre_age, scenario.target_compound)
    riv_cum = cum(rival_noise, rival.compound, rival.tyre_age, rival.target_compound)
    # A rival ahead by gap_s needs gap_s less time to reach the same track point.
    riv_cum = riv_cum - rival.gap_s

    k = np.array([p - scenario.current_lap - 1 for p in candidates])
    win_prob = win_probability_matrix(ego_cum, riv_cum, k, k, swap_rate,
                                      passing_window_s, rng)
    plan = rival.pit_lap if rival.pit_lap is not None else candidates[-1]
    return solve_pit_game(win_prob, candidates, candidates, plan)


@dataclass(frozen=True)
class MultiStrategyDuel:
    """Duel where the rival also chooses its **tyre compound**, not just its pit
    lap — a strictly richer covering strategy space than :class:`DuelResult`."""

    ego_pit_laps: tuple[int, ...]
    rival_strategies: tuple[tuple[int, str], ...]   # (pit lap, compound) menu
    win_prob: np.ndarray                            # (n_ego, n_rival_strategies)
    naive_pit_lap: int
    naive_win_prob: float                # rival keeps its announced lap+compound
    naive_win_prob_if_covered: float     # rival picks the best (lap, compound)
    rival_cover_strategy: tuple[int, str]  # the covering (lap, compound) it uses
    adversarial_pit_lap: int
    adversarial_win_prob: float

    @property
    def naive_overstatement(self) -> float:
        """Win probability the frozen-rival plan overstates once the rival is free
        to cover with *both* a pit lap and a compound."""
        return self.naive_win_prob - self.naive_win_prob_if_covered


def duel_multi_compound(
    scenario: Scenario,
    rival: RivalSpec,
    model: CircuitModel,
    swap_rate: float,
    n_draws: int = 2000,
    seed: int = 20260712,
    passing_window_s: float = DEFAULT_PASSING_WINDOW_S,
    min_final_stint: int = 3,
) -> MultiStrategyDuel:
    """Solve the pit game giving the rival a **compound choice** on top of its
    pit lap: it covers with whichever ``(lap, compound)`` most hurts the ego car.

    Uses the per-compound degradation the model already measures — no new
    assumption, just a rival that is no longer pinned to one tyre. The headline is
    that a compound-aware cover can raise the naive plan's overstatement above the
    lap-only figure, which is the honest answer to 'the rival reacts too simply'.
    """
    rng = np.random.default_rng(seed)
    candidates = scenario.candidate_pit_laps(min_final_stint)
    compounds = tuple(model.degradation.keys())
    laps = np.arange(scenario.current_lap + 1, scenario.total_laps + 1)
    n_laps = len(laps)

    status = np.stack([_sample_status(model, n_laps, rng, scenario.ongoing)
                       for _ in range(n_draws)])
    fuel = _sample_coef_batch(rng, model.fuel_slope, n_draws)
    deg = {c: tuple(_sample_coef_batch(rng, g, n_draws) for g in coefs)
           for c, coefs in model.degradation.items()}
    ego_noise = rng.normal(0.0, model.lap_noise_s, size=(n_draws, n_laps))
    rival_noise = rng.normal(0.0, model.lap_noise_s, size=(n_draws, n_laps))

    def cum(noise, compound, age, target):
        return np.stack([
            _car_lap_times(model, laps, status, noise, fuel, deg, compound, age,
                           scenario.current_lap, p, target).cumsum(axis=1)
            for p in candidates
        ])

    ego_cum = cum(ego_noise, scenario.compound, scenario.tyre_age, scenario.target_compound)
    riv_cum_all, strategies = [], []
    for comp in compounds:
        riv_cum_all.append(cum(rival_noise, rival.compound, rival.tyre_age, comp) - rival.gap_s)
        strategies.extend((int(p), comp) for p in candidates)
    riv_cum_all = np.concatenate(riv_cum_all, axis=0)

    k_ego = np.array([p - scenario.current_lap - 1 for p in candidates])
    k_riv = np.array([p - scenario.current_lap - 1 for p, _ in strategies])
    win_prob = win_probability_matrix(ego_cum, riv_cum_all, k_ego, k_riv,
                                      swap_rate, passing_window_s, rng)

    plan_lap = rival.pit_lap if rival.pit_lap is not None else candidates[-1]
    plan_comp = rival.target_compound or compounds[0]
    j_plan = min((abs(p - plan_lap), idx) for idx, (p, c) in enumerate(strategies)
                 if c == plan_comp)[1]
    i_naive = int(win_prob[:, j_plan].argmax())
    rival_best = win_prob.argmin(axis=1)
    covered = win_prob[np.arange(len(candidates)), rival_best]
    i_adv = int(covered.argmax())
    return MultiStrategyDuel(
        ego_pit_laps=candidates,
        rival_strategies=tuple(strategies),
        win_prob=win_prob,
        naive_pit_lap=candidates[i_naive],
        naive_win_prob=float(win_prob[i_naive, j_plan]),
        naive_win_prob_if_covered=float(covered[i_naive]),
        rival_cover_strategy=strategies[int(rival_best[i_naive])],
        adversarial_pit_lap=candidates[i_adv],
        adversarial_win_prob=float(covered[i_adv]),
    )
