"""Build the Phase 2 modelling dataset from the derived Phase 1 CSVs.

Selection is deliberately strict — degradation modelling needs clean pace
laps in stints long enough to show a trend:

- pace laps only (``is_pace_lap`` from Phase 1),
- dry compounds only (SOFT/MEDIUM/HARD),
- gross traffic outliers trimmed (lap slower than 1.10x the driver's own
  race median — backmarkers crawling behind traffic, not tyre behaviour),
- stints with fewer than 5 surviving laps dropped (no trend information).

Every filter's row count is returned so the Phase 2 report can account for
what was excluded, mirroring the Phase 1 accounting discipline.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.ingestion.config import F1_DERIVED_DIR, SEASONS

DRY_COMPOUNDS: tuple[str, ...] = ("SOFT", "MEDIUM", "HARD")
TRAFFIC_TRIM_FACTOR = 1.10
MIN_STINT_PACE_LAPS = 5


@dataclass(frozen=True)
class FrameDiagnostics:
    """Row accounting for the modelling-frame filters."""

    circuit: str
    pace_laps_in: int
    after_compound_filter: int
    after_traffic_trim: int
    after_min_stint: int
    n_stints: int
    n_driver_races: int


def load_circuit_laps(circuit: str, seasons: tuple[int, ...] = SEASONS) -> pd.DataFrame:
    """Concatenate the derived lap files for one circuit across seasons."""
    frames = []
    for season in seasons:
        df = pd.read_csv(F1_DERIVED_DIR / f"laps_{season}_{circuit}.csv")
        df["race"] = f"{season}_{circuit}"
        df["season"] = season
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def build_modelling_frame(
    laps: pd.DataFrame, circuit: str
) -> tuple[pd.DataFrame, FrameDiagnostics]:
    """Filter one circuit's laps down to the degradation-modelling frame."""
    df = laps[laps["is_pace_lap"]].copy()
    pace_in = len(df)

    df = df[df["Compound"].isin(DRY_COMPOUNDS)]
    df = df.dropna(subset=["lap_time_s", "TyreLife", "LapNumber", "Stint"])
    after_compound = len(df)

    df["driver_race"] = df["race"] + "_" + df["Driver"]
    df["stint_id"] = df["driver_race"] + "_S" + df["Stint"].astype(int).astype(str)

    median = df.groupby("driver_race")["lap_time_s"].transform("median")
    df = df[df["lap_time_s"] <= TRAFFIC_TRIM_FACTOR * median]
    after_trim = len(df)

    stint_size = df.groupby("stint_id")["lap_time_s"].transform("size")
    df = df[stint_size >= MIN_STINT_PACE_LAPS]
    df = df.reset_index(drop=True)

    diag = FrameDiagnostics(
        circuit=circuit,
        pace_laps_in=pace_in,
        after_compound_filter=after_compound,
        after_traffic_trim=after_trim,
        after_min_stint=len(df),
        n_stints=df["stint_id"].nunique(),
        n_driver_races=df["driver_race"].nunique(),
    )
    return df, diag
