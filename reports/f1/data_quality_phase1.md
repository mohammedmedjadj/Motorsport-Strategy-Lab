# Phase 1 — Data quality report

Lap-level accounting after cleaning (`src/ingestion/`). A lap is kept
for pace analysis (`is_pace_lap`) only if **no** exclusion flag is set.
Exclusion reasons overlap (e.g. an in-lap may also be flagged
inaccurate), so per-reason counts exceed the number of excluded laps.
`red-flag stint laps` is informational, not an exclusion: laps whose
stint contains a red flag (tyre sets may change without a pit stop).

| Race | Total | Pace laps | % kept | in_lap | out_lap | missing_laptime | inaccurate | wet_compound | non_green | unknown_status | deleted | red-flag stint laps |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2023_monaco | 1515 | 938 | 61.9% | 38 | 37 | 3 | 92 | 444 | 214 | 0 | 27 | 0 |
| 2023_singapore | 1088 | 829 | 76.2% | 25 | 26 | 26 | 130 | 0 | 243 | 0 | 10 | 0 |
| 2023_barcelona | 1312 | 1198 | 91.3% | 43 | 45 | 0 | 105 | 0 | 0 | 0 | 9 | 0 |
| 2023_suzuka | 880 | 673 | 76.5% | 48 | 44 | 61 | 178 | 0 | 129 | 0 | 14 | 0 |
| 2024_monaco | 1237 | 1168 | 94.4% | 23 | 23 | 11 | 50 | 0 | 54 | 0 | 5 | 20 |
| 2024_singapore | 1177 | 1097 | 93.2% | 25 | 23 | 1 | 68 | 0 | 0 | 0 | 14 | 0 |
| 2024_barcelona | 1310 | 1192 | 91.0% | 42 | 43 | 0 | 104 | 0 | 0 | 0 | 14 | 0 |
| 2024_suzuka | 907 | 756 | 83.4% | 55 | 54 | 31 | 122 | 0 | 42 | 0 | 10 | 20 |
| 2025_monaco | 1425 | 1165 | 81.8% | 41 | 40 | 2 | 154 | 0 | 176 | 0 | 14 | 0 |
| 2025_singapore | 1229 | 1106 | 90.0% | 23 | 25 | 0 | 66 | 0 | 40 | 0 | 19 | 0 |
| 2025_barcelona | 1203 | 980 | 81.5% | 55 | 55 | 1 | 213 | 0 | 115 | 0 | 9 | 0 |
| 2025_suzuka | 1059 | 989 | 93.4% | 21 | 21 | 0 | 62 | 0 | 0 | 0 | 8 | 0 |

**Overall: 12091/14342 laps kept for pace analysis (84.3%).**
