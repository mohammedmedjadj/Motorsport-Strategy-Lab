"""Replay every real first pit stop on the calendar through the simulator.

The F1 decision audit was five races, chosen by hand for how much they had been
argued about. That was the right shape for a Phase 5 gate on a four-circuit
scope, and it stopped being enough the moment the scope reached twenty-six: the
endurance side audits 209 races on a mechanical criterion, and F1 audited five
on a narrative one. A model's agreement with real strategy at Barcelona 2024 is
an anecdote. Its agreement across the calendar is a measurement.

**The criterion is uniform and stated, so nothing is chosen for being
interesting.** For every race with a fitted model, the top ``N_FINISHERS``
classified drivers who made at least one stop are replayed at their **first**
one. The model is asked ``LOOKBACK`` laps before the real stop, given the state
as it actually was, and its recommended lap is compared to what the team did.

This is a **replay, not a forecast.** The decision point is defined relative to
a stop that has already happened, which is what makes the comparison possible
and also what stops it being a prediction claim. The question it answers is
"where does this model disagree with real strategy, and by how much", not
"could it have called the race".

Rivals keep their real, historically observed plans — the standard audit
convention: the decision under study is ours, the rest of the world is as it
was.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.audit.state import (
    compound_after,
    gap_between,
    load_race_laps,
    pit_stops,
    state_at,
)
from src.simulator.artifacts import CircuitModel
from src.simulator.engine import RivalSpec, Scenario, simulate
from src.simulator.recommend import summarise

#: How many classified finishers per race to replay. The top of the field is
#: where strategy is actually contested and where a stop is a decision rather
#: than a consequence of damage or a lap down.
N_FINISHERS = 5

#: Laps before the real stop at which the model is asked. Far enough that the
#: stop is still a live choice, close enough that the state is the one the team
#: was actually looking at.
LOOKBACK = 5

#: A stop earlier than this is a first-lap incident or an unusual strategy the
#: replay cannot represent honestly (the model needs a stint to measure).
MIN_FIRST_STOP_LAP = 8

#: Rivals included: the cars immediately ahead and behind on the decision lap.
N_RIVALS = 2


@dataclass(frozen=True)
class Replay:
    """One real first-stop decision, replayed."""

    slug: str
    season: int
    circuit: str
    driver: str
    finishing_position: int
    decision_lap: int
    real_pit_lap: int
    model_pit_lap: int
    p_best_at_real: float
    p_best_at_model: float
    median_cost_s: float  # model's median race time at the real lap minus at its own
    #: Was the real stop taken while the race was neutralised? A stop under
    #: a Safety Car or VSC costs a fraction of a green-flag one, and the
    #: model is asked five laps earlier — before the neutralisation exists.
    #: It cannot foresee it, so a disagreement here is the model lacking
    #: information rather than the model being wrong about tyres.
    real_stop_neutralised: bool

    @property
    def delta_laps(self) -> int:
        """Model minus reality. Positive = the model would have stayed out."""
        return self.model_pit_lap - self.real_pit_lap


def _finishers(laps: pd.DataFrame, n: int) -> list[tuple[str, int]]:
    """The top ``n`` drivers by position on the final lap they completed.

    Final classification is deliberately not in the derived data — it would let
    a model see the outcome — so the finishing order is reconstructed from the
    last lap each driver ran. A driver who retired is ranked by where they were
    when they stopped, and the position filter then drops them.
    """
    last = laps.sort_values("LapNumber").groupby("Driver").tail(1)
    finished = last[last["LapNumber"] == laps["LapNumber"].max()]
    ranked = finished.sort_values("Position")
    return [
        (str(r["Driver"]), int(r["Position"]))
        for _, r in ranked.head(n).iterrows()
        if pd.notna(r["Position"])
    ]


def _rivals(
    laps: pd.DataFrame, driver: str, lap: int, n: int, compounds: frozenset[str]
) -> tuple[RivalSpec, ...]:
    """The cars immediately ahead and behind on the decision lap.

    A rival on a compound the model does not carry is dropped rather than
    guessed at. The degradation model is fitted on dry compounds only, so a
    rival running INTERMEDIATE in a wet race has no curve — and the engine
    would raise on it. Dropping the rival keeps the replay honest: our own
    decision is still replayable, and the head-to-head probability against that
    particular car simply is not reported.
    """
    on_lap = laps[laps["LapNumber"] == lap].dropna(subset=["Position"])
    if on_lap.empty:
        return ()
    row = on_lap[on_lap["Driver"] == driver]
    if row.empty:
        return ()
    our_position = int(row.iloc[0]["Position"])

    neighbours = (
        on_lap[on_lap["Driver"] != driver]
        .assign(distance=lambda d: (d["Position"] - our_position).abs())
        .nsmallest(n, "distance")
    )
    out: list[RivalSpec] = []
    for _, r in neighbours.iterrows():
        name = str(r["Driver"])
        try:
            them = state_at(laps, name, lap)
            gap = gap_between(laps, name, driver, lap)
        except (LookupError, ValueError):
            continue
        if them.compound not in compounds:
            continue
        stops = [s for s in pit_stops(laps, name) if s > lap]
        plan = stops[0] if stops else None
        target = None
        if plan is not None:
            try:
                target = compound_after(laps, name, plan)
            except LookupError:
                plan = None
            if target is not None and target not in compounds:
                plan, target = None, None
        out.append(
            RivalSpec(
                name=name,
                # Positive means the rival is ahead of us.
                gap_s=gap if int(r["Position"]) < our_position else -abs(gap),
                compound=them.compound,
                tyre_age=them.tyre_age,
                pit_lap=plan,
                target_compound=target,
            )
        )
    return tuple(out)


def replay_race(
    slug: str, model: CircuitModel, *, n_draws: int = 1500, seed: int = 20260712
) -> list[Replay]:
    """Replay every qualifying first stop in one race."""
    season, circuit = slug.split("_", 1)
    laps = load_race_laps(slug)
    total_laps = int(laps["LapNumber"].max())

    out: list[Replay] = []
    for driver, position in _finishers(laps, N_FINISHERS):
        stops = pit_stops(laps, driver)
        if not stops or stops[0] < MIN_FIRST_STOP_LAP:
            continue
        real = stops[0]
        decision = real - LOOKBACK
        if decision < 2:
            continue
        try:
            state = state_at(laps, driver, decision)
            target = compound_after(laps, driver, real)
        except (LookupError, ValueError):
            # ValueError too: a lap can exist with no tyre age recorded, which
            # `state_at` surfaces as a failed int cast. Semantically that is the
            # same thing as a missing lap — there is no usable state — so it is
            # a skip, not a crash that ends an audit over a hundred races.
            continue
        compounds = frozenset(model.degradation)
        if state.compound not in compounds or target not in compounds:
            continue

        scenario = Scenario(
            circuit=circuit,
            current_lap=decision,
            total_laps=total_laps,
            compound=state.compound,
            tyre_age=state.tyre_age,
            target_compound=target,
            rivals=_rivals(laps, driver, decision, N_RIVALS, compounds),
        )
        stop_lap = laps[(laps["Driver"] == driver) & (laps["LapNumber"] == real)]
        neutralised = bool(
            stop_lap["is_non_green"].fillna(False).any()
        ) if "is_non_green" in laps.columns else False

        rec = summarise(scenario, simulate(scenario, model, n_draws=n_draws, seed=seed))
        table = rec.table.set_index("pit_lap")
        if real not in table.index:
            continue

        out.append(
            Replay(
                slug=slug,
                season=int(season),
                circuit=circuit,
                driver=driver,
                finishing_position=position,
                decision_lap=decision,
                real_pit_lap=real,
                model_pit_lap=int(rec.best_lap),
                p_best_at_real=float(table.loc[real, "p_best"]),
                p_best_at_model=float(table.loc[rec.best_lap, "p_best"]),
                median_cost_s=float(
                    table.loc[real, "median_s"] - table.loc[rec.best_lap, "median_s"]
                ),
                real_stop_neutralised=neutralised,
            )
        )
    return out


def to_frame(replays: list[Replay]) -> pd.DataFrame:
    """The audit artifact: one row per replayed decision."""
    return pd.DataFrame(
        [
            {
                "season": r.season,
                "circuit": r.circuit,
                "driver": r.driver,
                "finishing_position": r.finishing_position,
                "decision_lap": r.decision_lap,
                "real_pit_lap": r.real_pit_lap,
                "model_pit_lap": r.model_pit_lap,
                "delta_laps": r.delta_laps,
                "p_best_at_real": round(r.p_best_at_real, 4),
                "p_best_at_model": round(r.p_best_at_model, 4),
                "median_cost_s": round(r.median_cost_s, 2),
                "real_stop_neutralised": r.real_stop_neutralised,
            }
            for r in replays
        ],
        columns=[
            "season", "circuit", "driver", "finishing_position", "decision_lap",
            "real_pit_lap", "model_pit_lap", "delta_laps", "p_best_at_real",
            "p_best_at_model", "median_cost_s", "real_stop_neutralised",
        ],
    )
