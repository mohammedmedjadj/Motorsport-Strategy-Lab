"""One canonical way to assemble an :class:`EnduranceRaceModel` for a real race.

The recipe — fit this race's own degradation slope, but draw the FCY/SC hazards
from the **series-wide** neutralisation posterior — was written out by hand in
five separate places (``scripts/run_multistop.py``, ``src/audit/
endurance_case_state.py``, two test modules and the Kaggle notebook). Five
copies of an eight-line incantation is five chances for them to drift apart,
and a drift here is silent: every copy still runs, they just stop describing
the same model. This module is the single definition they now all call.

Why series-wide hazards: a single circuit-season rarely sees enough
neutralisations to estimate a rate from on its own, so the per-race posterior
would be dominated by its prior. The degradation slope is the opposite case —
it is a property of *this* car, tyre and track, so it is fit per race.

This is the endurance counterpart of ``src/simulator/artifacts.py::
load_circuit_models`` for F1. It deliberately stays series-agnostic in code
while never merging the series in *meaning*: WEC and IMSA each get their own
posterior, their own events and their own model, and nothing here ever pools
them into a single "endurance" fit.
"""

from __future__ import annotations

from functools import lru_cache

import pandas as pd

from src.data.endurance_loader import EnduranceLoader, derived_path
from src.degradation.endurance import build_endurance_frame, fit_endurance_degradation
from src.data.endurance_scope import scoped_race_seasons
from src.safety_car.endurance import (
    extract_events,
    fit_neutralisation_models,
    load_race_flags,
    race_timeline,
)
from src.degradation.robust import t_degrees_of_freedom
from src.simulator.endurance import EnduranceRaceModel, build_race_model


@lru_cache(maxsize=1)
def _neutralisation_posteriors() -> dict[str, tuple]:
    """Series -> (fcy_model, sc_model, fcy_durations, sc_durations).

    Cached because it is the expensive, race-independent half of the recipe:
    it reads every committed flag row across both series and refits the same
    posteriors no matter which race is being modelled.
    """
    timeline = race_timeline(load_race_flags())
    events = extract_events(timeline)
    post = {(m.series, m.kind): m for m in fit_neutralisation_models(timeline, events)}
    out: dict[str, tuple] = {}
    for series in sorted({s for s, _ in post}):
        durations = {
            kind: tuple(
                e.duration_laps for e in events if e.series == series and e.kind == kind
            )
            for kind in ("FCY", "SC")
        }
        out[series] = (
            post[(series, "FCY")], post[(series, "SC")],
            durations["FCY"], durations["SC"],
        )
    return out


def available_races(series: str | None = None) -> pd.DataFrame:
    """Every scoped race whose laps are committed — what can be modelled offline.

    Derived from ``ENDURANCE_SCOPE`` intersected with what is actually on disk,
    **not** from ``available_events.csv``. The two answer different questions
    and conflating them was a real defect:

    - ``available_events.csv`` is a network-derived *scoping aid*: what exists
      upstream and clears the eligibility floor. Its own generator says
      "nothing here is used by a model directly". It enumerates one prototype
      class per series, so it has never known about GTD, GTD PRO, ELMS or
      LMP2 Pro/Am.
    - This function answers what a consumer can actually load right now, which
      is the scope — the thing every model is fitted from.

    Reading the catalogue meant the demo offered 2 of the project's 6 scoped
    classes and no ELMS at all, silently, and would have drifted again at the
    next widening. Deriving from the scope cannot go stale against it by
    construction.

    The ``eligible`` guarantee the catalogue provided is preserved and
    strengthened: a race only enters ``ENDURANCE_SCOPE`` after clearing that
    same floor, and the on-disk check means nothing is offered that cannot be
    loaded.
    """
    rows = [
        {"series": s, "year": year, "event": event, "car_class": car_class}
        for s, event, car_class, year in scoped_race_seasons()
        if derived_path(s, year, event, car_class).exists()
    ]
    races = pd.DataFrame(rows, columns=["series", "year", "event", "car_class"])
    if series is not None:
        races = races[races["series"] == series]
    return races.sort_values(
        ["series", "year", "event", "car_class"], kind="stable"
    ).reset_index(drop=True)


def load_race_laps(series: str, year: int, event: str, car_class: str) -> pd.DataFrame:
    """Normalised laps for one real race (offline, from the committed CSV)."""
    return EnduranceLoader(series).load_laps(year, event, car_class)


def race_distance(series: str, year: int, event: str, car_class: str) -> int:
    """Laps completed by the *median* car of the class.

    Not the winner's lap count: in endurance the leader can finish several
    laps clear of a class that spent time in the garage, and a race distance
    taken from the maximum would over-state how long a typical car ran.
    """
    laps = load_race_laps(series, year, event, car_class)
    return int(laps.groupby("car")["lap"].max().median())


def load_race_model(
    series: str, year: int, event: str, car_class: str
) -> EnduranceRaceModel:
    """Assemble the race model for one real endurance race.

    Raises ``KeyError`` if the series has no fitted neutralisation posterior,
    which means the flag data for it was never ingested — a clearer failure
    than an ``EnduranceRaceModel`` silently built on a default prior.
    """
    posteriors = _neutralisation_posteriors()
    if series not in posteriors:
        raise KeyError(
            f"no neutralisation posterior for series {series!r}; "
            f"have {sorted(posteriors)}"
        )
    fcy, sc, fcy_dur, sc_dur = posteriors[series]
    laps = load_race_laps(series, year, event, car_class)
    fit = fit_endurance_degradation(build_endurance_frame(laps))
    return build_race_model(
        laps, fit.net_slope.value, fit.net_slope.se,
        # +0.5 is the Jeffreys prior's pseudo-count, applied identically to
        # both hazards so IMSA's never-observed Safety Car gets a small
        # positive rate instead of an impossible exact zero.
        fcy.n_events + 0.5, fcy.laps_exposure, fcy_dur, fit.rmse_s,
        sc_alpha=sc.n_events + 0.5, sc_exposure=sc.laps_exposure, sc_durations=sc_dur,
        # Carry the cluster count through as t degrees of freedom, so a race
        # fit on 5 cars produces a visibly wider race-time distribution than
        # one fit on 20 rather than silently the same.
        net_slope_df=t_degrees_of_freedom(fit.net_slope.n_clusters),
    )
