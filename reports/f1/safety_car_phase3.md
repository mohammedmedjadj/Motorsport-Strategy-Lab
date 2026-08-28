# Phase 3 — Safety Car / VSC probability model

Event history 2018-2025 extracted from `TrackStatus` (SC=code 4,
VSC=codes 6/7, red flag=code 5). Estimates are posterior means with
95% equal-tailed credible intervals under a Jeffreys prior — with
6-8 editions per circuit, interval width IS the result; point
values alone would be false precision.

## Editions not included

- 2018_jeddah: LookupError: 2018_jeddah: requested 'Saudi Arabian Grand Prix' but FastF1 fuzzy-matched 'Australian Grand Prix' — edition most likely not held that season
- 2018_imola: LookupError: 2018_imola: requested 'Emilia Romagna Grand Prix' but FastF1 fuzzy-matched 'German Grand Prix' — edition most likely not held that season
- 2018_miami: LookupError: 2018_miami: requested 'Miami Grand Prix' but FastF1 fuzzy-matched 'Italian Grand Prix' — edition most likely not held that season
- 2018_zandvoort: LookupError: 2018_zandvoort: requested 'Dutch Grand Prix' but FastF1 fuzzy-matched 'Chinese Grand Prix' — edition most likely not held that season
- 2018_monza: DataNotLoadedError: The data you are trying to access has not been loaded yet. See `Session.load`
- 2019_jeddah: LookupError: 2019_jeddah: requested 'Saudi Arabian Grand Prix' but FastF1 fuzzy-matched 'Australian Grand Prix' — edition most likely not held that season
- 2019_imola: LookupError: 2019_imola: requested 'Emilia Romagna Grand Prix' but FastF1 fuzzy-matched 'German Grand Prix' — edition most likely not held that season
- 2019_miami: LookupError: 2019_miami: requested 'Miami Grand Prix' but FastF1 fuzzy-matched 'Italian Grand Prix' — edition most likely not held that season
- 2019_zandvoort: LookupError: 2019_zandvoort: requested 'Dutch Grand Prix' but FastF1 fuzzy-matched 'Chinese Grand Prix' — edition most likely not held that season
- 2019_mexico_city: DataNotLoadedError: The data you are trying to access has not been loaded yet. See `Session.load`
- 2020_jeddah: LookupError: 2020_jeddah: requested 'Saudi Arabian Grand Prix' but FastF1 fuzzy-matched 'Austrian Grand Prix' — edition most likely not held that season
- 2020_melbourne: LookupError: 2020_melbourne: requested 'Australian Grand Prix' but FastF1 fuzzy-matched 'Austrian Grand Prix' — edition most likely not held that season
- 2020_miami: LookupError: 2020_miami: requested 'Miami Grand Prix' but FastF1 fuzzy-matched 'Italian Grand Prix' — edition most likely not held that season
- 2020_monaco: LookupError: 2020_monaco: requested 'Monaco Grand Prix' but FastF1 fuzzy-matched 'Italian Grand Prix' — edition most likely not held that season
- 2020_baku: LookupError: 2020_baku: requested 'Azerbaijan Grand Prix' but FastF1 fuzzy-matched 'Austrian Grand Prix' — edition most likely not held that season
- 2020_montreal: LookupError: 2020_montreal: requested 'Canadian Grand Prix' but FastF1 fuzzy-matched 'Hungarian Grand Prix' — edition most likely not held that season
- 2020_ricard: LookupError: 2020_ricard: requested 'French Grand Prix' but FastF1 fuzzy-matched 'Belgian Grand Prix' — edition most likely not held that season
- 2020_zandvoort: LookupError: 2020_zandvoort: requested 'Dutch Grand Prix' but FastF1 fuzzy-matched 'Russian Grand Prix' — edition most likely not held that season
- 2020_singapore: LookupError: 2020_singapore: requested 'Singapore Grand Prix' but FastF1 fuzzy-matched 'Hungarian Grand Prix' — edition most likely not held that season
- 2020_suzuka: LookupError: 2020_suzuka: requested 'Japanese Grand Prix' but FastF1 fuzzy-matched 'Spanish Grand Prix' — edition most likely not held that season
- 2020_austin: LookupError: 2020_austin: requested 'United States Grand Prix' but FastF1 fuzzy-matched 'Hungarian Grand Prix' — edition most likely not held that season
- 2020_mexico_city: LookupError: 2020_mexico_city: requested 'Mexican Grand Prix' but FastF1 fuzzy-matched 'Belgian Grand Prix' — edition most likely not held that season
- 2020_interlagos: LookupError: 2020_interlagos: requested 'Brazilian Grand Prix' but FastF1 fuzzy-matched 'Belgian Grand Prix' — edition most likely not held that season
- 2021_melbourne: LookupError: 2021_melbourne: requested 'Australian Grand Prix' but FastF1 fuzzy-matched 'Austrian Grand Prix' — edition most likely not held that season
- 2021_miami: LookupError: 2021_miami: requested 'Miami Grand Prix' but FastF1 fuzzy-matched 'Italian Grand Prix' — edition most likely not held that season
- 2021_montreal: LookupError: 2021_montreal: requested 'Canadian Grand Prix' but FastF1 fuzzy-matched 'Hungarian Grand Prix' — edition most likely not held that season
- 2021_singapore: LookupError: 2021_singapore: requested 'Singapore Grand Prix' but FastF1 fuzzy-matched 'Hungarian Grand Prix' — edition most likely not held that season
- 2021_suzuka: LookupError: 2021_suzuka: requested 'Japanese Grand Prix' but FastF1 fuzzy-matched 'Spanish Grand Prix' — edition most likely not held that season

(2020-2021 gaps are COVID cancellations — those races never took place.)

## austin (7 editions, 392 race laps observed)

| Season | Laps | SC | VSC | Red | SC deploy laps | VSC deploy laps |
|---|---|---|---|---|---|---|
| 2018 | 56 | 0 | 1 | 0 | - | [11] |
| 2019 | 56 | 0 | 0 | 0 | - | - |
| 2021 | 56 | 0 | 1 | 0 | - | [28] |
| 2022 | 56 | 2 | 0 | 0 | [18, 22] | - |
| 2023 | 56 | 0 | 0 | 0 | - | - |
| 2024 | 56 | 1 | 0 | 0 | [3] | - |
| 2025 | 56 | 0 | 1 | 0 | - | [7] |

**SC** — races with >= 1: 2/7; deployments: 3.
- P(>= 1 per race) = 0.312 [0.065, 0.648]
- Per-lap deployment rate = 0.00893 [0.00216, 0.02042]
- Durations (laps): n=3, mean=3.7, min=3, max=4

**VSC** — races with >= 1: 3/7; deployments: 3.
- P(>= 1 per race) = 0.438 [0.139, 0.765]
- Per-lap deployment rate = 0.00893 [0.00216, 0.02042]
- Durations (laps): n=3, mean=2.0, min=1, max=3

## bahrain (8 editions, 455 race laps observed)

| Season | Laps | SC | VSC | Red | SC deploy laps | VSC deploy laps |
|---|---|---|---|---|---|---|
| 2018 | 57 | 0 | 1 | 0 | - | [2] |
| 2019 | 57 | 1 | 0 | 0 | [55] | - |
| 2020 | 57 | 2 | 0 | 1 | [3, 55] | - |
| 2021 | 56 | 1 | 1 | 0 | [1] | [4] |
| 2022 | 57 | 1 | 1 | 0 | [46] | [46] |
| 2023 | 57 | 0 | 1 | 0 | - | [41] |
| 2024 | 57 | 0 | 0 | 0 | - | - |
| 2025 | 57 | 1 | 0 | 0 | [32] | - |

**SC** — races with >= 1: 5/8; deployments: 6.
- P(>= 1 per race) = 0.611 [0.295, 0.881]
- Per-lap deployment rate = 0.01429 [0.00550, 0.02718]
- Durations (laps): n=6, mean=4.0, min=3, max=6

**VSC** — races with >= 1: 4/8; deployments: 4.
- P(>= 1 per race) = 0.500 [0.199, 0.801]
- Per-lap deployment rate = 0.00989 [0.00297, 0.02090]
- Durations (laps): n=4, mean=2.0, min=1, max=3

## baku (7 editions, 357 race laps observed)

| Season | Laps | SC | VSC | Red | SC deploy laps | VSC deploy laps |
|---|---|---|---|---|---|---|
| 2018 | 51 | 2 | 0 | 0 | [1, 40] | - |
| 2019 | 51 | 0 | 1 | 0 | - | [40] |
| 2021 | 51 | 2 | 0 | 1 | [31, 47] | - |
| 2022 | 51 | 0 | 2 | 0 | - | [9, 33] |
| 2023 | 51 | 1 | 0 | 0 | [11] | - |
| 2024 | 51 | 0 | 1 | 0 | - | [51] |
| 2025 | 51 | 1 | 0 | 0 | [1] | - |

**SC** — races with >= 1: 4/7; deployments: 6.
- P(>= 1 per race) = 0.562 [0.235, 0.861]
- Per-lap deployment rate = 0.01821 [0.00702, 0.03464]
- Durations (laps): n=6, mean=4.5, min=2, max=8

**VSC** — races with >= 1: 3/7; deployments: 4.
- P(>= 1 per race) = 0.438 [0.139, 0.765]
- Per-lap deployment rate = 0.01261 [0.00378, 0.02664]
- Durations (laps): n=4, mean=2.0, min=1, max=3

## barcelona (8 editions, 528 race laps observed)

| Season | Laps | SC | VSC | Red | SC deploy laps | VSC deploy laps |
|---|---|---|---|---|---|---|
| 2018 | 66 | 1 | 1 | 0 | [1] | [41] |
| 2019 | 66 | 1 | 0 | 0 | [46] | - |
| 2020 | 66 | 0 | 0 | 0 | - | - |
| 2021 | 66 | 1 | 0 | 0 | [8] | - |
| 2022 | 66 | 0 | 0 | 0 | - | - |
| 2023 | 66 | 0 | 0 | 0 | - | - |
| 2024 | 66 | 0 | 0 | 0 | - | - |
| 2025 | 66 | 1 | 0 | 0 | [55] | - |

**SC** — races with >= 1: 4/8; deployments: 4.
- P(>= 1 per race) = 0.500 [0.199, 0.801]
- Per-lap deployment rate = 0.00852 [0.00256, 0.01801]
- Durations (laps): n=4, mean=5.5, min=3, max=7

**VSC** — races with >= 1: 1/8; deployments: 1.
- P(>= 1 per race) = 0.167 [0.014, 0.454]
- Per-lap deployment rate = 0.00284 [0.00020, 0.00885]
- Durations (laps): n=1, mean=3.0, min=3, max=3

## hungaroring (8 editions, 560 race laps observed)

| Season | Laps | SC | VSC | Red | SC deploy laps | VSC deploy laps |
|---|---|---|---|---|---|---|
| 2018 | 70 | 0 | 2 | 0 | - | [6, 51] |
| 2019 | 70 | 0 | 0 | 0 | - | - |
| 2020 | 70 | 0 | 0 | 0 | - | - |
| 2021 | 70 | 1 | 0 | 1 | [1] | - |
| 2022 | 70 | 0 | 2 | 0 | - | [2, 68] |
| 2023 | 70 | 0 | 0 | 0 | - | - |
| 2024 | 70 | 0 | 0 | 0 | - | - |
| 2025 | 70 | 0 | 0 | 0 | - | - |

**SC** — races with >= 1: 1/8; deployments: 1.
- P(>= 1 per race) = 0.167 [0.014, 0.454]
- Per-lap deployment rate = 0.00268 [0.00019, 0.00835]
- Durations (laps): n=1, mean=2.0, min=2, max=2

**VSC** — races with >= 1: 2/8; deployments: 4.
- P(>= 1 per race) = 0.278 [0.056, 0.592]
- Per-lap deployment rate = 0.00804 [0.00241, 0.01698]
- Durations (laps): n=4, mean=2.0, min=2, max=2

## imola (5 editions, 315 race laps observed)

| Season | Laps | SC | VSC | Red | SC deploy laps | VSC deploy laps |
|---|---|---|---|---|---|---|
| 2020 | 63 | 1 | 1 | 0 | [51] | [30] |
| 2021 | 63 | 2 | 0 | 1 | [2, 32] | - |
| 2022 | 63 | 1 | 0 | 0 | [1] | - |
| 2024 | 63 | 0 | 0 | 0 | - | - |
| 2025 | 63 | 1 | 1 | 0 | [46] | [29] |

**SC** — races with >= 1: 4/5; deployments: 5.
- P(>= 1 per race) = 0.750 [0.371, 0.977]
- Per-lap deployment rate = 0.01746 [0.00606, 0.03479]
- Durations (laps): n=5, mean=5.2, min=2, max=8

**VSC** — races with >= 1: 2/5; deployments: 2.
- P(>= 1 per race) = 0.417 [0.094, 0.791]
- Per-lap deployment rate = 0.00794 [0.00132, 0.02037]
- Durations (laps): n=2, mean=2.5, min=2, max=3

## interlagos (7 editions, 495 race laps observed)

| Season | Laps | SC | VSC | Red | SC deploy laps | VSC deploy laps |
|---|---|---|---|---|---|---|
| 2018 | 71 | 0 | 0 | 0 | - | - |
| 2019 | 71 | 2 | 0 | 0 | [54, 66] | - |
| 2021 | 71 | 1 | 2 | 0 | [6] | [12, 30] |
| 2022 | 71 | 2 | 1 | 0 | [1, 54] | [53] |
| 2023 | 71 | 1 | 0 | 1 | [1] | - |
| 2024 | 69 | 2 | 1 | 1 | [30, 39] | [28] |
| 2025 | 71 | 1 | 1 | 0 | [2] | [7] |

**SC** — races with >= 1: 6/7; deployments: 9.
- P(>= 1 per race) = 0.812 [0.499, 0.984]
- Per-lap deployment rate = 0.01919 [0.00900, 0.03318]
- Durations (laps): n=9, mean=4.3, min=2, max=6

**VSC** — races with >= 1: 4/7; deployments: 5.
- P(>= 1 per race) = 0.562 [0.235, 0.861]
- Per-lap deployment rate = 0.01111 [0.00385, 0.02214]
- Durations (laps): n=5, mean=2.2, min=2, max=3

## jeddah (5 editions, 250 race laps observed)

| Season | Laps | SC | VSC | Red | SC deploy laps | VSC deploy laps |
|---|---|---|---|---|---|---|
| 2021 | 50 | 1 | 4 | 2 | [10] | [23, 28, 29, 36] |
| 2022 | 50 | 1 | 2 | 0 | [16] | [16, 38] |
| 2023 | 50 | 1 | 0 | 0 | [18] | - |
| 2024 | 50 | 1 | 0 | 0 | [7] | - |
| 2025 | 50 | 1 | 0 | 0 | [1] | - |

**SC** — races with >= 1: 5/5; deployments: 5.
- P(>= 1 per race) = 0.917 [0.621, 1.000]
- Per-lap deployment rate = 0.02200 [0.00763, 0.04384]
- Durations (laps): n=5, mean=3.6, min=3, max=5

**VSC** — races with >= 1: 2/5; deployments: 6.
- P(>= 1 per race) = 0.417 [0.094, 0.791]
- Per-lap deployment rate = 0.02600 [0.01002, 0.04947]
- Durations (laps): n=6, mean=2.3, min=1, max=5

## las_vegas (3 editions, 150 race laps observed)

| Season | Laps | SC | VSC | Red | SC deploy laps | VSC deploy laps |
|---|---|---|---|---|---|---|
| 2023 | 50 | 2 | 1 | 0 | [3, 26] | [1] |
| 2024 | 50 | 0 | 0 | 0 | - | - |
| 2025 | 50 | 0 | 2 | 0 | - | [2, 16] |

**SC** — races with >= 1: 1/3; deployments: 2.
- P(>= 1 per race) = 0.375 [0.039, 0.823]
- Per-lap deployment rate = 0.01667 [0.00277, 0.04278]
- Durations (laps): n=2, mean=3.5, min=3, max=4

**VSC** — races with >= 1: 2/3; deployments: 3.
- P(>= 1 per race) = 0.625 [0.177, 0.961]
- Per-lap deployment rate = 0.02333 [0.00563, 0.05338]
- Durations (laps): n=3, mean=2.0, min=1, max=3

## losail (3 editions, 171 race laps observed)

| Season | Laps | SC | VSC | Red | SC deploy laps | VSC deploy laps |
|---|---|---|---|---|---|---|
| 2023 | 57 | 1 | 0 | 0 | [1] | - |
| 2024 | 57 | 3 | 1 | 0 | [1, 35, 40] | [40] |
| 2025 | 57 | 1 | 0 | 0 | [7] | - |

**SC** — races with >= 1: 3/3; deployments: 5.
- P(>= 1 per race) = 0.875 [0.464, 1.000]
- Per-lap deployment rate = 0.03216 [0.01116, 0.06409]
- Durations (laps): n=5, mean=4.0, min=3, max=5

**VSC** — races with >= 1: 1/3; deployments: 1.
- P(>= 1 per race) = 0.375 [0.039, 0.823]
- Per-lap deployment rate = 0.00877 [0.00063, 0.02733]
- Durations (laps): n=1, mean=1.0, min=1, max=1

## melbourne (6 editions, 347 race laps observed)

| Season | Laps | SC | VSC | Red | SC deploy laps | VSC deploy laps |
|---|---|---|---|---|---|---|
| 2018 | 58 | 1 | 1 | 0 | [28] | [26] |
| 2019 | 58 | 0 | 0 | 0 | - | - |
| 2022 | 58 | 2 | 2 | 0 | [3, 23] | [3, 39] |
| 2023 | 58 | 3 | 1 | 4 | [1, 7, 54] | [18] |
| 2024 | 58 | 0 | 2 | 0 | - | [17, 58] |
| 2025 | 57 | 3 | 0 | 0 | [1, 34, 47] | - |

**SC** — races with >= 1: 4/6; deployments: 9.
- P(>= 1 per race) = 0.643 [0.286, 0.923]
- Per-lap deployment rate = 0.02738 [0.01283, 0.04734]
- Durations (laps): n=9, mean=4.3, min=2, max=8

**VSC** — races with >= 1: 4/6; deployments: 6.
- P(>= 1 per race) = 0.643 [0.286, 0.923]
- Per-lap deployment rate = 0.01873 [0.00722, 0.03564]
- Durations (laps): n=6, mean=1.8, min=1, max=3

## mexico_city (6 editions, 426 race laps observed)

| Season | Laps | SC | VSC | Red | SC deploy laps | VSC deploy laps |
|---|---|---|---|---|---|---|
| 2018 | 71 | 0 | 3 | 0 | - | [5, 31, 62] |
| 2021 | 71 | 1 | 0 | 0 | [1] | - |
| 2022 | 71 | 0 | 1 | 0 | - | [65] |
| 2023 | 71 | 2 | 1 | 1 | [33, 35] | [5] |
| 2024 | 71 | 1 | 0 | 0 | [1] | - |
| 2025 | 71 | 0 | 1 | 0 | - | [70] |

**SC** — races with >= 1: 3/6; deployments: 4.
- P(>= 1 per race) = 0.500 [0.167, 0.833]
- Per-lap deployment rate = 0.01056 [0.00317, 0.02233]
- Durations (laps): n=4, mean=3.2, min=1, max=6

**VSC** — races with >= 1: 4/6; deployments: 6.
- P(>= 1 per race) = 0.643 [0.286, 0.923]
- Per-lap deployment rate = 0.01526 [0.00588, 0.02903]
- Durations (laps): n=6, mean=2.0, min=1, max=3

## miami (4 editions, 228 race laps observed)

| Season | Laps | SC | VSC | Red | SC deploy laps | VSC deploy laps |
|---|---|---|---|---|---|---|
| 2022 | 57 | 1 | 1 | 0 | [41] | [41] |
| 2023 | 57 | 0 | 0 | 0 | - | - |
| 2024 | 57 | 1 | 1 | 0 | [28] | [23] |
| 2025 | 57 | 0 | 3 | 0 | - | [2, 29, 33] |

**SC** — races with >= 1: 2/4; deployments: 2.
- P(>= 1 per race) = 0.500 [0.123, 0.877]
- Per-lap deployment rate = 0.01096 [0.00182, 0.02814]
- Durations (laps): n=2, mean=5.5, min=5, max=6

**VSC** — races with >= 1: 3/4; deployments: 5.
- P(>= 1 per race) = 0.700 [0.284, 0.972]
- Per-lap deployment rate = 0.02412 [0.00837, 0.04807]
- Durations (laps): n=5, mean=1.6, min=1, max=2

## monaco (7 editions, 532 race laps observed)

| Season | Laps | SC | VSC | Red | SC deploy laps | VSC deploy laps |
|---|---|---|---|---|---|---|
| 2018 | 78 | 0 | 1 | 0 | - | [73] |
| 2019 | 78 | 1 | 0 | 0 | [11] | - |
| 2021 | 78 | 0 | 0 | 0 | - | - |
| 2022 | 64 | 2 | 1 | 2 | [2, 27] | [27] |
| 2023 | 78 | 0 | 0 | 0 | - | - |
| 2024 | 78 | 1 | 0 | 1 | [2] | - |
| 2025 | 78 | 0 | 1 | 0 | - | [2] |

**SC** — races with >= 1: 3/7; deployments: 4.
- P(>= 1 per race) = 0.438 [0.139, 0.765]
- Per-lap deployment rate = 0.00846 [0.00254, 0.01788]
- Durations (laps): n=4, mean=2.5, min=1, max=4

**VSC** — races with >= 1: 3/7; deployments: 3.
- P(>= 1 per race) = 0.438 [0.139, 0.765]
- Per-lap deployment rate = 0.00658 [0.00159, 0.01505]
- Durations (laps): n=3, mean=2.0, min=1, max=3

## montreal (6 editions, 420 race laps observed)

| Season | Laps | SC | VSC | Red | SC deploy laps | VSC deploy laps |
|---|---|---|---|---|---|---|
| 2018 | 70 | 1 | 0 | 0 | [1] | - |
| 2019 | 70 | 0 | 0 | 0 | - | - |
| 2022 | 70 | 1 | 2 | 0 | [49] | [9, 20] |
| 2023 | 70 | 1 | 1 | 0 | [12] | [8] |
| 2024 | 70 | 2 | 0 | 0 | [25, 54] | - |
| 2025 | 70 | 1 | 0 | 0 | [67] | - |

**SC** — races with >= 1: 5/6; deployments: 6.
- P(>= 1 per race) = 0.786 [0.442, 0.981]
- Per-lap deployment rate = 0.01548 [0.00596, 0.02945]
- Durations (laps): n=6, mean=4.8, min=4, max=6

**VSC** — races with >= 1: 2/6; deployments: 3.
- P(>= 1 per race) = 0.357 [0.077, 0.714]
- Per-lap deployment rate = 0.00833 [0.00201, 0.01906]
- Durations (laps): n=3, mean=1.7, min=1, max=2

## monza (7 editions, 369 race laps observed)

| Season | Laps | SC | VSC | Red | SC deploy laps | VSC deploy laps |
|---|---|---|---|---|---|---|
| 2019 | 53 | 0 | 2 | 0 | - | [29, 31] |
| 2020 | 53 | 2 | 0 | 1 | [20, 25] | - |
| 2021 | 53 | 1 | 2 | 0 | [26] | [1, 44] |
| 2022 | 53 | 1 | 1 | 0 | [48] | [12] |
| 2023 | 51 | 0 | 0 | 0 | - | - |
| 2024 | 53 | 0 | 0 | 0 | - | - |
| 2025 | 53 | 0 | 0 | 0 | - | - |

**SC** — races with >= 1: 3/7; deployments: 4.
- P(>= 1 per race) = 0.438 [0.139, 0.765]
- Per-lap deployment rate = 0.01220 [0.00366, 0.02578]
- Durations (laps): n=4, mean=4.2, min=2, max=6

**VSC** — races with >= 1: 3/7; deployments: 5.
- P(>= 1 per race) = 0.438 [0.139, 0.765]
- Per-lap deployment rate = 0.01491 [0.00517, 0.02970]
- Durations (laps): n=5, mean=1.4, min=1, max=2

## red_bull_ring (8 editions, 564 race laps observed)

| Season | Laps | SC | VSC | Red | SC deploy laps | VSC deploy laps |
|---|---|---|---|---|---|---|
| 2018 | 71 | 0 | 1 | 0 | - | [15] |
| 2019 | 71 | 0 | 0 | 0 | - | - |
| 2020 | 68 | 3 | 0 | 0 | [25, 50, 53] | - |
| 2021 | 71 | 1 | 0 | 0 | [1] | - |
| 2022 | 71 | 0 | 1 | 0 | - | [58] |
| 2023 | 71 | 1 | 1 | 0 | [1] | [14] |
| 2024 | 71 | 0 | 1 | 0 | - | [66] |
| 2025 | 70 | 1 | 0 | 0 | [1] | - |

**SC** — races with >= 1: 4/8; deployments: 6.
- P(>= 1 per race) = 0.500 [0.199, 0.801]
- Per-lap deployment rate = 0.01152 [0.00444, 0.02193]
- Durations (laps): n=6, mean=4.5, min=3, max=8

**VSC** — races with >= 1: 4/8; deployments: 4.
- P(>= 1 per race) = 0.500 [0.199, 0.801]
- Per-lap deployment rate = 0.00798 [0.00239, 0.01686]
- Durations (laps): n=4, mean=2.2, min=1, max=3

## ricard (4 editions, 212 race laps observed)

| Season | Laps | SC | VSC | Red | SC deploy laps | VSC deploy laps |
|---|---|---|---|---|---|---|
| 2018 | 53 | 1 | 1 | 0 | [1] | [52] |
| 2019 | 53 | 0 | 1 | 0 | - | [50] |
| 2021 | 53 | 0 | 0 | 0 | - | - |
| 2022 | 53 | 1 | 1 | 0 | [18] | [50] |

**SC** — races with >= 1: 2/4; deployments: 2.
- P(>= 1 per race) = 0.500 [0.123, 0.877]
- Per-lap deployment rate = 0.01179 [0.00196, 0.03027]
- Durations (laps): n=2, mean=4.0, min=3, max=5

**VSC** — races with >= 1: 3/4; deployments: 3.
- P(>= 1 per race) = 0.700 [0.284, 0.972]
- Per-lap deployment rate = 0.01651 [0.00399, 0.03777]
- Durations (laps): n=3, mean=1.7, min=1, max=2

## shanghai (2 editions, 112 race laps observed)

| Season | Laps | SC | VSC | Red | SC deploy laps | VSC deploy laps |
|---|---|---|---|---|---|---|
| 2024 | 56 | 2 | 1 | 0 | [23, 27] | [22] |
| 2025 | 56 | 0 | 0 | 0 | - | - |

**SC** — races with >= 1: 1/2; deployments: 2.
- P(>= 1 per race) = 0.500 [0.061, 0.939]
- Per-lap deployment rate = 0.02232 [0.00371, 0.05729]
- Durations (laps): n=2, mean=4.5, min=4, max=5

**VSC** — races with >= 1: 1/2; deployments: 1.
- P(>= 1 per race) = 0.500 [0.061, 0.939]
- Per-lap deployment rate = 0.01339 [0.00096, 0.04173]
- Durations (laps): n=1, mean=2.0, min=2, max=2

## silverstone (8 editions, 416 race laps observed)

| Season | Laps | SC | VSC | Red | SC deploy laps | VSC deploy laps |
|---|---|---|---|---|---|---|
| 2018 | 52 | 2 | 0 | 0 | [33, 38] | - |
| 2019 | 52 | 1 | 0 | 0 | [20] | - |
| 2020 | 52 | 2 | 0 | 0 | [2, 13] | - |
| 2021 | 52 | 1 | 0 | 1 | [1] | - |
| 2022 | 52 | 1 | 0 | 1 | [39] | - |
| 2023 | 52 | 1 | 1 | 0 | [33] | [33] |
| 2024 | 52 | 0 | 0 | 0 | - | - |
| 2025 | 52 | 2 | 2 | 0 | [14, 18] | [2, 5] |

**SC** — races with >= 1: 7/8; deployments: 10.
- P(>= 1 per race) = 0.833 [0.546, 0.986]
- Per-lap deployment rate = 0.02524 [0.01236, 0.04264]
- Durations (laps): n=10, mean=4.3, min=2, max=6

**VSC** — races with >= 1: 2/8; deployments: 3.
- P(>= 1 per race) = 0.278 [0.056, 0.592]
- Per-lap deployment rate = 0.00841 [0.00203, 0.01925]
- Durations (laps): n=3, mean=2.3, min=1, max=3

## singapore (6 editions, 367 race laps observed)

| Season | Laps | SC | VSC | Red | SC deploy laps | VSC deploy laps |
|---|---|---|---|---|---|---|
| 2018 | 61 | 1 | 0 | 0 | [1] | - |
| 2019 | 61 | 3 | 0 | 0 | [36, 44, 50] | - |
| 2022 | 59 | 2 | 3 | 0 | [8, 36] | [22, 26, 28] |
| 2023 | 62 | 1 | 1 | 0 | [20] | [44] |
| 2024 | 62 | 0 | 0 | 0 | - | - |
| 2025 | 62 | 0 | 0 | 0 | - | - |

**SC** — races with >= 1: 4/6; deployments: 7.
- P(>= 1 per race) = 0.643 [0.286, 0.923]
- Per-lap deployment rate = 0.02044 [0.00853, 0.03745]
- Durations (laps): n=7, mean=3.6, min=2, max=5

**VSC** — races with >= 1: 2/6; deployments: 4.
- P(>= 1 per race) = 0.357 [0.077, 0.714]
- Per-lap deployment rate = 0.01226 [0.00368, 0.02592]
- Durations (laps): n=4, mean=2.2, min=2, max=3

## spa (8 editions, 311 race laps observed)

| Season | Laps | SC | VSC | Red | SC deploy laps | VSC deploy laps |
|---|---|---|---|---|---|---|
| 2018 | 44 | 1 | 0 | 0 | [1] | - |
| 2019 | 44 | 1 | 0 | 0 | [1] | - |
| 2020 | 44 | 1 | 0 | 0 | [11] | - |
| 2021 | 3 | 0 | 0 | 2 | - | - |
| 2022 | 44 | 1 | 0 | 0 | [2] | - |
| 2023 | 44 | 0 | 0 | 0 | - | - |
| 2024 | 44 | 0 | 0 | 0 | - | - |
| 2025 | 44 | 1 | 0 | 1 | [1] | - |

**SC** — races with >= 1: 5/8; deployments: 5.
- P(>= 1 per race) = 0.611 [0.295, 0.881]
- Per-lap deployment rate = 0.01768 [0.00613, 0.03524]
- Durations (laps): n=5, mean=3.8, min=3, max=4

**VSC** — races with >= 1: 0/8; deployments: 0.
- P(>= 1 per race) = 0.056 [0.000, 0.262]
- Per-lap deployment rate = 0.00161 [0.00000, 0.00808]
- Durations: no events observed

## suzuka (6 editions, 294 race laps observed)

| Season | Laps | SC | VSC | Red | SC deploy laps | VSC deploy laps |
|---|---|---|---|---|---|---|
| 2018 | 53 | 1 | 1 | 0 | [4] | [41] |
| 2019 | 53 | 0 | 0 | 0 | - | - |
| 2022 | 29 | 1 | 0 | 1 | [1] | - |
| 2023 | 53 | 1 | 1 | 0 | [1] | [14] |
| 2024 | 53 | 0 | 0 | 1 | - | - |
| 2025 | 53 | 0 | 0 | 0 | - | - |

**SC** — races with >= 1: 3/6; deployments: 3.
- P(>= 1 per race) = 0.500 [0.167, 0.833]
- Per-lap deployment rate = 0.01190 [0.00287, 0.02723]
- Durations (laps): n=3, mean=3.3, min=2, max=4

**VSC** — races with >= 1: 2/6; deployments: 2.
- P(>= 1 per race) = 0.357 [0.077, 0.714]
- Per-lap deployment rate = 0.00850 [0.00141, 0.02182]
- Durations (laps): n=2, mean=1.5, min=1, max=2

## yas_marina (8 editions, 455 race laps observed)

| Season | Laps | SC | VSC | Red | SC deploy laps | VSC deploy laps |
|---|---|---|---|---|---|---|
| 2018 | 55 | 1 | 1 | 0 | [1] | [7] |
| 2019 | 55 | 0 | 0 | 0 | - | - |
| 2020 | 55 | 1 | 1 | 0 | [11] | [10] |
| 2021 | 58 | 1 | 1 | 0 | [53] | [36] |
| 2022 | 58 | 0 | 0 | 0 | - | - |
| 2023 | 58 | 0 | 0 | 0 | - | - |
| 2024 | 58 | 0 | 1 | 0 | - | [2] |
| 2025 | 58 | 0 | 0 | 0 | - | - |

**SC** — races with >= 1: 3/8; deployments: 3.
- P(>= 1 per race) = 0.389 [0.119, 0.705]
- Per-lap deployment rate = 0.00769 [0.00186, 0.01760]
- Durations (laps): n=3, mean=4.0, min=3, max=5

**VSC** — races with >= 1: 4/8; deployments: 4.
- P(>= 1 per race) = 0.500 [0.199, 0.801]
- Per-lap deployment rate = 0.00989 [0.00297, 0.02090]
- Durations (laps): n=4, mean=2.2, min=2, max=3

## zandvoort (5 editions, 360 race laps observed)

| Season | Laps | SC | VSC | Red | SC deploy laps | VSC deploy laps |
|---|---|---|---|---|---|---|
| 2021 | 72 | 0 | 0 | 0 | - | - |
| 2022 | 72 | 1 | 1 | 0 | [56] | [48] |
| 2023 | 72 | 2 | 1 | 1 | [16, 65] | [64] |
| 2024 | 72 | 0 | 0 | 0 | - | - |
| 2025 | 72 | 3 | 1 | 0 | [23, 53, 65] | [31] |

**SC** — races with >= 1: 3/5; deployments: 6.
- P(>= 1 per race) = 0.583 [0.209, 0.906]
- Per-lap deployment rate = 0.01806 [0.00696, 0.03436]
- Durations (laps): n=6, mean=4.3, min=2, max=6

**VSC** — races with >= 1: 3/5; deployments: 3.
- P(>= 1 per race) = 0.583 [0.209, 0.906]
- Per-lap deployment rate = 0.00972 [0.00235, 0.02224]
- Durations (laps): n=3, mean=2.0, min=1, max=3

## Statistical reliability — read this before trusting any number

- **6-8 races per circuit is a structurally small sample.** The
  credible intervals span factors of 2-4x; any strategy conclusion
  sensitive to the exact SC probability inside those bounds is not
  supported by this data.
- **Deployment laps cluster early** (lap-1 incidents) at some
  circuits; the per-lap rate model assumes a constant hazard and
  therefore understates lap-1 risk and overstates mid-race risk.
  Listed deployment laps above let the reader judge; a two-bin
  hazard is possible future work if Phase 5 shows it matters.
- **Circuit changes are absorbed silently** (e.g. Singapore's 2023
  layout shortening) — the model treats all editions of a circuit
  as exchangeable, which is an approximation.
- **Red flags are counted but not modelled** (too rare: the
  simulator scope excludes them, documented in Phase 4).
- SC and VSC are modelled independently; in reality a VSC sometimes
  escalates into an SC, so the two rates are not fully independent.
