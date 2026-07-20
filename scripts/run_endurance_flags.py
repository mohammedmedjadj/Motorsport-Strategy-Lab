"""Materialise the per-race race-control flag timeline for IMSA and WEC.

Aggregates server-side into per (race, lap, flag) car-lap counts — a ~1 MB
artifact covering every available race — rather than downloading full lap data
for ~100 races. Neutralisations are race-wide, so no per-class detail is needed.

Usage (needs network; writes data/derived/endurance/race_flags.csv)::

    python scripts/run_endurance_flags.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.endurance_loader import HF_DUCKDB  # noqa: E402
from src.safety_car.endurance import (  # noqa: E402
    RACE_FLAGS_CSV,
    extract_events,
    fit_neutralisation_models,
    load_race_flags,
    race_timeline,
)

QUERY = """
    SELECT series_code, year, event, session_id, lap, flags, count(*) AS car_laps
    FROM imsa.laps_with_metadata
    WHERE session = 'race' AND series_code IN ('imsa', 'wec')
    GROUP BY 1, 2, 3, 4, 5, 6
    ORDER BY series_code, year, event, session_id, lap, flags
"""


def main() -> int:
    import duckdb

    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute(f"ATTACH '{HF_DUCKDB}' AS imsa (READ_ONLY);")
    df = con.execute(QUERY).df()
    RACE_FLAGS_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(RACE_FLAGS_CSV, index=False)
    print(f"wrote {RACE_FLAGS_CSV} ({len(df)} rows)")

    timeline = race_timeline(load_race_flags())
    events = extract_events(timeline)
    print(f"{timeline.groupby(['series_code','year','event','session_id']).ngroups} races, "
          f"{len(events)} neutralisation periods")
    for m in fit_neutralisation_models(timeline, events):
        print(
            f"  {m.series.upper():5s} {m.kind:4s} "
            f"{m.n_races_with_event}/{m.n_races} races  "
            f"P(>=1) {m.occurrence.fmt(3)}  rate/lap {m.rate_per_lap.fmt(5)}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
