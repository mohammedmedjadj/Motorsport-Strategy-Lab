"""F1 reliability / attrition from the Kaggle results (2011-2024).

The cross-series counterpart to the WEC reliability layer, sharing the same
Jeffreys machinery via ``reliability.core``. Turns ``results`` + ``status`` into
the probability a car is classified at the finish, by circuit and by regulation
era — which circuits break cars, and whether reliability moved across eras.

Finish classification is explicit: a car is *classified* if it saw the flag
("Finished") or was running but lapped ("+N Laps"); every mechanical or accident
status ("Engine", "Collision", "Gearbox", ...) is a DNF. Kept honest — the raw
status strings drive it, nothing is imputed.
"""

from __future__ import annotations

import pandas as pd

from src.data.f1_history_loader import (
    DEFAULT_ERA_START,
    F1_EXTERNAL,
    regulation_era,
)
from src.reliability.core import ReliabilityRate, finish_rate_by

__all__ = ["load_f1_results", "finish_rate_by", "ReliabilityRate",
           "reliability_improves_off_the_street"]

#: Street / temporary circuits — collision-driven attrition should make these
#: harder to finish than permanent tracks. Used only as the positive control,
#: not in any estimate. circuitRef values from the Kaggle circuits table.
_STREET_CIRCUITS = frozenset({
    "monaco", "marina_bay", "baku", "valencia", "jeddah", "vegas", "miami",
})


def _classified(status: pd.Series) -> pd.Series:
    s = status.astype(str)
    return s.eq("Finished") | s.str.startswith("+")


def load_f1_results(era_start: int = DEFAULT_ERA_START) -> pd.DataFrame:
    """One row per car-entry with ``classified`` (bool), ``era`` and ``street``
    (bool) derived. Filtered to ``year >= era_start``."""
    def _read(name: str) -> pd.DataFrame:
        return pd.read_csv(F1_EXTERNAL / name, na_values=["\\N"])

    results = _read("results.csv")[["raceId", "driverId", "statusId"]]
    races = _read("races.csv")[["raceId", "year", "circuitId"]]
    circuits = _read("circuits.csv")[["circuitId", "circuitRef"]]
    status = _read("status.csv")

    df = (results.merge(races, on="raceId")
          .merge(circuits, on="circuitId")
          .merge(status, on="statusId"))
    df = df[df["year"] >= era_start].copy()
    df["classified"] = _classified(df["status"])
    df["era"] = df["year"].map(regulation_era)
    df["street"] = df["circuitRef"].isin(_STREET_CIRCUITS)
    return df


def reliability_improves_off_the_street(df: pd.DataFrame) -> bool:
    """Positive control: permanent circuits are easier to finish than street
    circuits (which punish any mistake with a wall). True iff the permanent-track
    finish rate exceeds the street one."""
    if df["street"].nunique() < 2:
        return False
    street = df.loc[df["street"], "classified"].mean()
    permanent = df.loc[~df["street"], "classified"].mean()
    return bool(permanent > street)
