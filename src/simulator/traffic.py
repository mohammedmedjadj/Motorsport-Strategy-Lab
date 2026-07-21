"""Inter-class traffic cost — endurance's unique racecraft problem.

A Hypercar or GTP prototype does not race in a clean field: it is constantly
lapping slower GT cars, and every one it has to fight past costs it time. No
public-data F1 project models this because F1 is single-class; here it is a
first-order strategic cost, and it is measurable directly from the timing.

## How it is measured (no fabrication)

The trap is lapping: a prototype and the GT it is lapping are nose-to-tail on
the road while a lap apart on the count, so a cumulative-time *rank* is not the
on-track order. The fix is to compare **start/finish crossing times**: a GT that
crosses the line just before a prototype is right ahead of it on the road,
whatever lap either is on. So for each prototype green, non-pit lap we count the
other-class cars that crossed the line in the ``window_s`` seconds before it —
the traffic it is about to deal with — and measure how much slower that lap is
than the prototype's own clean pace.

The signal is clean and monotone (Spa 2024 HYPERCAR: clear-air laps run ~0.6 s
under a car's own median, rising to ~+0.6 s with three GT cars just ahead), so
the cost is reported as a measured per-car penalty, not an assumption.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass

import numpy as np
import pandas as pd

#: Seconds before a prototype's line crossing within which another-class
#: crossing counts as traffic just ahead. A fraction of a lap; a parameter.
DEFAULT_WINDOW_S = 12.0

#: Lap-time deviations outside this band (vs a car's own median) are neutralised
#: laps / errors, not traffic, and are trimmed before measuring.
_DEV_TRIM = (-5.0, 15.0)


@dataclass(frozen=True)
class TrafficCost:
    """Measured inter-class traffic cost for one race."""

    series: str
    circuit: str
    prime_class: str
    clean_air_dev_s: float      # median lap dev with zero other-class cars ahead
    cost_per_car_s: float       # extra seconds per other-class car just ahead
    clear_vs_traffic_s: float   # median(dev | traffic) - median(dev | clear)
    n_prime_laps: int
    n_other_cars: int
    window_s: float


def traffic_exposure(
    field: pd.DataFrame, prime_class: str, window_s: float = DEFAULT_WINDOW_S,
) -> pd.DataFrame:
    """Per prime-class green, non-pit lap: how many other-class cars crossed the
    line just ahead (``traffic``) and how far that lap ran off the car's own
    clean pace (``dev``)."""
    df = field.copy()
    df["is_pit"] = pd.to_numeric(df["pit_time"], errors="coerce").notna()
    df = df.sort_values(["car", "lap"])
    df["cross"] = df.groupby("car")["lap_time"].cumsum()  # S/F crossing time

    other_cross = np.sort(df.loc[df["class"] != prime_class, "cross"].to_numpy())

    def count_ahead(t: float) -> int:
        return bisect.bisect_right(other_cross, t) - bisect.bisect_left(other_cross, t - window_s)

    prime = df[(df["class"] == prime_class) & (df["flags"] == "GF") & ~df["is_pit"]].copy()
    if prime.empty:
        raise ValueError(f"no green {prime_class} laps in this field")
    prime["traffic"] = prime["cross"].map(count_ahead)
    prime["clean"] = prime.groupby("car")["lap_time"].transform("median")
    prime["dev"] = prime["lap_time"] - prime["clean"]
    prime = prime[prime["dev"].between(*_DEV_TRIM)]
    return prime[["car", "lap", "traffic", "dev"]]


def measure_traffic_cost(
    field: pd.DataFrame, series: str, circuit: str, prime_class: str,
    window_s: float = DEFAULT_WINDOW_S,
) -> TrafficCost:
    """Measure the inter-class traffic cost for one race's full field."""
    ex = traffic_exposure(field, prime_class, window_s)
    if (ex["traffic"] == 0).sum() < 20 or (ex["traffic"] > 0).sum() < 20:
        raise ValueError("too few clear or in-traffic laps to measure a cost")
    clean = float(ex.loc[ex["traffic"] == 0, "dev"].median())
    in_traffic = float(ex.loc[ex["traffic"] > 0, "dev"].median())
    slope = float(np.polyfit(ex["traffic"].to_numpy(float), ex["dev"].to_numpy(float), 1)[0])
    return TrafficCost(
        series=series, circuit=circuit, prime_class=prime_class,
        clean_air_dev_s=round(clean, 3),
        cost_per_car_s=round(slope, 3),
        clear_vs_traffic_s=round(in_traffic - clean, 3),
        n_prime_laps=len(ex),
        n_other_cars=int((field["class"] != prime_class).groupby(field["car"]).any().sum()),
        window_s=window_s,
    )
