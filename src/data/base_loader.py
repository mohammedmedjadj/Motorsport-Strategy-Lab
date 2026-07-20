"""Common loader interface and the normalised lap schema every series maps to.

The F1 pipeline (FastF1) and the endurance pipeline (IMSA/WEC DuckDB) have very
different raw schemas. Rather than force one series' shape onto the other, each
loader normalises into ``LAP_COLUMNS`` below — the minimal lap-level frame the
degradation / safety-car / simulator layers consume. Anything a source cannot
provide is left as a NaN/None column (never fabricated), exactly like the F1
side treats missing FastF1 fields.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

#: The normalised per-lap columns. Every loader returns exactly these.
#:
#: Endurance racing separates three things F1 conflates into "the stint", and
#: the schema keeps them apart because they drive different decisions:
#:
#: - **pit visits** (``is_pit_lap``): a car may stop for fuel only,
#: - **tyre life** (``tyre_age``): resets only when tyres are actually changed,
#: - **driver stints** (``driver_stint``): resets on a driver change, which is
#:   mandatory in endurance and independent of both of the above.
#:
#: At Watkins Glen 2023 the #01 GTP car made 13 pit visits across only 4 driver
#: stints — the difference is fuel-only stops. Collapsing these would destroy
#: exactly the structure an endurance strategy model needs.
LAP_COLUMNS: tuple[str, ...] = (
    "series",          # "f1" | "imsa" | "wec" | ...
    "year",            # int
    "event",           # short event name, e.g. "Watkins Glen"
    "circuit",         # circuit name
    "car",             # car number/id (str; endurance runs multi-car teams)
    "car_class",       # class as raced, e.g. "GTP", "HYPERCAR"; "" for F1
    "driver",          # driver on this lap (endurance rotates drivers)
    "lap",             # int lap number within the race
    "driver_stint",    # int driver-stint number (increments on driver change)
    "driver_stint_lap",  # int lap index within the driver stint (0 = out-lap)
    "lap_time_s",      # float seconds; NaN if not set/timed
    "pit_time_s",      # float seconds spent in pit on this lap; NaN if none
    "is_pit_lap",      # bool: the car visited the pits on this lap
    "flag",            # track status token: "GF", "FCY", "FF", "RF"
    "is_green",        # bool: racing under green flag
    "tyre_age",        # float laps on the current tyre set; NaN if unknown
    "is_tyre_change",  # bool: tyre_age reset on this lap (new tyres fitted)
    "air_temp_c",      # float; NaN if unknown
    "track_temp_c",    # float; NaN if unknown
    "humidity_pct",    # float; NaN if unknown
    "raining",         # bool; NA if unknown
    "race_duration_min",  # int scheduled race length in minutes; NaN if unknown
)


class BaseLoader(ABC):
    """A source that yields the normalised lap frame for one race.

    Deliberately leaner than a FastF1 clone: endurance timing feeds carry laps
    and weather together and no public telemetry, so the interface promises only
    what every supported source can actually deliver — the lap frame and the
    list of events it can serve.
    """

    series: str

    @abstractmethod
    def list_events(self, year: int) -> list[str]:
        """Event names available for ``year`` in this series."""

    @abstractmethod
    def load_laps(self, year: int, event: str, car_class: str | None = None) -> pd.DataFrame:
        """Return the normalised lap frame (``LAP_COLUMNS``) for one race,
        optionally restricted to a single car class."""

    @staticmethod
    def _check_schema(df: pd.DataFrame) -> pd.DataFrame:
        """Assert the frame has exactly the normalised columns, in order."""
        missing = [c for c in LAP_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"normalised frame is missing columns: {missing}")
        return df[list(LAP_COLUMNS)]
