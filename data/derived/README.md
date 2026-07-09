# Derived datasets — column dictionary

Produced by `scripts/run_ingestion.py` (Phase 1). One file set per race,
plus a session index. All time quantities are float seconds (timedeltas do
not round-trip through CSV).

## `laps_{season}_{circuit}.csv`

| Column | Meaning |
|---|---|
| `Driver`, `DriverNumber`, `Team` | Driver three-letter code, car number, team name |
| `LapNumber` | Lap of the race (1-based) |
| `Stint` | Stint counter (increments at pit stops) |
| `Compound` | Tyre compound (SOFT/MEDIUM/HARD/INTERMEDIATE/WET) |
| `TyreLife` | Tyre age in laps (includes laps run in other sessions for used sets) |
| `FreshTyre` | True if the set was new at stint start |
| `Position` | Running position during the lap (live info — no leakage) |
| `TrackStatus` | Concatenated status codes active during the lap (1=green, 2=yellow, 4=SC, 5=red, 6/7=VSC) |
| `lap_time_s` | Lap time in seconds |
| `time_s` / `lap_start_time_s` | Session time at lap end / lap start, seconds |
| `air_temp_c`, `track_temp_c`, `humidity_pct`, `rainfall` | Latest weather reading at or before lap end |
| `is_in_lap` … `is_deleted` | Exclusion flags (see `src/ingestion/cleaning.py` docstring) |
| `is_pace_lap` | True iff **no** exclusion flag is set — the filter for pace analysis |
| `stint_crosses_red_flag` | Informational: stint contains a red flag (tyre set arithmetic weakened) |

## `track_status_{season}_{circuit}.csv`

Status change log: `time_s` (session time), `Status` (code string), `Message`.
A file with a single row means the status never changed (full green race),
not missing data.

## `sessions.csv`

One row per race: `season`, `circuit`, `event_name`, `scheduled_laps`
(race distance), `n_drivers`.
