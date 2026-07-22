"""Loader for the relational F1 history (Kaggle ``lap_times`` + friends).

FastF1 gives the existing project deep, high-fidelity data (tyre compound,
per-lap Safety-Car / VSC flags) but only for the four circuits in
``src/ingestion/config.py``. This Kaggle export is the complementary axis:
**per-lap times for every circuit since 1996**, plus real pit-stop durations and
finish status — broad but without compound or per-lap neutralisation flags.

It is the direct fix for the "only 4 F1 circuits" coverage gap on the physical
layers (degradation, pit loss, reliability). Neutralisation calibration still
needs FastF1's flags; this source cannot replace that, and does not pretend to.

Every join and unit conversion is verified against the real files, not assumed.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.ingestion.config import REPO_ROOT

F1_EXTERNAL = REPO_ROOT / "data" / "external" / "f1"

#: Refuelling was banned from 2010, so from 2011 a green pit stop is a tyre
#: change (not a fuel splash) and within-stint pace is clean tyre + fuel-burn
#: net degradation — the same "net slope" the endurance model fits. Earlier
#: seasons mix refuelling strategy into stint pace and are excluded by default.
DEFAULT_ERA_START = 2011

#: F1 regulation eras. Degradation is only ever comparable *within* an era —
#: power unit, tyre generation and aero rules all shift pace and wear across
#: these boundaries. Encoding them makes cross-era pooling impossible by
#: construction.
#:
#: **2026 is its own era, and the deepest break in a generation.** It changes at
#: once, not just one dimension:
#:   * power unit — MGU-H removed, electric share ~50% (MGU-K 350 kW), 100%
#:     sustainable fuel, and ~30% less race fuel by mass (~70 kg vs ~100);
#:   * aerodynamics — active front/rear wings (X/Z modes) and a Manual Override
#:     Mode electric boost that *replaces DRS*;
#:   * chassis — narrower (1900 mm), shorter wheelbase, ~30 kg lighter (~768 kg);
#:   * tyres — narrower front and rear.
#: Less fuel + narrower tyres shift both the tyre-wear slope and the fuel-burn
#: term the decoupling isolates, and the MOM changes overtaking — so no pre-2026
#: fit transfers. A 2026 race is modelled from 2026 data alone (the live FastF1
#: pipeline), never from this historical Kaggle source, which stops at 2024.
_ERA_BOUNDS: tuple[tuple[int, int, str], ...] = (
    (2011, 2013, "v8-blown"),
    (2014, 2016, "hybrid-v6"),
    (2017, 2021, "wide-aero"),
    (2022, 2025, "ground-effect"),
    (2026, 9999, "2026-nextgen"),
)


def regulation_era(year: int) -> str:
    """The F1 regulation era a season belongs to. Two seasons in different eras
    must never be pooled for a degradation slope."""
    for lo, hi, name in _ERA_BOUNDS:
        if lo <= year <= hi:
            return name
    return "pre-2011"


def _require(name: str) -> pd.DataFrame:
    path = F1_EXTERNAL / name
    if not path.exists():
        raise FileNotFoundError(
            f"F1 Kaggle file {name} not found at {path}. Drop the Kaggle export "
            f"under data/external/f1/ (see src/data/f1_history_loader.py)."
        )
    # The Kaggle files use \N for missing; treat it as NaN everywhere.
    return pd.read_csv(path, na_values=["\\N"])


def load_f1_lap_history(era_start: int = DEFAULT_ERA_START) -> pd.DataFrame:
    """Per-lap F1 history joined to circuit + season, one row per driver-lap.

    Columns: ``raceId, year, round, circuitRef, circuit, driverRef, driverId,
    lap, lap_time_s, stint, tyre_age`` — where ``stint`` and ``tyre_age`` are
    reconstructed from ``pit_stops`` (a stop on lap L starts a new stint at L+1,
    tyre_age counting from 0 within each stint). Filtered to ``year >= era_start``.
    """
    laps = _require("lap_times.csv")
    races = _require("races.csv")[["raceId", "year", "round", "circuitId", "name"]]
    circuits = _require("circuits.csv")[["circuitId", "circuitRef", "name"]]
    circuits = circuits.rename(columns={"name": "circuit"})
    drivers = _require("drivers.csv")[["driverId", "driverRef"]]
    pits = _require("pit_stops.csv")[["raceId", "driverId", "lap"]]

    df = (laps
          .merge(races, on="raceId")
          .merge(circuits, on="circuitId")
          .merge(drivers, on="driverId"))
    df = df[df["year"] >= era_start].copy()
    df["lap_time_s"] = df["milliseconds"] / 1000.0
    df["era"] = df["year"].map(regulation_era)

    # Reconstruct stint index per (race, driver), vectorised: mark the laps a pit
    # stop happened, then the stint of any lap is the number of stops strictly
    # before it (a stop on lap L means new tyres run from L+1).
    df = df.sort_values(["raceId", "driverId", "lap"])
    pit_flag = pits.assign(is_pit=1)
    df = df.merge(pit_flag, on=["raceId", "driverId", "lap"], how="left")
    df["is_pit"] = df["is_pit"].fillna(0).astype(int)
    grp = df.groupby(["raceId", "driverId"], sort=False)
    df["stint"] = grp["is_pit"].cumsum() - df["is_pit"]
    # tyre age = laps since the stint's own first lap.
    first_lap = df.groupby(["raceId", "driverId", "stint"])["lap"].transform("min")
    df["tyre_age"] = df["lap"] - first_lap
    return df[["raceId", "year", "round", "era", "circuitRef", "circuit",
               "driverRef", "driverId", "lap", "lap_time_s", "stint", "tyre_age"]]
