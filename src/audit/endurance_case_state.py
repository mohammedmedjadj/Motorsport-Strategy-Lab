"""Reconstruct real endurance race states and race models for the per-decision
audit — the endurance analogue of ``src/audit/state.py``.

Endurance's decision unit is different from F1's: there is no compound choice
and no rival gap to track, but there IS a fuel clock (``laps_since_refuel``)
that F1 never has. ``state_at`` mirrors the exact ``fuel_stint`` /
``laps_since_refuel`` recipe ``src/degradation/endurance.py::build_endurance_frame``
uses, so a case's reconstructed state is defined identically to how the model
itself defines it.

``build_case_model`` is a thin alias for
``src/simulator/endurance_models.py::load_race_model``: net degradation slope
fit on this one race, but FCY/SC hazards drawn from the **series-wide**
posterior. It used to spell that recipe out here, which meant the audit could
drift away from what ``scripts/run_multistop.py`` built for the same race
without either one failing.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.simulator.endurance import EnduranceRaceModel
from src.simulator.endurance_models import load_race_laps, load_race_model


@dataclass(frozen=True)
class EnduranceDriverState:
    """One car's situation at the end of a given lap."""

    car: str
    tyre_age: int
    laps_since_refuel: int
    flag: str  # the race-control flag active on this lap, for this car


def load_case_laps(series: str, year: int, event: str, car_class: str) -> pd.DataFrame:
    """Normalised laps for one real race (offline, from the committed CSV)."""
    return load_race_laps(series, year, event, car_class)


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
    """The ``EnduranceRaceModel`` for one real race.

    Kept as a named entry point because the audit reads better for it, but it
    is deliberately not a second implementation — see the module docstring.
    """
    return load_race_model(series, year, event, car_class)
