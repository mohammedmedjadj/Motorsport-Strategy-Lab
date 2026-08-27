# Phase 1 — Data quality report

Lap-level accounting after cleaning (`src/ingestion/`). A lap is kept
for pace analysis (`is_pace_lap`) only if **no** exclusion flag is set.
Exclusion reasons overlap (e.g. an in-lap may also be flagged
inaccurate), so per-reason counts exceed the number of excluded laps.
`red-flag stint laps` is informational, not an exclusion: laps whose
stint contains a red flag (tyre sets may change without a pit stop).

| Race | Total | Pace laps | % kept | in_lap | out_lap | missing_laptime | inaccurate | wet_compound | non_green | unknown_status | deleted | red-flag stint laps |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2022_bahrain | 1125 | 854 | 75.9% | 59 | 58 | 7 | 232 | 0 | 167 | 0 | 4 | 0 |
| 2022_jeddah | 820 | 588 | 71.7% | 21 | 19 | 48 | 169 | 0 | 191 | 0 | 11 | 0 |
| 2022_melbourne | 1045 | 794 | 76.0% | 22 | 22 | 19 | 232 | 0 | 204 | 0 | 0 | 0 |
| 2022_imola | 1132 | 728 | 64.3% | 26 | 26 | 6 | 126 | 329 | 121 | 0 | 8 | 0 |
| 2022_miami | 1057 | 802 | 75.9% | 29 | 27 | 35 | 179 | 0 | 200 | 0 | 6 | 0 |
| 2022_barcelona | 1230 | 1046 | 85.0% | 55 | 53 | 0 | 126 | 0 | 64 | 0 | 16 | 0 |
| 2022_monaco | 1179 | 599 | 50.8% | 55 | 73 | 26 | 212 | 398 | 269 | 0 | 14 | 184 |
| 2022_baku | 891 | 734 | 82.4% | 30 | 27 | 19 | 127 | 0 | 113 | 0 | 0 | 0 |
| 2022_montreal | 1264 | 1000 | 79.1% | 32 | 31 | 2 | 235 | 0 | 214 | 0 | 8 | 0 |
| 2022_silverstone | 815 | 646 | 79.3% | 49 | 47 | 42 | 141 | 0 | 104 | 0 | 8 | 20 |
| 2022_red_bull_ring | 1324 | 1080 | 81.6% | 44 | 43 | 1 | 143 | 0 | 86 | 0 | 65 | 0 |
| 2022_ricard | 958 | 780 | 81.4% | 28 | 25 | 13 | 125 | 0 | 152 | 0 | 10 | 0 |
| 2022_hungaroring | 1383 | 1122 | 81.1% | 42 | 43 | 1 | 180 | 0 | 178 | 0 | 14 | 0 |
| 2022_spa | 792 | 624 | 78.8% | 38 | 40 | 40 | 147 | 0 | 91 | 0 | 5 | 0 |
| 2022_zandvoort | 1392 | 1042 | 74.9% | 72 | 71 | 4 | 253 | 0 | 259 | 0 | 8 | 0 |
| 2022_monza | 971 | 736 | 75.8% | 30 | 28 | 3 | 193 | 0 | 161 | 0 | 15 | 0 |
| 2022_singapore | 945 | 275 | 29.1% | 23 | 22 | 108 | 269 | 588 | 305 | 0 | 0 | 0 |
| 2022_suzuka | 507 | 0 | 0.0% | 42 | 43 | 75 | 137 | 507 | 38 | 0 | 0 | 35 |
| 2022_austin | 992 | 743 | 74.9% | 37 | 37 | 74 | 214 | 0 | 170 | 0 | 29 | 0 |
| 2022_mexico_city | 1379 | 1276 | 92.5% | 24 | 23 | 1 | 95 | 0 | 34 | 0 | 2 | 0 |
| 2022_interlagos | 1259 | 904 | 71.8% | 44 | 45 | 3 | 318 | 0 | 276 | 0 | 6 | 0 |
| 2022_yas_marina | 1117 | 994 | 89.0% | 34 | 31 | 0 | 85 | 0 | 20 | 0 | 25 | 0 |
| 2023_bahrain | 1056 | 872 | 82.6% | 52 | 50 | 1 | 142 | 0 | 77 | 0 | 17 | 0 |
| 2023_jeddah | 943 | 809 | 85.8% | 25 | 24 | 19 | 114 | 0 | 77 | 0 | 16 | 0 |
| 2023_melbourne | 1003 | 755 | 75.3% | 65 | 67 | 102 | 234 | 0 | 197 | 0 | 1 | 644 |
| 2023_baku | 962 | 803 | 83.5% | 24 | 25 | 32 | 116 | 0 | 134 | 0 | 1 | 0 |
| 2023_miami | 1138 | 1071 | 94.1% | 20 | 20 | 0 | 60 | 0 | 0 | 0 | 7 | 0 |
| 2023_monaco | 1515 | 938 | 61.9% | 38 | 37 | 3 | 92 | 444 | 214 | 0 | 27 | 0 |
| 2023_barcelona | 1312 | 1198 | 91.3% | 43 | 45 | 0 | 105 | 0 | 0 | 0 | 9 | 0 |
| 2023_montreal | 1317 | 1066 | 80.9% | 34 | 33 | 3 | 190 | 0 | 186 | 0 | 8 | 0 |
| 2023_red_bull_ring | 1354 | 1087 | 80.3% | 63 | 65 | 2 | 168 | 0 | 129 | 0 | 82 | 0 |
| 2023_silverstone | 971 | 787 | 81.1% | 26 | 24 | 5 | 169 | 0 | 125 | 0 | 17 | 0 |
| 2023_hungaroring | 1252 | 1124 | 89.8% | 39 | 36 | 0 | 94 | 0 | 39 | 0 | 18 | 0 |
| 2023_spa | 816 | 653 | 80.0% | 38 | 38 | 1 | 95 | 0 | 55 | 0 | 14 | 0 |
| 2023_zandvoort | 1343 | 798 | 59.4% | 102 | 102 | 33 | 329 | 328 | 206 | 0 | 1 | 61 |
| 2023_monza | 957 | 864 | 90.3% | 26 | 25 | 9 | 79 | 0 | 0 | 0 | 14 | 0 |
| 2023_singapore | 1088 | 829 | 76.2% | 25 | 26 | 26 | 130 | 0 | 243 | 0 | 10 | 0 |
| 2023_suzuka | 880 | 673 | 76.5% | 48 | 44 | 61 | 178 | 0 | 129 | 0 | 14 | 0 |
| 2023_losail | 1006 | 760 | 75.5% | 55 | 55 | 6 | 172 | 0 | 110 | 0 | 49 | 0 |
| 2023_austin | 1014 | 881 | 86.9% | 39 | 40 | 0 | 95 | 0 | 7 | 0 | 34 | 0 |
| 2023_mexico_city | 1282 | 1061 | 82.8% | 42 | 39 | 30 | 151 | 0 | 175 | 0 | 9 | 157 |
| 2023_interlagos | 1108 | 986 | 89.0% | 70 | 67 | 19 | 122 | 0 | 34 | 0 | 0 | 15 |
| 2023_las_vegas | 946 | 639 | 67.5% | 31 | 31 | 85 | 208 | 0 | 272 | 0 | 13 | 0 |
| 2023_yas_marina | 1157 | 1032 | 89.2% | 38 | 37 | 0 | 94 | 0 | 0 | 0 | 33 | 0 |
| 2024_bahrain | 1129 | 988 | 87.5% | 43 | 43 | 2 | 105 | 0 | 42 | 0 | 20 | 0 |
| 2024_jeddah | 901 | 786 | 87.2% | 20 | 19 | 28 | 85 | 0 | 69 | 0 | 16 | 0 |
| 2024_melbourne | 998 | 851 | 85.3% | 37 | 37 | 3 | 141 | 0 | 61 | 0 | 1 | 0 |
| 2024_suzuka | 907 | 756 | 83.4% | 55 | 54 | 31 | 122 | 0 | 42 | 0 | 10 | 20 |
| 2024_shanghai | 1032 | 739 | 71.6% | 41 | 41 | 25 | 270 | 0 | 223 | 0 | 5 | 0 |
| 2024_miami | 1111 | 915 | 82.4% | 28 | 28 | 5 | 177 | 0 | 130 | 0 | 20 | 0 |
| 2024_imola | 1238 | 1153 | 93.1% | 28 | 28 | 1 | 74 | 0 | 0 | 0 | 11 | 0 |
| 2024_monaco | 1237 | 1168 | 94.4% | 23 | 23 | 11 | 50 | 0 | 54 | 0 | 5 | 20 |
| 2024_montreal | 1272 | 251 | 19.7% | 45 | 44 | 5 | 250 | 846 | 317 | 0 | 29 | 0 |
| 2024_barcelona | 1310 | 1192 | 91.0% | 42 | 43 | 0 | 104 | 0 | 0 | 0 | 14 | 0 |
| 2024_silverstone | 960 | 658 | 68.5% | 46 | 46 | 0 | 110 | 234 | 0 | 0 | 9 | 0 |
| 2024_hungaroring | 1355 | 1228 | 90.6% | 41 | 41 | 0 | 101 | 0 | 21 | 0 | 5 | 0 |
| 2024_spa | 841 | 725 | 86.2% | 35 | 34 | 1 | 90 | 0 | 19 | 0 | 10 | 0 |
| 2024_zandvoort | 1426 | 1350 | 94.7% | 26 | 27 | 0 | 72 | 0 | 0 | 0 | 4 | 0 |
| 2024_monza | 1008 | 914 | 90.7% | 31 | 30 | 0 | 81 | 0 | 0 | 0 | 13 | 0 |
| 2024_baku | 973 | 852 | 87.6% | 24 | 24 | 21 | 92 | 0 | 63 | 0 | 2 | 0 |
| 2024_singapore | 1177 | 1097 | 93.2% | 25 | 23 | 1 | 68 | 0 | 0 | 0 | 14 | 0 |
| 2024_austin | 1059 | 852 | 80.5% | 23 | 24 | 28 | 122 | 0 | 133 | 0 | 39 | 0 |
| 2024_mexico_city | 1215 | 1051 | 86.5% | 22 | 22 | 2 | 154 | 0 | 110 | 0 | 10 | 0 |
| 2024_interlagos | 1134 | 0 | 0.0% | 36 | 35 | 37 | 191 | 1134 | 328 | 0 | 21 | 187 |
| 2024_las_vegas | 938 | 820 | 87.4% | 41 | 40 | 0 | 112 | 0 | 0 | 0 | 9 | 0 |
| 2024_losail | 943 | 664 | 70.4% | 61 | 60 | 20 | 226 | 0 | 246 | 0 | 18 | 0 |
| 2024_yas_marina | 1035 | 857 | 82.8% | 30 | 28 | 2 | 114 | 0 | 102 | 0 | 27 | 0 |
| 2025_melbourne | 927 | 36 | 3.9% | 82 | 84 | 69 | 359 | 750 | 372 | 0 | 6 | 0 |
| 2025_shanghai | 1065 | 942 | 88.5% | 26 | 26 | 0 | 70 | 0 | 71 | 0 | 3 | 0 |
| 2025_suzuka | 1059 | 989 | 93.4% | 21 | 21 | 0 | 62 | 0 | 0 | 0 | 8 | 0 |
| 2025_bahrain | 1128 | 924 | 81.9% | 43 | 42 | 13 | 176 | 0 | 80 | 0 | 31 | 0 |
| 2025_jeddah | 898 | 798 | 88.9% | 20 | 19 | 37 | 88 | 0 | 56 | 0 | 12 | 0 |
| 2025_miami | 1005 | 857 | 85.3% | 19 | 19 | 3 | 144 | 0 | 124 | 0 | 4 | 0 |
| 2025_imola | 1207 | 939 | 77.8% | 37 | 38 | 2 | 251 | 0 | 221 | 0 | 3 | 0 |
| 2025_monaco | 1425 | 1165 | 81.8% | 41 | 40 | 2 | 154 | 0 | 176 | 0 | 14 | 0 |
| 2025_barcelona | 1203 | 980 | 81.5% | 55 | 55 | 1 | 213 | 0 | 115 | 0 | 9 | 0 |
| 2025_montreal | 1349 | 1154 | 85.5% | 83 | 84 | 3 | 152 | 0 | 108 | 0 | 9 | 0 |
| 2025_red_bull_ring | 1126 | 984 | 87.4% | 33 | 32 | 2 | 116 | 0 | 69 | 0 | 11 | 0 |
| 2025_silverstone | 825 | 138 | 16.7% | 36 | 40 | 91 | 329 | 608 | 340 | 0 | 13 | 0 |
| 2025_spa | 879 | 602 | 68.5% | 26 | 46 | 60 | 132 | 240 | 80 | 0 | 13 | 0 |
| 2025_singapore | 1229 | 1106 | 90.0% | 23 | 25 | 0 | 66 | 0 | 40 | 0 | 19 | 0 |
| 2026_suzuka | 1107 | 913 | 82.5% | 30 | 29 | 21 | 184 | 0 | 140 | 0 | 6 | 0 |
| 2026_monaco | 1452 | 1136 | 78.2% | 89 | 87 | 37 | 275 | 0 | 247 | 0 | 25 | 32 |

**Overall: 70583/91080 laps kept for pace analysis (77.5%).**

## Races skipped (not available at ingest time)

- 2024_red_bull_ring: DataNotLoadedError: The data you are trying to access has not been loaded yet. See `Session.load`
- 2025_hungaroring: DataNotLoadedError: The data you are trying to access has not been loaded yet. See `Session.load`
- 2025_zandvoort: RateLimitExceededError: any API: 500 calls/h
- 2025_monza: RateLimitExceededError: any API: 500 calls/h
- 2025_baku: RateLimitExceededError: any API: 500 calls/h
- 2025_austin: RateLimitExceededError: any API: 500 calls/h
- 2025_mexico_city: RateLimitExceededError: any API: 500 calls/h
- 2025_interlagos: RateLimitExceededError: any API: 500 calls/h
- 2025_las_vegas: RateLimitExceededError: any API: 500 calls/h
- 2025_losail: RateLimitExceededError: any API: 500 calls/h
- 2025_yas_marina: RateLimitExceededError: any API: 500 calls/h
- 2026_melbourne: RateLimitExceededError: any API: 500 calls/h
- 2026_shanghai: RateLimitExceededError: any API: 500 calls/h
- 2026_miami: RateLimitExceededError: any API: 500 calls/h
- 2026_montreal: RateLimitExceededError: any API: 500 calls/h
- 2026_barcelona: RateLimitExceededError: any API: 500 calls/h
- 2026_red_bull_ring: RateLimitExceededError: any API: 500 calls/h
- 2026_silverstone: RateLimitExceededError: any API: 500 calls/h
- 2026_spa: RateLimitExceededError: any API: 500 calls/h
- 2026_hungaroring: RateLimitExceededError: any API: 500 calls/h
- 2026_zandvoort: RateLimitExceededError: any API: 500 calls/h
- 2026_monza: RateLimitExceededError: any API: 500 calls/h
- 2026_madrid: RateLimitExceededError: any API: 500 calls/h
- 2026_baku: RateLimitExceededError: any API: 500 calls/h
- 2026_bahrain: RateLimitExceededError: any API: 500 calls/h
- 2026_singapore: RateLimitExceededError: any API: 500 calls/h
- 2026_austin: RateLimitExceededError: any API: 500 calls/h
- 2026_mexico_city: RateLimitExceededError: any API: 500 calls/h
- 2026_interlagos: RateLimitExceededError: any API: 500 calls/h
- 2026_las_vegas: RateLimitExceededError: any API: 500 calls/h
- 2026_losail: RateLimitExceededError: any API: 500 calls/h
- 2026_yas_marina: RateLimitExceededError: any API: 500 calls/h
