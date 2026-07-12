# Phase 3 — Safety Car / VSC probability model

Event history 2018-2025 extracted from `TrackStatus` (SC=code 4,
VSC=codes 6/7, red flag=code 5). Estimates are posterior means with
95% equal-tailed credible intervals under a Jeffreys prior — with
6-8 editions per circuit, interval width IS the result; point
values alone would be false precision.

## Editions not included

- 2020_monaco: LookupError: 2020_monaco: requested 'Monaco' but FastF1 fuzzy-matched 'Italian Grand Prix' — edition most likely not held that season
- 2020_singapore: LookupError: 2020_singapore: requested 'Singapore' but FastF1 fuzzy-matched 'Hungarian Grand Prix' — edition most likely not held that season
- 2021_singapore: LookupError: 2021_singapore: requested 'Singapore' but FastF1 fuzzy-matched 'Hungarian Grand Prix' — edition most likely not held that season
- 2020_suzuka: LookupError: 2020_suzuka: requested 'Japanese' but FastF1 fuzzy-matched 'Spanish Grand Prix' — edition most likely not held that season
- 2021_suzuka: LookupError: 2021_suzuka: requested 'Japanese' but FastF1 fuzzy-matched 'Spanish Grand Prix' — edition most likely not held that season

(2020-2021 gaps are COVID cancellations — those races never took place.)

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
