"""Green-flag pit loss across the whole F1 calendar, from the Kaggle history.

The breadth complement to ``pit_loss.estimate_pit_loss`` (which is exact but only
the four FastF1 circuits). Same definition — ``t_in + t_out - 2 x driver green
median``, green-flanked stops only, stops beyond 2x the median trimmed as
non-routine — but reconstructed from Kaggle ``lap_times`` + ``pit_stops``.

Kaggle has no per-lap Safety-Car flag, so "green-flanked" is enforced by the same
field-wide slow-lap inference the degradation layer uses: a stop whose in- or
out-lap is a field-wide slow lap (a neutralised stop, which is cheap) is dropped,
so only true green-pace pit losses are measured.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.degradation.f1_history import FIELD_SLOW_FACTOR

#: A stop costing more than this multiple of the race's median stop is treated as
#: non-routine (damage, a penalty served in the box) and dropped — mirrors the
#: 2x trim in the FastF1 estimator.
NONROUTINE_FACTOR = 2.0
#: Fewest clean stops a circuit-era needs to report a pit loss.
MIN_STOPS = 5


def _race_pit_loss(race: pd.DataFrame, pit_laps: dict[int, set[int]]) -> list[float]:
    """Clean green-flanked pit losses for one race (list, one per stop)."""
    green_median = race["lap_time_s"].median()
    field_by_lap = race.groupby("lap")["lap_time_s"].median()
    slow_laps = set(field_by_lap.index[field_by_lap > FIELD_SLOW_FACTOR * green_median])

    losses: list[float] = []
    for driver, dg in race.groupby("driverId"):
        stops = pit_laps.get(driver, set())
        if not stops:
            continue
        times = dg.set_index("lap")["lap_time_s"]
        out_laps = {s + 1 for s in stops}
        # driver green pace: exclude in-laps, out-laps and field-wide slow laps.
        green = times[~times.index.isin(stops | out_laps | slow_laps)]
        pace = green.median()
        if pd.isna(pace):
            continue
        for s in stops:
            if s in slow_laps or (s + 1) in slow_laps:       # not green-flanked
                continue
            if s not in times.index or (s + 1) not in times.index:
                continue
            t_in, t_out = times[s], times[s + 1]
            if pd.isna(t_in) or pd.isna(t_out):
                continue
            losses.append(float(t_in + t_out - 2.0 * pace))
    return losses


def estimate_history_pit_loss(laps: pd.DataFrame, pits: pd.DataFrame) -> pd.DataFrame:
    """Per (circuit, era) green-flag pit loss: median, IQR, n clean stops.

    ``laps`` is ``load_f1_lap_history`` output; ``pits`` is the raw Kaggle
    ``pit_stops`` (raceId, driverId, lap)."""
    stops_by_race: dict[int, dict[int, set[int]]] = {}
    for (race_id, driver), grp in pits.groupby(["raceId", "driverId"]):
        stops_by_race.setdefault(race_id, {})[driver] = set(grp["lap"])

    per_race: dict[tuple[str, str], list[float]] = {}
    for (race_id, circuit, era), race in laps.groupby(["raceId", "circuitRef", "era"]):
        losses = _race_pit_loss(race, stops_by_race.get(race_id, {}))
        per_race.setdefault((circuit, era), []).extend(losses)

    rows = []
    for (circuit, era), losses in per_race.items():
        arr = np.array(losses, dtype=float)
        if len(arr):
            arr = arr[arr <= NONROUTINE_FACTOR * np.median(arr)]   # drop non-routine
        if len(arr) < MIN_STOPS:
            continue
        q75, q25 = np.percentile(arr, [75, 25])
        rows.append({"circuit": circuit, "era": era,
                     "pit_loss_median_s": round(float(np.median(arr)), 2),
                     "pit_loss_iqr_s": round(float(q75 - q25), 2),
                     "n_stops": int(len(arr))})
    return (pd.DataFrame(rows)
            .sort_values(["era", "pit_loss_median_s"], ascending=[True, False])
            .reset_index(drop=True))
