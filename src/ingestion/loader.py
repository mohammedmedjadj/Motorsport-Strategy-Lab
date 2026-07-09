"""Thin FastF1 wrapper: load one race session into plain DataFrames.

This is the only module in the ingestion layer that touches the network.
Everything downstream (cleaning, quality reporting) works on the plain
DataFrames returned here, so it can be unit-tested with synthetic data.
"""

from __future__ import annotations

from dataclasses import dataclass

import fastf1
import pandas as pd

from src.ingestion.config import CACHE_DIR, RaceId

_cache_enabled = False


def _ensure_cache() -> None:
    """Enable the FastF1 on-disk cache exactly once per process."""
    global _cache_enabled  # noqa: PLW0603 - simple process-wide latch
    if not _cache_enabled:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        fastf1.Cache.enable_cache(str(CACHE_DIR))
        _cache_enabled = True


@dataclass
class RawRaceData:
    """Unprocessed session data for one race, as plain DataFrames."""

    race: RaceId
    event_name: str
    total_laps: int  # scheduled race distance in laps
    laps: pd.DataFrame
    track_status: pd.DataFrame
    weather: pd.DataFrame


def load_race(race: RaceId) -> RawRaceData:
    """Load one race session (laps, track status, weather; no telemetry).

    Uses the FastF1 cache, so repeated calls after the first download are
    served from disk. Raises whatever FastF1 raises on failure — the caller
    decides whether a missing session is fatal (it is, for the MVP scope,
    since Phase 0 verified all scoped sessions load).
    """
    _ensure_cache()
    session = fastf1.get_session(race.season, race.gp_name, "R")
    session.load(laps=True, telemetry=False, weather=True, messages=True)

    track_status = session.track_status
    if track_status is None:
        track_status = pd.DataFrame(columns=["Time", "Status", "Message"])
    weather = session.weather_data
    if weather is None:
        weather = pd.DataFrame(columns=["Time", "AirTemp", "TrackTemp", "Humidity", "Rainfall"])

    return RawRaceData(
        race=race,
        event_name=str(session.event["EventName"]),
        total_laps=int(session.total_laps),
        laps=pd.DataFrame(session.laps),
        track_status=pd.DataFrame(track_status),
        weather=pd.DataFrame(weather),
    )
