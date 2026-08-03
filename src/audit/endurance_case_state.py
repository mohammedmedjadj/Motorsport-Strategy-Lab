"""Reconstruct real endurance race states and race models for the per-decision
audit — the endurance analogue of ``src/audit/state.py``.

Endurance's decision unit is different from F1's: there is no compound choice
and no rival gap to track, but there IS a fuel clock (``laps_since_refuel``)
that F1 never has. ``state_at`` mirrors the exact ``fuel_stint`` /
``laps_since_refuel`` recipe ``src/degradation/endurance.py::build_endurance_frame``
uses, so a case's reconstructed state is defined identically to how the model
itself defines it.

``build_case_model`` builds an ``EnduranceRaceModel`` the same way
``scripts/run_multistop.py::_build_model`` does: net degradation slope fit on
this one race, but FCY/SC hazards drawn from the **series-wide** posterior
(``fit_neutralisation_models``, not the per-circuit one) — the convention used
everywhere else in this project an ``EnduranceRaceModel`` is assembled, because
a single circuit-season rarely has enough neutralisation events on its own to
estimate a rate from.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.data.endurance_loader import EnduranceLoader
from src.degradation.endurance import build_endurance_frame, fit_endurance_degradation
from src.safety_car.endurance import (
    extract_events,
    fit_neutralisation_models,
    load_race_flags,
    race_timeline,
)
from src.simulator.endurance import EnduranceRaceModel, build_race_model


@dataclass(frozen=True)
class EnduranceDriverState:
    """One car's situation at the end of a given lap."""

    car: str
    tyre_age: int
    laps_since_refuel: int
    flag: str  # the race-control flag active on this lap, for this car


def load_case_laps(series: str, year: int, event: str, car_class: str) -> pd.DataFrame:
    """Normalised laps for one real race (offline, from the committed CSV)."""
    return EnduranceLoader(series).load_laps(year, event, car_class)


def state_at(laps: pd.DataFrame, car: str, lap: int) -> EnduranceDriverState:
    """Car state at the end of ``lap`` (raises if the lap is missing).

    ``laps_since_refuel`` uses the identical ``fuel_stint``/cumcount recipe as
    ``build_endurance_frame`` — this is not an approximation of the model's
    own fuel clock, it IS the model's own fuel clock, evaluated at one lap.
    """
    work = laps[laps["car"] == car].sort_values("lap", kind="stable").copy()
    if work.empty:
        raise LookupError(f"car {car} has no laps in this race")
    work["fuel_stint"] = work["is_pit_lap"].cumsum()
    work["laps_since_refuel"] = work.groupby("fuel_stint")["lap"].cumcount()
    row = work[work["lap"] == lap]
    if row.empty:
        raise LookupError(f"car {car} has no lap {lap} in this race")
    r = row.iloc[0]
    return EnduranceDriverState(
        car=car,
        tyre_age=int(r["tyre_age"]),
        laps_since_refuel=int(r["laps_since_refuel"]),
        flag=str(r["flag"]),
    )


def pit_stops(laps: pd.DataFrame, car: str) -> list[int]:
    """Laps on which the car made a pit visit, in order."""
    d = laps[(laps["car"] == car) & laps["is_pit_lap"]]
    return sorted(int(lap) for lap in d["lap"])


def race_length(laps: pd.DataFrame, car: str) -> int:
    """The car's own last lap — the race distance it actually completed."""
    d = laps[laps["car"] == car]
    if d.empty:
        raise LookupError(f"car {car} has no laps in this race")
    return int(d["lap"].max())


def build_case_model(series: str, year: int, event: str, car_class: str) -> EnduranceRaceModel:
    """Build the ``EnduranceRaceModel`` for one real race, exactly as
    ``scripts/run_multistop.py::_build_model`` does."""
    laps = load_case_laps(series, year, event, car_class)
    fit = fit_endurance_degradation(build_endurance_frame(laps))
    timeline = race_timeline(load_race_flags())
    events = extract_events(timeline)
    post = {(m.series, m.kind): m for m in fit_neutralisation_models(timeline, events)}
    fcy, sc = post[(series, "FCY")], post[(series, "SC")]
    fcy_dur = tuple(e.duration_laps for e in events if e.series == series and e.kind == "FCY")
    sc_dur = tuple(e.duration_laps for e in events if e.series == series and e.kind == "SC")
    return build_race_model(
        laps, fit.net_slope.value, fit.net_slope.se,
        fcy.n_events + 0.5, fcy.laps_exposure, fcy_dur, fit.rmse_s,
        sc_alpha=sc.n_events + 0.5, sc_exposure=sc.laps_exposure, sc_durations=sc_dur,
    )
