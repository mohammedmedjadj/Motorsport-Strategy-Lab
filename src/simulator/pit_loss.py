"""Data-derived pit-loss and neutralisation pace ratios.

No invented constants: everything here is measured from the Phase 1
derived laps.

- **Pit loss** (s): for every green-flag pit event (in-lap and the
  following out-lap both run under status "1"), loss =
  ``t_in + t_out - 2 x driver's median green pace that race``. This
  includes the pit-lane transit and the stationary time — the full
  strategic cost of a stop under green.
- **Pace ratios**: median lap time under SC (status contains "4") or VSC
  (contains "6"/"7"), divided by the median green pace lap of the same
  circuit. Used both to slow simulated laps under neutralisation and to
  discount the pit loss of a stop made under it (the field covers less
  distance while you transit the pit lane).

Circuits with no observed VSC laps in the derived window fall back to the
pooled cross-circuit ratio — flagged in the returned diagnostics, never
silent.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PitLossEstimate:
    """Green-flag pit loss for one circuit."""

    circuit: str
    median_s: float
    iqr_s: float
    n_events: int


@dataclass(frozen=True)
class PaceRatios:
    """Neutralisation pace ratios (>= 1) relative to green running."""

    circuit: str
    sc_ratio: float
    vsc_ratio: float
    n_sc_laps: int
    n_vsc_laps: int
    used_pooled_sc: bool
    used_pooled_vsc: bool


def _status_series(laps: pd.DataFrame) -> pd.Series:
    return laps["TrackStatus"].fillna("").astype(str)


def green_median_pace(laps: pd.DataFrame) -> float:
    """Median pace-lap time (s) — the circuit's green-flag reference."""
    return float(laps.loc[laps["is_pace_lap"], "lap_time_s"].median())


def estimate_pit_loss(laps: pd.DataFrame, circuit: str) -> PitLossEstimate:
    """Measure green-flag pit loss from in/out lap pairs."""
    df = laps.copy()
    status = _status_series(df)
    green = status == "1"
    losses: list[float] = []

    for (race, driver), group in df.groupby(["race", "Driver"]):
        group = group.sort_values("LapNumber")
        pace = group.loc[group["is_pace_lap"], "lap_time_s"].median()
        if pd.isna(pace):
            continue
        by_lap = group.set_index("LapNumber")
        in_laps = group.loc[group["is_in_lap"] & green.loc[group.index], "LapNumber"]
        for lap_no in in_laps:
            out_no = lap_no + 1
            if out_no not in by_lap.index:
                continue
            out_row = by_lap.loc[out_no]
            if not bool(out_row["is_out_lap"]):
                continue
            if str(out_row["TrackStatus"]) != "1":
                continue
            t_in, t_out = by_lap.loc[lap_no, "lap_time_s"], out_row["lap_time_s"]
            if pd.isna(t_in) or pd.isna(t_out):
                continue
            losses.append(float(t_in + t_out - 2.0 * pace))

    arr = np.array(losses, dtype=float)
    # Trim clearly non-routine stops (damage, penalties served in the box):
    # anything beyond 2x the median loss is not a normal stop.
    if len(arr):
        arr = arr[arr <= 2.0 * np.median(arr)]
    if len(arr) == 0:
        raise ValueError(f"{circuit}: no clean green-flag pit events found")
    q75, q25 = np.percentile(arr, [75, 25])
    return PitLossEstimate(
        circuit=circuit,
        median_s=float(np.median(arr)),
        iqr_s=float(q75 - q25),
        n_events=len(arr),
    )


def _ratio(laps: pd.DataFrame, mask: pd.Series, green_pace: float) -> tuple[float, int]:
    """Median lap-time ratio vs green pace for laps matching ``mask``."""
    clean = mask & ~laps["is_in_lap"] & ~laps["is_out_lap"] & laps["lap_time_s"].notna()
    n = int(clean.sum())
    if n == 0:
        return float("nan"), 0
    return float(laps.loc[clean, "lap_time_s"].median() / green_pace), n


def estimate_pace_ratios(
    laps_by_circuit: dict[str, pd.DataFrame]
) -> dict[str, PaceRatios]:
    """Per-circuit SC/VSC pace ratios with pooled fallback."""
    raw: dict[str, dict[str, tuple[float, int]]] = {}
    for circuit, laps in laps_by_circuit.items():
        status = _status_series(laps)
        pace = green_median_pace(laps)
        raw[circuit] = {
            "sc": _ratio(laps, status.str.contains("4", regex=False), pace),
            "vsc": _ratio(laps, status.str.contains("6|7", regex=True), pace),
        }

    def pooled(kind: str) -> float:
        vals = [(r, n) for c in raw.values() for r, n in [c[kind]] if n > 0]
        if not vals:
            raise ValueError(f"no {kind.upper()} laps observed anywhere in the data")
        weights = np.array([n for _, n in vals], dtype=float)
        return float(np.average([r for r, _ in vals], weights=weights))

    pooled_sc, pooled_vsc = pooled("sc"), pooled("vsc")
    out: dict[str, PaceRatios] = {}
    for circuit, ratios in raw.items():
        sc_r, n_sc = ratios["sc"]
        vsc_r, n_vsc = ratios["vsc"]
        out[circuit] = PaceRatios(
            circuit=circuit,
            sc_ratio=sc_r if n_sc > 0 else pooled_sc,
            vsc_ratio=vsc_r if n_vsc > 0 else pooled_vsc,
            n_sc_laps=n_sc,
            n_vsc_laps=n_vsc,
            used_pooled_sc=n_sc == 0,
            used_pooled_vsc=n_vsc == 0,
        )
    return out
