"""Reconstruct real race states from the Phase 1 derived laps.

Everything an audit case needs at a decision point is measured here from
the committed lap data — compounds, tyre ages, cumulative-time gaps and
actual pit laps. No number in an audit case is quoted from memory.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.ingestion.config import F1_DERIVED_DIR


@dataclass(frozen=True)
class DriverState:
    """One driver's situation at the end of a given lap."""

    driver: str
    compound: str
    tyre_age: int
    position: int


def load_race_laps(slug: str) -> pd.DataFrame:
    """Load one race's derived laps (e.g. ``2023_singapore``)."""
    return pd.read_csv(F1_DERIVED_DIR / f"laps_{slug}.csv")


def state_at(laps: pd.DataFrame, driver: str, lap: int) -> DriverState:
    """Driver state at the end of ``lap`` (raises if the lap is missing)."""
    row = laps[(laps["Driver"] == driver) & (laps["LapNumber"] == lap)]
    if row.empty:
        raise LookupError(f"{driver} has no lap {lap} in this race")
    r = row.iloc[0]
    return DriverState(
        driver=driver,
        compound=str(r["Compound"]),
        tyre_age=int(r["TyreLife"]),
        position=int(r["Position"]),
    )


def gap_between(laps: pd.DataFrame, front: str, back: str, lap: int) -> float:
    """Cumulative-time gap (s) at the end of ``lap``; positive = front ahead."""
    t_front = laps[(laps["Driver"] == front) & (laps["LapNumber"] == lap)]["time_s"]
    t_back = laps[(laps["Driver"] == back) & (laps["LapNumber"] == lap)]["time_s"]
    if t_front.empty or t_back.empty:
        raise LookupError(f"missing lap {lap} for {front} or {back}")
    return float(t_back.iloc[0] - t_front.iloc[0])


def pit_stops(laps: pd.DataFrame, driver: str) -> list[int]:
    """Laps on which the driver entered the pits (in-laps)."""
    d = laps[(laps["Driver"] == driver) & (laps["is_in_lap"])]
    return sorted(int(lap) for lap in d["LapNumber"])


def compound_after(laps: pd.DataFrame, driver: str, stop_lap: int) -> str:
    """Compound fitted at a stop = compound of the following out-lap."""
    row = laps[(laps["Driver"] == driver) & (laps["LapNumber"] == stop_lap + 1)]
    if row.empty:
        raise LookupError(f"{driver} has no lap {stop_lap + 1} (post-stop)")
    return str(row.iloc[0]["Compound"])
