"""Monte Carlo strategy engine.

For a given race state, evaluates every candidate pit lap against thousands
of simulated race continuations and returns full outcome distributions.

Uncertainty propagated per draw (nothing is a trusted point value):

- degradation & fuel coefficients resampled from their Phase 2 CIs,
- per-lap SC/VSC hazards resampled from their Phase 3 Gamma posteriors,
- neutralisation durations resampled from observed Phase 3 events,
- lap noise at the Phase 2 cross-validated RMSE.

**Common random numbers**: within one draw, every candidate pit lap is
evaluated under the SAME realisation (status timeline, noise, sampled
coefficients), so P(candidate is best) is a clean per-draw argmin and
candidate comparisons are not polluted by between-scenario noise.

Modelling assumptions (stated, mirrored in the Phase 4 report):

- Laps under SC/VSC run at the measured circuit pace ratio; degradation,
  fuel and noise terms are suppressed during neutralisation (their
  within-neutralisation variation is second-order and common to all cars).
- A stop under SC/VSC costs ``pit_loss * green_pace_ratio`` — the field
  covers less distance while the car transits the pit lane. Field bunching
  behind the safety car (gap resets) is NOT modelled; this is the known
  main simplification of the MVP.
- Red flags are out of scope (Phase 3: too rare to model honestly).
- Tyre age keeps advancing under neutralisation (conservative).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from src.simulator.artifacts import CircuitModel, GaussianCoef

GREEN, SC, VSC = 0, 1, 2


@dataclass(frozen=True)
class RivalSpec:
    """A rival car at the decision point. ``gap_s`` > 0 means it is ahead."""

    name: str
    gap_s: float
    compound: str
    tyre_age: int
    pit_lap: int | None  # planned stop; None = stays out to the end
    target_compound: str | None = None


@dataclass(frozen=True)
class Scenario:
    """Race state at the end of ``current_lap`` (the decision point)."""

    circuit: str
    current_lap: int
    total_laps: int
    compound: str
    tyre_age: int
    target_compound: str
    rivals: tuple[RivalSpec, ...] = field(default_factory=tuple)
    #: A neutralisation already running at the decision point:
    #: (kind "SC"/"VSC", laps already run under it). Its remaining length is
    #: resampled per draw from observed durations conditional on exceeding
    #: the elapsed laps.
    ongoing: tuple[str, int] | None = None
    #: Adds a "no further stop" pseudo-candidate (pit_lap 0 in outputs) —
    #: required to audit races where staying out was the real strategy.
    include_no_stop: bool = False

    def candidate_pit_laps(self, min_final_stint: int = 3) -> tuple[int, ...]:
        """Feasible pit laps: from next lap to race end minus a minimal stint."""
        first = self.current_lap + 1
        last = self.total_laps - min_final_stint
        if last < first:
            raise ValueError("no feasible pit window in this scenario")
        return tuple(range(first, last + 1))


@dataclass(frozen=True)
class SimulationResult:
    """Raw per-draw outcomes for each candidate pit lap."""

    candidates: tuple[int, ...]
    our_time: np.ndarray  # shape (n_candidates, n_draws)
    ahead_of_rival: dict[str, np.ndarray]  # rival -> bool (n_candidates, n_draws)

    @property
    def p_best(self) -> np.ndarray:
        """P(candidate minimises total time), by per-draw argmin."""
        best = np.argmin(self.our_time, axis=0)
        return np.bincount(best, minlength=len(self.candidates)) / self.our_time.shape[1]


def _sample_coef(rng: np.random.Generator, coef: GaussianCoef) -> float:
    return float(rng.normal(coef.mean, coef.sd)) if coef.sd > 0 else coef.mean


def _sample_status(
    model: CircuitModel,
    n_laps: int,
    rng: np.random.Generator,
    ongoing: tuple[str, int] | None = None,
) -> np.ndarray:
    """Per-lap status timeline from resampled hazards and duration pools."""
    lam_sc = rng.gamma(model.sc_hazard.alpha, 1.0 / model.sc_hazard.beta)
    lam_vsc = rng.gamma(model.vsc_hazard.alpha, 1.0 / model.vsc_hazard.beta)
    status = np.full(n_laps, GREEN, dtype=np.int8)
    lap = 0
    if ongoing is not None:
        kind, elapsed = ongoing
        pool = model.sc_durations if kind == "SC" else model.vsc_durations
        code = SC if kind == "SC" else VSC
        longer = [d for d in pool if d > elapsed]
        remaining = (int(rng.choice(longer)) - elapsed) if longer else 1
        remaining = min(max(remaining, 1), n_laps)
        status[:remaining] = code
        lap = remaining
    while lap < n_laps:
        u = rng.random()
        if u < lam_sc:
            duration = int(rng.choice(model.sc_durations))
            status[lap : lap + duration] = SC
            lap += duration
        elif u < lam_sc + lam_vsc:
            duration = int(rng.choice(model.vsc_durations))
            status[lap : lap + duration] = VSC
            lap += duration
        else:
            lap += 1
    return status


def _poly(coefs: tuple[float, ...], age: np.ndarray) -> np.ndarray:
    out = np.zeros_like(age, dtype=float)
    for power, c in enumerate(coefs, start=1):
        out += c * age**power
    return out


def _car_times(
    model: CircuitModel,
    scenario_laps: np.ndarray,
    status: np.ndarray,
    noise: np.ndarray,
    fuel: float,
    deg: dict[str, tuple[float, ...]],
    start_compound: str,
    start_age: int,
    current_lap: int,
    pit_lap: int | None,
    target_compound: str | None,
    pit_loss_s: float,
) -> float:
    """Total remaining time for one car under one realisation."""
    green = status == GREEN
    ratio = np.where(
        status == SC, model.pace_ratios.sc_ratio,
        np.where(status == VSC, model.pace_ratios.vsc_ratio, 1.0),
    )
    base = np.where(
        green,
        model.green_pace_s + fuel * scenario_laps + noise,
        model.green_pace_s * ratio,
    )
    old_age = start_age + (scenario_laps - current_lap)
    deg_total = np.where(green, _poly(deg[start_compound], old_age.astype(float)), 0.0)
    total = float(base.sum())
    if pit_lap is None:
        return total + float(deg_total.sum())

    k = int(pit_lap - current_lap - 1)  # index of the in-lap
    new_age = (scenario_laps - pit_lap).astype(float)
    new_compound = target_compound or start_compound
    deg_new = np.where(green, _poly(deg[new_compound], np.maximum(new_age, 0.0)), 0.0)
    total += float(deg_total[: k + 1].sum()) + float(deg_new[k + 1 :].sum())
    # A stop under neutralisation is cheaper by the measured pace ratio.
    total += pit_loss_s / float(ratio[k])
    return total


def simulate(
    scenario: Scenario,
    model: CircuitModel,
    n_draws: int = 5000,
    seed: int = 20260712,
    min_final_stint: int = 3,
) -> SimulationResult:
    """Evaluate every candidate pit lap over ``n_draws`` shared realisations."""
    rng = np.random.default_rng(seed)
    candidates = scenario.candidate_pit_laps(min_final_stint)
    if scenario.include_no_stop:
        candidates = (*candidates, 0)  # 0 = stay out to the end
    laps = np.arange(scenario.current_lap + 1, scenario.total_laps + 1)
    n_laps = len(laps)

    our = np.empty((len(candidates), n_draws), dtype=float)
    ahead = {r.name: np.empty((len(candidates), n_draws), dtype=bool)
             for r in scenario.rivals}

    for d in range(n_draws):
        status = _sample_status(model, n_laps, rng, scenario.ongoing)
        fuel = _sample_coef(rng, model.fuel_slope)
        deg = {
            c: tuple(_sample_coef(rng, g) for g in coefs)
            for c, coefs in model.degradation.items()
        }
        our_noise = rng.normal(0.0, model.lap_noise_s, n_laps)
        rival_times: dict[str, float] = {}
        for rival in scenario.rivals:
            rival_times[rival.name] = _car_times(
                model, laps, status, rng.normal(0.0, model.lap_noise_s, n_laps),
                fuel, deg, rival.compound, rival.tyre_age, scenario.current_lap,
                rival.pit_lap, rival.target_compound, model.pit_loss.median_s,
            ) - rival.gap_s  # a rival ahead by g effectively finishes g sooner

        for i, pit_lap in enumerate(candidates):
            t = _car_times(
                model, laps, status, our_noise, fuel, deg,
                scenario.compound, scenario.tyre_age, scenario.current_lap,
                pit_lap if pit_lap > 0 else None,
                scenario.target_compound, model.pit_loss.median_s,
            )
            our[i, d] = t
            for rival in scenario.rivals:
                ahead[rival.name][i, d] = t < rival_times[rival.name]

    return SimulationResult(candidates=candidates, our_time=our, ahead_of_rival=ahead)
