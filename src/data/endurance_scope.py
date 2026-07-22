"""Endurance modelling scope — the single source of truth for which
circuit-seasons the degradation / CV / simulator work covers, per series.

Kept separate from the *neutralisation* model, which deliberately uses every
available race (see ``safety_car/endurance.py``). This scope was **widened from
the original 4+4 hand-picked circuits to every eligible prototype race** the
upstream DuckDB carries (>= 4 cars, >= 40 laps), enumerated and verified by
``scripts/discover_endurance_events.py`` — so the names below are the source's
own event strings, not guessed. Only circuit-seasons whose laps are materialised
under ``data/derived/<series>/`` belong here; ``scripts/materialise_endurance.py``
fills them.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CircuitScope:
    """One circuit's coverage within a series."""

    event: str
    car_class: str
    seasons: tuple[int, ...]


#: series -> circuits, each with its class and the eligible seasons. Generated
#: from the verified availability scan; 24 h / 12 h formats (Le Mans, Daytona,
#: Sebring) are included — they are real races, flagged by their lap count where
#: format matters rather than excluded.
ENDURANCE_SCOPE: dict[str, tuple[CircuitScope, ...]] = {
    "imsa": (
        CircuitScope("Daytona", "GTP", (2023, 2024, 2025, 2026)),
        CircuitScope("Detroit", "GTP", (2024, 2025, 2026)),
        CircuitScope("Indianapolis", "GTP", (2023, 2024, 2025)),
        CircuitScope("Laguna Seca", "GTP", (2023, 2024, 2025, 2026)),
        CircuitScope("Long Beach", "GTP", (2023, 2024, 2025, 2026)),
        CircuitScope("Mosport", "GTP", (2023,)),
        CircuitScope("Road America", "GTP", (2023, 2024, 2025)),
        CircuitScope("Road Atlanta", "GTP", (2023, 2024, 2025)),
        CircuitScope("Sebring", "GTP", (2023, 2024, 2025, 2026)),
        CircuitScope("Watkins Glen", "GTP", (2023, 2024, 2025, 2026)),
    ),
    "wec": (
        CircuitScope("Bahrain", "HYPERCAR", (2022, 2023, 2024, 2025)),
        CircuitScope("COTA", "HYPERCAR", (2024, 2025)),
        CircuitScope("Fuji", "HYPERCAR", (2022, 2023, 2024, 2025)),
        CircuitScope("Imola", "HYPERCAR", (2024, 2025, 2026)),
        CircuitScope("Interlagos", "HYPERCAR", (2024, 2025)),
        CircuitScope("Le Mans", "HYPERCAR", (2022, 2025, 2026)),
        CircuitScope("Losail", "HYPERCAR", (2025,)),
        # 2021 excluded at both: the source carries no race-control flags at all
        # for HYPERCAR that season (100% NaN `flags`, verified directly against
        # the raw materialised laps) — the first Hypercar season, evidently an
        # upstream collection gap, not a modelling choice. Every other season at
        # every other circuit in this scope has full flag coverage.
        CircuitScope("Monza", "HYPERCAR", (2022,)),
        CircuitScope("Portimao", "HYPERCAR", (2023,)),
        CircuitScope("Sebring", "HYPERCAR", (2022, 2023)),
        CircuitScope("Spa", "HYPERCAR", (2022, 2023, 2024, 2025, 2026)),
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
