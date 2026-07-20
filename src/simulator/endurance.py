"""Endurance strategy simulator (IMSA / WEC).

Same philosophy as the F1 engine — measure every constant from data, propagate
uncertainty, return distributions rather than a single "pit on lap N" — but the
decision problem is different in three ways that drive the design:

1. **Fuel range is a hard constraint.** An F1 car *may* choose not to stop; an
   endurance car cannot. Measured fuel-stint length is ~20 laps (IMSA Watkins
   Glen) and ~23 (WEC Spa), so the candidate set is bounded above by the fuel
   range, not by strategic taste.

2. **Neutralisations are frequent and brutally slow.** The measured FCY pace
   ratio is **2.03** at Watkins Glen and **1.77** at Spa, against ~1.4 for an F1
   safety car. Combined with an IMSA FCY rate of one per ~48 laps, pitting under
   caution is worth far more than in F1, and the simulator must price it.

3. **The stop is expensive and compound-free.** Measured green-flag pit loss is
   ~62 s (F1: 19-27 s) because stops refuel and usually change driver. Tyre
   compound is not in the source at all, so there is no compound choice to model
   — degradation is the single net slope from Phase 1.

Uncertainty propagated per draw: the net degradation slope is resampled from its
Phase 1 confidence interval, the FCY per-lap rate from its Phase 2 Gamma
posterior, and FCY durations from the observed pool. Candidates share
realisations (common random numbers), so P(best) is a clean per-draw argmin —
the same guarantee the F1 engine gives.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.data.endurance_loader import green_lap_times

GREEN, FCY = 0, 1

#: Stops slower than this multiple of the median are not routine (garage
#: repairs, penalties served in the box) and are trimmed before estimating.
PIT_LOSS_TRIM = 2.0


@dataclass(frozen=True)
class EnduranceRaceModel:
    """Everything the endurance engine needs, all measured from one race."""

    series: str
    event: str
    car_class: str
    green_pace_s: float
    lap_noise_s: float
    #: Net within-stint slope (s per lap of tyre age) with its standard error.
    net_slope_s: float
    net_slope_se: float
    pit_loss_s: float
    pit_loss_iqr_s: float
    n_pit_events: int
    #: Median lap time under FCY divided by green pace (>= 1).
    fcy_pace_ratio: float
    #: Gamma posterior for FCY deployments per lap (alpha, exposure).
    fcy_alpha: float
    fcy_exposure: float
    #: Observed FCY durations in laps, resampled per draw.
    fcy_durations: tuple[int, ...]
    #: Hard fuel constraint: maximum laps runnable between pit visits.
    fuel_range_laps: int


def estimate_pit_loss(laps: pd.DataFrame) -> tuple[float, float, int]:
    """Green-flag pit loss (s): in-lap + out-lap minus twice the car's pace.

    Restricted to stops where both the pit lap and the following lap ran green,
    so neutralised stops (which are cheaper by construction) do not contaminate
    the green-flag reference. Returns (median, IQR, n).
    """
    work = laps.sort_values(["car", "lap"], kind="stable").copy()
    baseline = green_lap_times(work).groupby("car")["lap_time_s"].median()
    work["t_next"] = work.groupby("car", sort=False)["lap_time_s"].shift(-1)
    work["flag_next"] = work.groupby("car", sort=False)["flag"].shift(-1)

    stops = work[
        work["is_pit_lap"]
        & work["is_green"]
        & work["flag_next"].eq("GF")
        & work["lap_time_s"].notna()
        & work["t_next"].notna()
    ].copy()
    stops["loss"] = (
        stops["lap_time_s"] + stops["t_next"] - 2.0 * stops["car"].map(baseline)
    )
    losses = stops["loss"].dropna().to_numpy(dtype=float)
    losses = losses[losses > 0]
    if losses.size == 0:
        raise ValueError("no clean green-flag pit stops found")
    losses = losses[losses <= PIT_LOSS_TRIM * np.median(losses)]
    q75, q25 = np.percentile(losses, [75, 25])
    return float(np.median(losses)), float(q75 - q25), int(losses.size)


def estimate_fcy_pace_ratio(laps: pd.DataFrame) -> float:
    """Median FCY lap time divided by median green pace (>= 1)."""
    green = green_lap_times(laps)["lap_time_s"].median()
    neutral = laps.loc[
        laps["flag"].eq("FCY") & ~laps["is_pit_lap"] & laps["lap_time_s"].notna(),
        "lap_time_s",
    ]
    if neutral.empty or not np.isfinite(green) or green <= 0:
        raise ValueError("cannot measure an FCY pace ratio in this race")
    return float(neutral.median() / green)


def estimate_fuel_range(laps: pd.DataFrame, quantile: float = 0.9) -> int:
    """Laps runnable between pit visits, as the high quantile of observed
    fuel stints (the max is contaminated by cars that stopped racing)."""
    work = laps.sort_values(["car", "lap"], kind="stable").copy()
    work["fuel_stint"] = work.groupby("car", sort=False)["is_pit_lap"].cumsum()
    lengths = work.groupby(["car", "fuel_stint"]).size()
    if lengths.empty:
        raise ValueError("no fuel stints observed")
    return int(np.ceil(lengths.quantile(quantile)))


@dataclass(frozen=True)
class EnduranceScenario:
    """Race state at a decision point."""

    current_lap: int
    total_laps: int
    tyre_age: int
    #: Laps already run on the current fuel load.
    laps_since_refuel: int

    def candidate_pit_laps(self, model: EnduranceRaceModel) -> tuple[int, ...]:
        """Feasible next-stop laps: from the next lap until fuel runs out.

        The upper bound is the fuel constraint, not a preference — running dry
        is not a strategy. If the remaining race is shorter than the fuel range,
        finishing without stopping is included as lap 0.
        """
        first = self.current_lap + 1
        laps_left_in_tank = model.fuel_range_laps - self.laps_since_refuel
        last = min(self.current_lap + laps_left_in_tank, self.total_laps)
        if last < first:
            raise ValueError("fuel already exhausted at this decision point")
        candidates = tuple(range(first, last + 1))
        if self.total_laps - self.current_lap <= laps_left_in_tank:
            candidates = (*candidates, 0)  # 0 = run to the flag without stopping
        return candidates


def _sample_status(
    model: EnduranceRaceModel, n_laps: int, n_draws: int, rng: np.random.Generator
) -> np.ndarray:
    """(n_draws, n_laps) green/FCY timelines from the Phase 2 posterior."""
    rate = rng.gamma(model.fcy_alpha, 1.0 / model.fcy_exposure, size=n_draws)
    status = np.full((n_draws, n_laps), GREEN, dtype=np.int8)
    durations = np.asarray(model.fcy_durations, dtype=int)
    for d in range(n_draws):
        lap = 0
        while lap < n_laps:
            if rng.random() < rate[d]:
                span = int(rng.choice(durations))
                status[d, lap : lap + span] = FCY
                lap += span
            else:
                lap += 1
    return status


def simulate(
    scenario: EnduranceScenario,
    model: EnduranceRaceModel,
    n_draws: int = 2000,
    seed: int = 20260712,
) -> pd.DataFrame:
    """Total remaining race time per candidate next-stop lap, over ``n_draws``.

    Returns one row per candidate with the outcome distribution; the caller
    decides how to read it (the project never emits a bare "stop on lap N").
    """
    rng = np.random.default_rng(seed)
    candidates = scenario.candidate_pit_laps(model)
    laps = np.arange(scenario.current_lap + 1, scenario.total_laps + 1)
    n_laps = len(laps)
    if n_laps == 0:
        raise ValueError("race already finished at this decision point")

    status = _sample_status(model, n_laps, n_draws, rng)
    is_green = status == GREEN
    # Shared per-draw realisations: degradation slope and lap noise.
    slope = rng.normal(model.net_slope_s, model.net_slope_se, size=(n_draws, 1))
    noise = rng.normal(0.0, model.lap_noise_s, size=(n_draws, n_laps))
    ratio = np.where(is_green, 1.0, model.fcy_pace_ratio)

    rows = []
    for pit_lap in candidates:
        if pit_lap == 0:
            age = scenario.tyre_age + (laps - scenario.current_lap)
        else:
            before = laps <= pit_lap
            age = np.where(
                before,
                scenario.tyre_age + (laps - scenario.current_lap),
                np.maximum(laps - pit_lap, 0),
            )
        # Degradation and noise apply to green running; a neutralised lap is
        # paced by the field, not by the car's tyres.
        base = model.green_pace_s * ratio
        deg = np.where(is_green, slope * age.astype(float), 0.0)
        total = (base + deg + np.where(is_green, noise, 0.0)).sum(axis=1)
        if pit_lap != 0:
            # A stop under caution is cheaper: the field is slower, so the time
            # surrendered relative to rivals shrinks by the pace ratio.
            k = int(pit_lap - scenario.current_lap - 1)
            total = total + model.pit_loss_s / ratio[:, k]
        rows.append({
            "pit_lap": pit_lap,
            "median_s": float(np.median(total)),
            "mean_s": float(total.mean()),
            "p10_s": float(np.percentile(total, 10)),
            "p90_s": float(np.percentile(total, 90)),
            "_total": total,
        })

    stacked = np.vstack([r.pop("_total") for r in rows])
    best = np.argmin(stacked, axis=0)
    p_best = np.bincount(best, minlength=len(rows)) / stacked.shape[1]
    table = pd.DataFrame(rows)
    table["p_best"] = p_best
    return table.sort_values("pit_lap").reset_index(drop=True)


def build_race_model(
    laps: pd.DataFrame,
    net_slope_s: float,
    net_slope_se: float,
    fcy_alpha: float,
    fcy_exposure: float,
    fcy_durations: tuple[int, ...],
    lap_noise_s: float,
) -> EnduranceRaceModel:
    """Assemble a race model, measuring pit loss / pace ratio / fuel range."""
    pit_loss, pit_iqr, n_events = estimate_pit_loss(laps)
    return EnduranceRaceModel(
        series=str(laps["series"].iloc[0]),
        event=str(laps["event"].iloc[0]),
        car_class=str(laps["car_class"].iloc[0]),
        green_pace_s=float(green_lap_times(laps)["lap_time_s"].median()),
        lap_noise_s=lap_noise_s,
        net_slope_s=net_slope_s,
        net_slope_se=net_slope_se,
        pit_loss_s=pit_loss,
        pit_loss_iqr_s=pit_iqr,
        n_pit_events=n_events,
        fcy_pace_ratio=estimate_fcy_pace_ratio(laps),
        fcy_alpha=fcy_alpha,
        fcy_exposure=fcy_exposure,
        fcy_durations=fcy_durations,
        fuel_range_laps=estimate_fuel_range(laps),
    )
