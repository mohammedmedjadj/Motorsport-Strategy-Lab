"""Replay every real first stop in every endurance race, in every class.

The endurance decision audit was three hand-picked cases per series while F1's
had grown to 357 replayed decisions on a uniform criterion. That asymmetry made
the endurance classes look thinner than they are: GTD has 60 race-seasons and
GTD PRO 47, and between them they had six audited decisions chosen for being
interesting.

This is the endurance counterpart of ``src/audit/systematic.py`` and it asks the
same question the same way: for every scoped race with a usable model, the top
``N_CARS`` finishers of the class who made at least one stop are replayed at
their **first** one, with the model asked ``LOOKBACK`` laps earlier.

Two things differ from F1, both forced by the sport rather than chosen:

- **The fuel clock is a hard constraint, not a preference.** The candidate set
  is bounded by the lap the tank runs dry, so a disagreement here is always
  within a feasible window — an endurance model cannot recommend "stay out
  forever" the way the F1 one can.
- **Position comes from lap count, not a Position column.** The source carries
  no running order, so the class winner is the car that completed the most laps
  and the ranking follows from that.

A **replay, not a forecast**: the decision point is defined relative to a stop
that already happened. What it measures is where the model disagrees with real
strategy, and by how much.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.audit.endurance_case_state import (
    load_case_laps,
    pit_stops,
    race_length,
    state_at,
)
from src.simulator.endurance import EnduranceRaceModel, EnduranceScenario, simulate

#: Cars per race to replay, ranked by laps completed. Endurance fields run 7-19
#: cars in a class, so five is a comparable slice to F1's top five of twenty.
N_CARS = 5

#: Laps before the real stop at which the model is asked.
LOOKBACK = 3

#: A first stop earlier than this leaves no stint to measure a state from.
MIN_FIRST_STOP_LAP = 6


@dataclass(frozen=True)
class EnduranceReplay:
    """One real first-stop decision in one endurance race, replayed."""

    series: str
    year: int
    event: str
    car_class: str
    car: str
    rank: int
    decision_lap: int
    real_pit_lap: int
    model_pit_lap: int
    fuel_deadline_lap: int
    p_best_at_real: float
    median_cost_s: float
    real_stop_neutralised: bool

    @property
    def delta_laps(self) -> int:
        """Model minus reality. Positive = the model would have stayed out."""
        return self.model_pit_lap - self.real_pit_lap


def _ranked_cars(laps: pd.DataFrame, n: int) -> list[tuple[str, int]]:
    """Cars by laps completed, best first — the class order as measured."""
    completed = laps.groupby("car")["lap"].max().sort_values(ascending=False)
    return [(str(car), rank) for rank, car in enumerate(completed.head(n).index, 1)]


def replay_race(
    series: str,
    year: int,
    event: str,
    car_class: str,
    model: EnduranceRaceModel,
    *,
    n_draws: int = 1200,
    seed: int = 20260712,
) -> list[EnduranceReplay]:
    """Replay every qualifying first stop in one endurance race."""
    laps = load_case_laps(series, year, event, car_class)

    out: list[EnduranceReplay] = []
    for car, rank in _ranked_cars(laps, N_CARS):
        stops = pit_stops(laps, car)
        if not stops or stops[0] < MIN_FIRST_STOP_LAP:
            continue
        real = stops[0]
        decision = real - LOOKBACK
        if decision < 2:
            continue
        try:
            state = state_at(laps, car, decision)
            total = race_length(laps, car)
        except (LookupError, ValueError):
            continue

        scenario = EnduranceScenario(
            current_lap=decision,
            total_laps=total,
            tyre_age=state.tyre_age,
            laps_since_refuel=state.laps_since_refuel,
        )
        try:
            candidates = scenario.candidate_pit_laps(model)
        except ValueError:
            # "fuel already exhausted at this decision point": the car had run
            # more laps on its fuel load than the model's measured fuel range
            # allows. That is a real disagreement between the fuel model and
            # what the car did, and it is worth knowing — but it is a finding
            # about the fuel range, not a stop decision the simulator can be
            # scored on, so it is skipped here and left to the fuel-limited
            # audit, which is the layer that measures exactly this.
            continue
        if real not in candidates:
            # The real stop is outside the window the fuel clock allows from
            # this state. That is a finding about the fuel model, not a
            # decision the simulator can be scored on, so it is left out
            # rather than counted as a disagreement.
            continue

        table = simulate(scenario, model, n_draws=n_draws, seed=seed)
        table = table.set_index("pit_lap")
        best = int(table["median_s"].idxmin())

        stop_row = laps[(laps["car"] == car) & (laps["lap"] == real)]
        neutralised = bool((~stop_row["is_green"].fillna(True)).any())

        out.append(
            EnduranceReplay(
                series=series, year=year, event=event, car_class=car_class,
                car=car, rank=rank,
                decision_lap=decision,
                real_pit_lap=real,
                model_pit_lap=best,
                fuel_deadline_lap=int(max(candidates)),
                p_best_at_real=float(table.loc[real, "p_best"])
                if "p_best" in table.columns else float("nan"),
                median_cost_s=float(
                    table.loc[real, "median_s"] - table.loc[best, "median_s"]
                ),
                real_stop_neutralised=neutralised,
            )
        )
    return out


def to_frame(replays: list[EnduranceReplay]) -> pd.DataFrame:
    """The audit artifact: one row per replayed endurance decision."""
    return pd.DataFrame(
        [
            {
                "series": r.series,
                "year": r.year,
                "event": r.event,
                "car_class": r.car_class,
                "car": r.car,
                "rank": r.rank,
                "decision_lap": r.decision_lap,
                "real_pit_lap": r.real_pit_lap,
                "model_pit_lap": r.model_pit_lap,
                "delta_laps": r.delta_laps,
                "fuel_deadline_lap": r.fuel_deadline_lap,
                "p_best_at_real": round(r.p_best_at_real, 4)
                if not np.isnan(r.p_best_at_real) else "",
                "median_cost_s": round(r.median_cost_s, 2),
                "real_stop_neutralised": r.real_stop_neutralised,
            }
            for r in replays
        ],
        columns=[
            "series", "year", "event", "car_class", "car", "rank", "decision_lap",
            "real_pit_lap", "model_pit_lap", "delta_laps", "fuel_deadline_lap",
            "p_best_at_real", "median_cost_s", "real_stop_neutralised",
        ],
    )
