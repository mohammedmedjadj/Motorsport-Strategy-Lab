"""Extract SC/VSC/red-flag events from raw session data.

Input is the raw ``TrackStatus`` change log (one row per status *change*,
where a status string concatenates simultaneous codes, e.g. ``"24"`` =
yellow + safety car) plus the lap data needed to convert session times
into race lap numbers.

Every extracted event keeps its deployment lap and duration so the Phase 3
report can list raw events verbatim — the audit trail matters more than
the aggregates with samples this small.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd

from src.ingestion.loader import RawRaceData

#: Status-code predicates per event kind. VSC has a dedicated "ending" code
#: (7) that still belongs to the VSC period.
KIND_PREDICATES: dict[str, Callable[[str], bool]] = {
    "SC": lambda s: "4" in s,
    "VSC": lambda s: "6" in s or "7" in s,
    "RED": lambda s: "5" in s,
}


@dataclass(frozen=True)
class TrackEvent:
    """One SC, VSC or red-flag period, mapped to race laps."""

    kind: str
    start_lap: int
    end_lap: int
    start_time_s: float

    @property
    def duration_laps(self) -> int:
        return self.end_lap - self.start_lap + 1


@dataclass(frozen=True)
class RaceEvents:
    """All extracted events for one race."""

    circuit: str
    season: int
    laps_completed: int
    events: tuple[TrackEvent, ...]

    def count(self, kind: str) -> int:
        return sum(1 for e in self.events if e.kind == kind)

    def deployment_laps(self, kind: str) -> list[int]:
        return [e.start_lap for e in self.events if e.kind == kind]


def extract_periods(
    track_status: pd.DataFrame, predicate: Callable[[str], bool], session_end_s: float
) -> list[tuple[float, float]]:
    """Return (start_s, end_s) for each maximal period where the predicate holds.

    A period still active at the last status row is closed at
    ``session_end_s`` (an open period is real, not missing data).
    """
    if track_status.empty:
        return []
    ts = track_status.dropna(subset=["Time"]).sort_values("Time")
    times = ts["Time"].dt.total_seconds().to_numpy()
    active = ts["Status"].fillna("").astype(str).map(predicate).to_numpy()

    periods: list[tuple[float, float]] = []
    start: float | None = None
    for t, a in zip(times, active):
        if a and start is None:
            start = t
        elif not a and start is not None:
            periods.append((start, t))
            start = None
    if start is not None:
        periods.append((start, session_end_s))
    return periods


def lap_start_boundaries(laps: pd.DataFrame) -> np.ndarray:
    """Session time (s) at which each race lap begins, indexed by lap-1.

    Lap N is considered to begin when the FIRST driver starts it (the field
    spreads over a lap; the leader defines race-lap timing).
    """
    starts = (
        laps.dropna(subset=["LapStartTime"])
        .groupby("LapNumber")["LapStartTime"]
        .min()
        .dt.total_seconds()
        .sort_index()
    )
    return starts.to_numpy()


def time_to_lap(time_s: float, boundaries: np.ndarray) -> int:
    """Race lap containing a session time (1-based, clipped to race bounds)."""
    lap = int(np.searchsorted(boundaries, time_s, side="right"))
    return max(1, min(lap, len(boundaries)))


def extract_race_events(raw: RawRaceData) -> RaceEvents:
    """Extract all SC/VSC/red periods for one race, mapped to laps."""
    boundaries = lap_start_boundaries(raw.laps)
    lap_ends = raw.laps.dropna(subset=["Time"])["Time"].dt.total_seconds()
    session_end_s = float(lap_ends.max()) if len(lap_ends) else float("inf")

    events: list[TrackEvent] = []
    for kind, predicate in KIND_PREDICATES.items():
        for start_s, end_s in extract_periods(raw.track_status, predicate, session_end_s):
            events.append(
                TrackEvent(
                    kind=kind,
                    start_lap=time_to_lap(start_s, boundaries),
                    end_lap=time_to_lap(end_s, boundaries),
                    start_time_s=start_s,
                )
            )
    events.sort(key=lambda e: e.start_time_s)
    return RaceEvents(
        circuit=raw.race.circuit,
        season=raw.race.season,
        laps_completed=int(raw.laps["LapNumber"].max()),
        events=tuple(events),
    )
