"""Reconstruct real endurance race states from the committed derived laps, for a
retrospective audit of the multi-stop finding.

The headline endurance result is that every scoped race is **fuel-limited on stop
count** (the DP never takes more stops than the fuel minimum). The honest test of
that is not another model run but **what the winners actually did**: if real
race-winning cars ran stints near the full fuel range, their behaviour
corroborates the model; if they short-filled deliberately for tyres, it refutes
it. Every number here is measured from the committed laps, none quoted.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.ingestion.config import DERIVED_DIR


def load_endurance_laps(series: str, slug: str) -> pd.DataFrame:
    """Load one race's committed derived laps, e.g. ``2024_bahrain_hypercar``."""
    return pd.read_csv(DERIVED_DIR / series / f"laps_{series}_{slug}.csv")


def winning_car(laps: pd.DataFrame):
    """The class winner as measured — the car that completed the most laps.
    Returned in the ``car`` column's own dtype so it filters correctly."""
    return laps.groupby("car")["lap"].max().idxmax()


def stint_lengths(laps: pd.DataFrame, car) -> list[int]:
    """Fuel-stint lengths for a car, segmented by its real pit visits
    (``pit_time`` present). The length of a stint is the number of laps run
    before that pit visit."""
    car_laps = laps[laps["car"] == car].sort_values("lap")
    pit_laps = car_laps.loc[car_laps["pit_time"].fillna(0) > 0, "lap"].astype(int).tolist()
    boundaries = [int(car_laps["lap"].min()) - 1] + pit_laps + [int(car_laps["lap"].max())]
    lengths = [b - a for a, b in zip(boundaries, boundaries[1:]) if b - a > 0]
    return lengths


#: Default slack (laps) a stint may fall short of the fuel range and still
#: count as "full" — chosen once, never re-examined until the sensitivity
#: sweep in scripts/run_fuel_limited_sensitivity.py. See that script's report
#: for whether the headline finding actually depends on this choice.
DEFAULT_TOLERANCE_LAPS = 3


@dataclass(frozen=True)
class FuelLimitedAudit:
    """Whether a race winner's real stints ran near the fuel maximum."""

    series: str
    circuit: str
    car_class: str
    year: int
    car: str
    fuel_range_laps: int
    longest_stint: int
    n_full_stints: int      # stints within tolerance_laps of the fuel range
    n_stints: int
    tolerance_laps: int = DEFAULT_TOLERANCE_LAPS

    @property
    def ran_fuel_limited(self) -> bool:
        """The winner ran at least one full-range stint and its longest stint
        reaches the fuel range — i.e. it was fuel- not tyre-limited."""
        return (
            self.n_full_stints >= 1
            and self.longest_stint >= self.fuel_range_laps - self.tolerance_laps
        )

    def row(self) -> dict:
        return {
            # car_class belongs in the identity: IMSA fields three classes at
            # the same circuit-year, and without it their rows are
            # indistinguishable -- which hid that "winners run fuel-limited"
            # is a prototype fact, not a universal one.
            "series": self.series, "circuit": self.circuit,
            "car_class": self.car_class, "year": self.year,
            "winner_car": self.car, "fuel_range_laps": self.fuel_range_laps,
            "longest_stint": self.longest_stint, "n_full_stints": self.n_full_stints,
            "n_stints": self.n_stints, "ran_fuel_limited": self.ran_fuel_limited,
        }


def audit_fuel_limited(series: str, circuit: str, car_class: str, year: int, slug: str,
                       fuel_range_laps: int,
                       tolerance_laps: int = DEFAULT_TOLERANCE_LAPS) -> FuelLimitedAudit:
    """Reconstruct the winner's stints and test them against the fuel range."""
    laps = load_endurance_laps(series, slug)
    car = winning_car(laps)
    lengths = stint_lengths(laps, car)
    longest = max(lengths) if lengths else 0
    n_full = int(np.sum(np.array(lengths) >= fuel_range_laps - tolerance_laps))
    return FuelLimitedAudit(series, circuit, car_class, year, str(car), fuel_range_laps,
                            longest, n_full, len(lengths), tolerance_laps)
