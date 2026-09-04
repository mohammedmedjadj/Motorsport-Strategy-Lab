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


def event_matches_request(
    requested_gp: str,
    actual_event_name: str,
    actual_location: str | None = None,
    circuit: str | None = None,
) -> bool:
    """True iff FastF1's fuzzy matching returned the race we asked for.

    FastF1 silently fuzzy-matches event names, and when the requested event does
    not exist in a season it **returns an unrelated one with only a warning**.
    Asking for the 2018 Miami Grand Prix returns the Italian Grand Prix at
    Monza; asking for the cancelled 2020 Monaco Grand Prix returns the same.
    Analysing Monza as Monaco is the failure this exists to prevent.

    The name alone is too crude in the other direction. A Grand Prix can be
    renamed without moving — Mexico ran as the "Mexican Grand Prix" through 2020
    and the "Mexico City Grand Prix" from 2021 — and a substring check rejects
    those legitimate matches. It rejected four real editions here before anyone
    noticed, because they were listed among thirty-one skips under a heading
    that called them cancellations.

    **A rename keeps the location; a substitution changes it.** So a match is
    accepted when the name lines up *or* the resolved location is one this
    circuit is known to report (``CIRCUIT_LOCATIONS``). Miami-to-Monza fails
    both; Mexico City-to-Mexican passes the second.

    The location arguments are optional so existing callers keep working; when
    they are absent the check falls back to the name alone.
    """
    if requested_gp.strip().lower() in actual_event_name.strip().lower():
        return True
    if actual_location is None or circuit is None:
        return False
    from src.ingestion.config import CIRCUIT_LOCATIONS

    known = CIRCUIT_LOCATIONS.get(circuit)
    if not known:
        return False
    return actual_location.strip().casefold() in {
        location.casefold() for location in known
    }


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
    resolved = str(session.event["EventName"])
    location = str(session.event.get("Location", "") or "")
    if not event_matches_request(race.gp_name, resolved, location, race.circuit):
        raise LookupError(
            f"{race.slug}: requested '{race.gp_name}' but FastF1 fuzzy-matched "
            f"'{resolved}' at {location!r}, which is not a location "
            f"{race.circuit} reports — this edition was most likely not held "
            "that season, and FastF1 substituted a different race"
        )
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
