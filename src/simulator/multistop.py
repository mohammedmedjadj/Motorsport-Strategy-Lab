"""Multi-stop strategy for a full endurance race.

The single-next-stop engine (:mod:`src.simulator.endurance`) answers "when is
the next stop?"; a 6-24 h race needs the *whole sequence* — 4-6 stops bounded by
a hard fuel range, traded off against tyre degradation and the chance a
neutralisation makes a stop cheap. This module adds that, reusing the same
measured race model and hazard sampling rather than a parallel one.

Two layers, deliberately separated:

- **The deterministic optimum** (:func:`optimal_stop_plan`) — an exact dynamic
  program over stint lengths. Its only inputs are the measured green pace, net
  degradation slope, pit loss and fuel range. With a flat slope it minimises
  stops (fuel-max stints); with a steep slope it trades extra stops for fresher
  tyres. The DP finds the exact balance, not a heuristic.
- **The stochastic evaluation** (:func:`evaluate_plan`) — that plan run through
  the same per-draw neutralisation timeline as the single-stop engine, so a stop
  that happens to fall under a Full Course Yellow or Safety Car is priced
  cheaper, and the output is a race-time *distribution*, never a bare number.

**Traffic** (:class:`TrafficModel`, optional) enters here as *calibrated
variance, not a bias*. The engine's green pace is the observed pace, so the
average cost of lapping traffic is already baked into it; adding a positive
per-lap tax would double-count. What the multi-class field measurement adds that
green pace cannot is how much a race's traffic *varies* — the cross-season SD
per circuit (`endurance_traffic_stability.csv`). We inject that as a zero-mean
per-race random effect, widening the P10-P90 band at a traffic-volatile circuit
(Spa, ±0.29 s/lap) more than a stable one (Fuji, ±0.05), without shifting the
median. Because it is zero-mean and strategy-independent, it does not bias which
plan wins — a correctness property, stated rather than hidden: honestly
representing traffic's effect on a *stop-timing* decision would need a
multi-class field-position model this two-car abstraction deliberately omits.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.simulator.endurance import FCY, GREEN, SC, EnduranceRaceModel, _sample_status


@dataclass(frozen=True)
class TrafficModel:
    """Per-circuit traffic-cost spread, from ``endurance_traffic_stability.csv``.

    Only the SD is used: the mean is already inside the model's green pace (see
    the module docstring), so traffic contributes variance, not a shift."""

    clear_vs_traffic_sd_s: float


@dataclass(frozen=True)
class StopPlan:
    """A full-race stop sequence and its deterministic (expected-pace) time."""

    stop_laps: tuple[int, ...]        # laps after which the car pits
    stint_lengths: tuple[int, ...]    # green laps per stint, sums to race_laps
    deterministic_time_s: float

    @property
    def n_stops(self) -> int:
        return len(self.stop_laps)


def _stint_time(length: int, green_pace_s: float, net_slope_s: float) -> float:
    """Running time of one stint of ``length`` laps on fresh tyres (ages
    0..length-1), degradation applied lap by lap: sum of an arithmetic series."""
    return length * green_pace_s + net_slope_s * (length * (length - 1) / 2.0)


def optimal_stop_plan(
    race_laps: int,
    green_pace_s: float,
    net_slope_s: float,
    pit_loss_s: float,
    fuel_range_laps: int,
) -> StopPlan:
    """Exact minimum-time stop sequence for a full race, by dynamic programming.

    Minimises total green running time + degradation + ``n_stops * pit_loss``
    over every partition of ``race_laps`` into stints each no longer than
    ``fuel_range_laps`` (the hard tank constraint). ``O(race_laps * fuel_range)``.
    """
    if race_laps <= 0:
        raise ValueError("race_laps must be positive")
    if fuel_range_laps <= 0:
        raise ValueError("fuel_range_laps must be positive")

    best_time = [np.inf] * (race_laps + 1)
    best_len = [0] * (race_laps + 1)
    best_time[0] = 0.0
    for r in range(1, race_laps + 1):
        for length in range(1, min(r, fuel_range_laps) + 1):
            # A stint that finishes the race needs no pit after it.
            pit = pit_loss_s if length < r else 0.0
            cand = _stint_time(length, green_pace_s, net_slope_s) + pit + best_time[r - length]
            if cand < best_time[r]:
                best_time[r] = cand
                best_len[r] = length

    lengths: list[int] = []
    r = race_laps
    while r > 0:
        lengths.append(best_len[r])
        r -= best_len[r]
    lengths.reverse()

    stops = tuple(int(s) for s in np.cumsum(lengths)[:-1])  # drop the finish line
    return StopPlan(stop_laps=stops, stint_lengths=tuple(lengths),
                    deterministic_time_s=float(best_time[race_laps]))


def _age_from_stops(race_laps: int, stop_laps: tuple[int, ...]) -> np.ndarray:
    """Tyre age (laps since the last stop) for each lap 1..race_laps, given the
    stops. Fresh tyres are fitted at each stop, so age resets to 0 the lap after."""
    age = np.empty(race_laps, dtype=float)
    last_stop = 0
    stop_set = set(stop_laps)
    for i in range(1, race_laps + 1):
        age[i - 1] = i - 1 - last_stop
        if i in stop_set:
            last_stop = i
    return age


def evaluate_plan(
    plan: StopPlan,
    race_laps: int,
    model: EnduranceRaceModel,
    n_draws: int = 2000,
    seed: int = 20260721,
    traffic: TrafficModel | None = None,
) -> dict[str, float]:
    """Race-time distribution for a fixed stop plan under stochastic
    neutralisations (and optional traffic variance). Same lap-time model as the
    single-stop engine: degradation and noise on green laps, a neutralised lap
    paced by the field, a stop under caution discounted by the pace ratio."""
    rng = np.random.default_rng(seed)
    status = _sample_status(model, race_laps, n_draws, rng)
    is_green = status == GREEN
    ratio = np.where(status == FCY, model.fcy_pace_ratio,
                     np.where(status == SC, model.sc_pace_ratio, 1.0))
    slope = rng.normal(model.net_slope_s, model.net_slope_se, size=(n_draws, 1))
    noise = rng.normal(0.0, model.lap_noise_s, size=(n_draws, race_laps))
    age = _age_from_stops(race_laps, plan.stop_laps)

    base = model.green_pace_s * ratio
    deg = np.where(is_green, slope * age, 0.0)
    per_lap = base + deg + np.where(is_green, noise, 0.0)

    if traffic is not None and traffic.clear_vs_traffic_sd_s > 0:
        # Zero-mean per-race traffic condition (see module docstring): one draw
        # of "how heavy was traffic this race", applied to green laps only.
        traffic_dev = rng.normal(0.0, traffic.clear_vs_traffic_sd_s, size=(n_draws, 1))
        per_lap = per_lap + np.where(is_green, traffic_dev, 0.0)

    total = per_lap.sum(axis=1)
    for s in plan.stop_laps:
        total = total + model.pit_loss_s / ratio[:, s - 1]

    return {
        "n_stops": plan.n_stops,
        "median_s": float(np.median(total)),
        "mean_s": float(total.mean()),
        "p10_s": float(np.percentile(total, 10)),
        "p90_s": float(np.percentile(total, 90)),
        "_total": total,
    }


def _plan_from_lengths(lengths: tuple[int, ...]) -> StopPlan:
    """A hand-built plan (for comparison against the optimum), time left at 0."""
    stops = tuple(int(s) for s in np.cumsum(lengths)[:-1])
    return StopPlan(stop_laps=stops, stint_lengths=tuple(lengths),
                    deterministic_time_s=0.0)


def min_stops_plan(race_laps: int, fuel_range_laps: int) -> StopPlan:
    """The fewest-stops plan: fuel-max stints, a shorter final one. The natural
    naive baseline the optimum is measured against."""
    lengths = []
    left = race_laps
    while left > fuel_range_laps:
        lengths.append(fuel_range_laps)
        left -= fuel_range_laps
    lengths.append(left)
    return _plan_from_lengths(tuple(lengths))
