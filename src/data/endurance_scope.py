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


#: Event strings the source uses for the SAME physical circuit, mapped to one
#: canonical name. Built from knowledge of the championship, not from string
#: similarity — the two are different, and the difference matters:
#:
#: - ``Mosport`` and ``Canadian Tire Motorsport Park`` are one track; the
#:   source renamed it in 2026.
#: - ``Watkins Glen``, ``Watkins Glen 240`` and ``Watkins Glen 6 Hours`` are
#:   one track under three event names used in 2021.
#: - ``Belle Isle`` and ``Detroit`` look like the same pattern and are **not**:
#:   IMSA moved from the Belle Isle park circuit to the downtown Detroit
#:   street course in 2023. They stay separate on purpose.
#:
#: This exists because leave-one-circuit-out validation is only meaningful if
#: its folds are independent. Two names for one track would let a model train
#: on Mosport, test on Canadian Tire Motorsport Park, and report the result as
#: generalisation to an unseen circuit — leakage that inflates the headline
#: transfer number instead of failing visibly.
CIRCUIT_ALIASES: dict[str, str] = {
    "Canadian Tire Motorsport Park": "Mosport",
    "Watkins Glen 240": "Watkins Glen",
    "Watkins Glen 6 Hours": "Watkins Glen",
}


def canonical_circuit(event: str) -> str:
    """The canonical circuit name for a source event string."""
    return CIRCUIT_ALIASES.get(event, event)


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
        # --- GT3 (GTD): IMSA's Pro/Am GT class. Scoped as its own class, never
        # pooled with GTP: different cars, different pit procedure, and a
        # mandatory amateur-rated driver. All 60 race-seasons cleared the
        # phase-0 eligibility floor (reports/new_series_survey_phase0.md).
        # Note "Mosport"/"Canadian Tire Motorsport Park" and the three Watkins
        # Glen strings are the source's names for two tracks, resolved by
        # CIRCUIT_ALIASES above -- 16 event strings, 14 circuits.
        CircuitScope("Belle Isle", "GTD", (2022,)),
        CircuitScope("Canadian Tire Motorsport Park", "GTD", (2026,)),
        CircuitScope("Daytona", "GTD", (2021, 2022, 2023, 2024, 2025, 2026)),
        CircuitScope("Indianapolis", "GTD", (2023, 2024, 2025)),
        CircuitScope("Laguna Seca", "GTD", (2021, 2022, 2023, 2024, 2025, 2026)),
        CircuitScope("Lime Rock", "GTD", (2021, 2022, 2023)),
        CircuitScope("Long Beach", "GTD", (2021, 2022, 2023, 2024, 2025, 2026)),
        CircuitScope("Mid-Ohio", "GTD", (2021, 2022)),
        CircuitScope("Mosport", "GTD", (2022, 2023, 2024, 2025)),
        CircuitScope("Road America", "GTD", (2021, 2022, 2023, 2024, 2025)),
        CircuitScope("Road Atlanta", "GTD", (2021, 2022, 2023, 2024, 2025)),
        CircuitScope("Sebring", "GTD", (2021, 2022, 2023, 2024, 2025, 2026)),
        CircuitScope("VIR", "GTD", (2021, 2022, 2023, 2024, 2025)),
        CircuitScope("Watkins Glen", "GTD", (2022, 2023, 2024, 2025, 2026)),
        CircuitScope("Watkins Glen 240", "GTD", (2021,)),
        CircuitScope("Watkins Glen 6 Hours", "GTD", (2021,)),
        # --- GT3 (GTD PRO): the same GT3 cars under the same Balance of
        # Performance as GTD, but entered with all-professional line-ups
        # instead of GTD's mandatory bronze- or silver-rated driver. Scoped
        # separately because that difference is the point: the class boundary
        # *is* the crew rating, which makes the amateur effect measurable
        # like-for-like on the same weekends at the same tracks, with no
        # external rating data. 47 of 47 race-seasons cleared the floor.
        CircuitScope("Canadian Tire Motorsport Park", "GTDPRO", (2026,)),
        CircuitScope("Daytona", "GTDPRO", (2022, 2023, 2024, 2025, 2026)),
        CircuitScope("Detroit", "GTDPRO", (2024, 2025, 2026)),
        CircuitScope("Indianapolis", "GTDPRO", (2023, 2024, 2025)),
        CircuitScope("Laguna Seca", "GTDPRO", (2022, 2023, 2024, 2025, 2026)),
        CircuitScope("Lime Rock", "GTDPRO", (2022, 2023)),
        CircuitScope("Long Beach", "GTDPRO", (2022, 2023)),
        CircuitScope("Mosport", "GTDPRO", (2022, 2023, 2024, 2025)),
        CircuitScope("Road America", "GTDPRO", (2022, 2023, 2024, 2025)),
        CircuitScope("Road Atlanta", "GTDPRO", (2022, 2023, 2024, 2025)),
        CircuitScope("Sebring", "GTDPRO", (2022, 2023, 2024, 2025, 2026)),
        CircuitScope("VIR", "GTDPRO", (2022, 2023, 2024, 2025)),
        CircuitScope("Watkins Glen", "GTDPRO", (2022, 2023, 2024, 2025, 2026)),
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
