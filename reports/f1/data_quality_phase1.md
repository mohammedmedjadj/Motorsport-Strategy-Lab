# Phase 1 — Data quality report

Lap-level accounting after cleaning (`src/ingestion/`). A lap is kept
for pace analysis (`is_pace_lap`) only if **no** exclusion flag is set.
Exclusion reasons overlap (e.g. an in-lap may also be flagged
inaccurate), so per-reason counts exceed the number of excluded laps.
`red-flag stint laps` is informational, not an exclusion: laps whose
stint contains a red flag (tyre sets may change without a pit stop).

| Race | Total | Pace laps | % kept | in_lap | out_lap | missing_laptime | inaccurate | wet_compound | non_green | unknown_status | deleted | red-flag stint laps |
|---|---|---|---|---|---|---|---|---|---|---|---|---|

**No laps.**

## Races skipped (not available at ingest time)

- 2023_monaco: SessionNotAvailableError: No data for this session! If this session only finished recently, please try again in a few minutes.
- 2023_singapore: SessionNotAvailableError: No data for this session! If this session only finished recently, please try again in a few minutes.
- 2023_barcelona: SessionNotAvailableError: No data for this session! If this session only finished recently, please try again in a few minutes.
- 2023_suzuka: SessionNotAvailableError: No data for this session! If this session only finished recently, please try again in a few minutes.
- 2024_monaco: SessionNotAvailableError: No data for this session! If this session only finished recently, please try again in a few minutes.
- 2024_singapore: SessionNotAvailableError: No data for this session! If this session only finished recently, please try again in a few minutes.
- 2024_barcelona: SessionNotAvailableError: No data for this session! If this session only finished recently, please try again in a few minutes.
- 2024_suzuka: SessionNotAvailableError: No data for this session! If this session only finished recently, please try again in a few minutes.
- 2025_monaco: SessionNotAvailableError: No data for this session! If this session only finished recently, please try again in a few minutes.
- 2025_singapore: SessionNotAvailableError: No data for this session! If this session only finished recently, please try again in a few minutes.
- 2025_barcelona: SessionNotAvailableError: No data for this session! If this session only finished recently, please try again in a few minutes.
- 2025_suzuka: SessionNotAvailableError: No data for this session! If this session only finished recently, please try again in a few minutes.
- 2026_monaco: SessionNotAvailableError: No data for this session! If this session only finished recently, please try again in a few minutes.
- 2026_singapore: SessionNotAvailableError: No data for this session! If this session only finished recently, please try again in a few minutes.
- 2026_barcelona: SessionNotAvailableError: No data for this session! If this session only finished recently, please try again in a few minutes.
- 2026_suzuka: SessionNotAvailableError: No data for this session! If this session only finished recently, please try again in a few minutes.
