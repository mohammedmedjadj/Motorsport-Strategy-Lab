"""Endurance modelling scope — the single source of truth for which
circuit-seasons the degradation / CV / simulator work covers, per series.

Kept separate from the *neutralisation* model, which deliberately uses every
available race (see ``safety_car/endurance.py``). Widening the degradation and
simulator coverage is now a one-file edit here: add a circuit or a season and
re-run ``scripts/run_endurance_models.py`` to regenerate the committed model
artifacts. Only circuit-seasons whose laps are materialised under
``data/derived/<series>/`` belong here.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CircuitScope:
    """One circuit's coverage within a series."""

    event: str
    car_class: str
    seasons: tuple[int, ...]


#: series -> circuits, each with its class and the seasons materialised for it.
#: Mosport is single-season on purpose: GTP raced there only in 2023 (verified;
#: see reports/imsa/data_availability_phase0.md). Imola (WEC) starts in 2024:
#: HYPERCAR did not race there before.
ENDURANCE_SCOPE: dict[str, tuple[CircuitScope, ...]] = {
    "imsa": (
        CircuitScope("Watkins Glen", "GTP", (2023, 2024, 2025)),
        CircuitScope("Sebring", "GTP", (2023, 2024, 2025)),
        CircuitScope("Mosport", "GTP", (2023,)),
        CircuitScope("Road America", "GTP", (2023, 2024, 2025)),
    ),
    "wec": (
        CircuitScope("Spa", "HYPERCAR", (2023, 2024, 2025)),
        CircuitScope("Fuji", "HYPERCAR", (2023, 2024, 2025)),
        CircuitScope("Bahrain", "HYPERCAR", (2023, 2024, 2025)),
        CircuitScope("Imola", "HYPERCAR", (2024, 2025)),
    ),
}


def scoped_race_seasons() -> list[tuple[str, str, str, int]]:
    """Flatten the scope to (series, event, car_class, season) tuples."""
    return [
        (series, cs.event, cs.car_class, season)
        for series, circuits in ENDURANCE_SCOPE.items()
        for cs in circuits
        for season in cs.seasons
    ]
