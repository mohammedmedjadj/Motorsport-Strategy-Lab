"""IMSA / WEC lap loader.

FastF1 does not cover endurance racing, so this layer replaces the whole F1
ingestion path for those series. Source: the community-maintained DuckDB at
``hf://datasets/tobil/imsa/imsa.duckdb``, whose ``laps_with_metadata`` view
already joins laps, stints, weather and event metadata for IMSA, WEC, ELMS and
ALMS. Verified in Phase 0 — see ``reports/endurance_availability_phase0.md``.

Two gotchas found during that verification, both handled here:

1. **Sessions are mixed.** ``laps_with_metadata`` holds practice, qualifying,
   warmup, test *and* race laps for an event. Filtering an event without also
   filtering ``session='race'`` silently returns several overlapping races'
   worth of lap numbers. The loader always pins the session.
2. **``stint_number`` is the driver stint, not the tyre stint.** Tyre life is
   ``est_tire_age``, which resets independently when tyres are changed. See
   ``base_loader.LAP_COLUMNS``.

Remote queries are slow (the DuckDB is fetched over HTTP), so races used by the
project are materialised once into ``data/derived/endurance/`` and read from
there by default; ``source="remote"`` re-fetches.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.base_loader import BaseLoader
from src.ingestion.config import DERIVED_DIR

#: The upstream dataset, attached read-only by DuckDB.
HF_DUCKDB = "hf://datasets/tobil/imsa/imsa.duckdb"

ENDURANCE_DIR = DERIVED_DIR  # each series lives in DERIVED_DIR/<series>/

SUPPORTED_SERIES = ("imsa", "wec", "elms", "alms")

#: Raw columns pulled from ``laps_with_metadata`` (deliberately excludes the
#: bulky ``microsectors_json``).
_RAW_COLUMNS = (
    "series_code", "year", "event", "circuit_name", "session", "session_id",
    "car", "class", "driver_name", "driver_id", "lap", "stint_number",
    "stint_lap", "lap_time", "lap_time_s1", "lap_time_s2", "lap_time_s3",
    "pit_time", "flags", "est_tire_age", "air_temp_f", "track_temp_f",
    "humidity_percent", "raining", "race_duration_minutes",
)


def slugify(text: str) -> str:
    """Stable file-name fragment: ``"Watkins Glen"`` -> ``"watkins_glen"``."""
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def derived_path(series: str, year: int, event: str, car_class: str) -> Path:
    """Where a materialised race lives on disk."""
    return ENDURANCE_DIR / series / (
        f"laps_{series}_{year}_{slugify(event)}_{slugify(car_class)}.csv"
    )


def _fahrenheit_to_celsius(f: pd.Series) -> pd.Series:
    return (pd.to_numeric(f, errors="coerce") - 32.0) * 5.0 / 9.0


class EnduranceLoader(BaseLoader):
    """Loads one endurance race into the normalised lap frame.

    One class serves every series in the source rather than the per-series
    loaders originally sketched: ``laps_with_metadata`` already exposes IMSA and
    WEC through an identical view, so separate classes would duplicate the same
    normalisation. Series-specific *modelling* still lives in its own modules.
    """

    def __init__(self, series: str) -> None:
        series = series.lower()
        if series not in SUPPORTED_SERIES:
            raise ValueError(
                f"unsupported series {series!r}; expected one of {SUPPORTED_SERIES}"
            )
        self.series = series

    # ---------------------------------------------------------------- remote

    @staticmethod
    def _connect():  # pragma: no cover - requires network
        import duckdb

        con = duckdb.connect()
        con.execute("INSTALL httpfs; LOAD httpfs;")
        con.execute(f"ATTACH '{HF_DUCKDB}' AS imsa (READ_ONLY);")
        return con

    def list_events(self, year: int) -> list[str]:  # pragma: no cover - network
        con = self._connect()
        rows = con.execute(
            "SELECT DISTINCT event FROM imsa.laps_with_metadata "
            "WHERE series_code = ? AND year = ? AND session = 'race' ORDER BY event",
            [self.series, str(year)],
        ).fetchall()
        return [r[0] for r in rows]

    def fetch_remote(self, year: int, event: str, car_class: str) -> pd.DataFrame:  # pragma: no cover - network
        """Pull one race's raw laps from the upstream DuckDB."""
        con = self._connect()
        return con.execute(
            f"SELECT {', '.join(_RAW_COLUMNS)} FROM imsa.laps_with_metadata "
            "WHERE series_code = ? AND year = ? AND event = ? AND class = ? "
            "AND session = 'race' ORDER BY car, lap",
            [self.series, str(year), event, car_class],
        ).df()

    def materialise(self, year: int, event: str, car_class: str) -> Path:  # pragma: no cover - network
        """Fetch one race and cache it under ``data/derived/endurance/``."""
        raw = self.fetch_remote(year, event, car_class)
        if raw.empty:
            raise ValueError(f"no race laps for {self.series} {year} {event} {car_class}")
        path = derived_path(self.series, year, event, car_class)
        path.parent.mkdir(parents=True, exist_ok=True)
        raw.to_csv(path, index=False)
        return path

    # ----------------------------------------------------------- normalising

    @staticmethod
    def normalise(raw: pd.DataFrame) -> pd.DataFrame:
        """Map the upstream schema onto ``LAP_COLUMNS``.

        Nothing is imputed: fields the source leaves empty stay NaN/NA.
        """
        if raw.empty:
            raise ValueError("cannot normalise an empty lap frame")
        sessions = set(raw["session"].dropna().unique())
        if not sessions <= {"race"}:
            raise ValueError(
                f"expected race laps only, got sessions {sorted(sessions)} — "
                "filter session='race' before normalising"
            )

        out = pd.DataFrame(index=raw.index)
        out["series"] = raw["series_code"].astype(str)
        out["year"] = pd.to_numeric(raw["year"], errors="coerce").astype("Int64")
        out["event"] = raw["event"].astype(str)
        out["circuit"] = raw["circuit_name"].astype(str)
        out["car"] = raw["car"].astype(str)
        out["car_class"] = raw["class"].astype(str)
        out["driver"] = raw["driver_name"].astype(str)
        out["lap"] = pd.to_numeric(raw["lap"], errors="coerce").astype("Int64")
        out["driver_stint"] = pd.to_numeric(raw["stint_number"], errors="coerce").astype("Int64")
        out["driver_stint_lap"] = pd.to_numeric(raw["stint_lap"], errors="coerce").astype("Int64")
        out["lap_time_s"] = pd.to_numeric(raw["lap_time"], errors="coerce")

        pit = pd.to_numeric(raw["pit_time"], errors="coerce")
        out["pit_time_s"] = pit
        out["is_pit_lap"] = pit.fillna(0.0) > 0.0

        out["flag"] = raw["flags"].astype(str)
        out["is_green"] = out["flag"].eq("GF")

        age = pd.to_numeric(raw["est_tire_age"], errors="coerce")
        out["tyre_age"] = age
        out["air_temp_c"] = _fahrenheit_to_celsius(raw["air_temp_f"])
        out["track_temp_c"] = _fahrenheit_to_celsius(raw["track_temp_f"])
        out["humidity_pct"] = pd.to_numeric(raw["humidity_percent"], errors="coerce")
        out["raining"] = raw["raining"].astype("boolean")
        out["race_duration_min"] = pd.to_numeric(
            raw["race_duration_minutes"], errors="coerce"
        ).astype("Int64")

        out = out.sort_values(["car", "lap"], kind="stable").reset_index(drop=True)
        # A tyre change is a drop in tyre age within a car (the estimator resets
        # to 0 on fresh rubber). The first lap of a race is not a change.
        prev_age = out.groupby("car", sort=False)["tyre_age"].shift(1)
        out["is_tyre_change"] = (prev_age.notna() & out["tyre_age"].notna()
                                 & (out["tyre_age"] < prev_age))
        return BaseLoader._check_schema(out)

    # ------------------------------------------------------------------ read

    def load_laps(
        self,
        year: int,
        event: str,
        car_class: str | None = None,
        source: str = "derived",
    ) -> pd.DataFrame:
        """Normalised race laps for one event and class.

        ``source="derived"`` (default) reads the materialised CSV — offline and
        fast; ``source="remote"`` re-fetches from the upstream DuckDB.
        """
        if car_class is None:
            raise ValueError("car_class is required (endurance races are multi-class)")
        if source == "remote":  # pragma: no cover - network
            raw = self.fetch_remote(year, event, car_class)
        elif source == "derived":
            path = derived_path(self.series, year, event, car_class)
            if not path.exists():
                raise FileNotFoundError(
                    f"{path} not materialised; call materialise() once with network access"
                )
            raw = pd.read_csv(path, dtype={"car": str})
        else:
            raise ValueError(f"unknown source {source!r}; use 'derived' or 'remote'")
        return self.normalise(raw)


def green_lap_times(laps: pd.DataFrame) -> pd.DataFrame:
    """Green-flag, non-pit laps — the endurance analogue of an F1 pace lap.

    Excludes anything under FCY/red and any lap with a pit visit, since both
    carry time that says nothing about tyre or car pace.
    """
    keep = laps["is_green"] & ~laps["is_pit_lap"] & laps["lap_time_s"].notna()
    return laps.loc[keep].copy()
