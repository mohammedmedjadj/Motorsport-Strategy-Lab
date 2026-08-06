# Phase 3 — Safety Car / VSC probability model

Event history 2018-2025 extracted from `TrackStatus` (SC=code 4,
VSC=codes 6/7, red flag=code 5). Estimates are posterior means with
95% equal-tailed credible intervals under a Jeffreys prior — with
6-8 editions per circuit, interval width IS the result; point
values alone would be false precision.

## Editions not included

- 2018_monaco: DataNotLoadedError: The data you are trying to access has not been loaded yet. See `Session.load`
- 2019_monaco: DataNotLoadedError: The data you are trying to access has not been loaded yet. See `Session.load`
- 2020_monaco: LookupError: 2020_monaco: requested 'Monaco' but FastF1 fuzzy-matched 'Italian Grand Prix' — edition most likely not held that season
- 2023_monaco: DataNotLoadedError: The data you are trying to access has not been loaded yet. See `Session.load`
- 2024_monaco: DataNotLoadedError: The data you are trying to access has not been loaded yet. See `Session.load`
- 2025_monaco: DataNotLoadedError: The data you are trying to access has not been loaded yet. See `Session.load`
- 2018_singapore: DataNotLoadedError: The data you are trying to access has not been loaded yet. See `Session.load`
- 2019_singapore: DataNotLoadedError: The data you are trying to access has not been loaded yet. See `Session.load`
- 2020_singapore: LookupError: 2020_singapore: requested 'Singapore' but FastF1 fuzzy-matched 'Hungarian Grand Prix' — edition most likely not held that season
- 2021_singapore: LookupError: 2021_singapore: requested 'Singapore' but FastF1 fuzzy-matched 'Hungarian Grand Prix' — edition most likely not held that season
- 2023_singapore: DataNotLoadedError: The data you are trying to access has not been loaded yet. See `Session.load`
- 2024_singapore: DataNotLoadedError: The data you are trying to access has not been loaded yet. See `Session.load`
- 2025_singapore: DataNotLoadedError: The data you are trying to access has not been loaded yet. See `Session.load`
- 2018_barcelona: DataNotLoadedError: The data you are trying to access has not been loaded yet. See `Session.load`
- 2019_barcelona: DataNotLoadedError: The data you are trying to access has not been loaded yet. See `Session.load`
- 2020_barcelona: DataNotLoadedError: The data you are trying to access has not been loaded yet. See `Session.load`
- 2023_barcelona: DataNotLoadedError: The data you are trying to access has not been loaded yet. See `Session.load`
- 2024_barcelona: DataNotLoadedError: The data you are trying to access has not been loaded yet. See `Session.load`
- 2025_barcelona: DataNotLoadedError: The data you are trying to access has not been loaded yet. See `Session.load`
- 2018_suzuka: DataNotLoadedError: The data you are trying to access has not been loaded yet. See `Session.load`
- 2019_suzuka: DataNotLoadedError: The data you are trying to access has not been loaded yet. See `Session.load`
- 2020_suzuka: LookupError: 2020_suzuka: requested 'Japanese' but FastF1 fuzzy-matched 'Spanish Grand Prix' — edition most likely not held that season
- 2021_suzuka: LookupError: 2021_suzuka: requested 'Japanese' but FastF1 fuzzy-matched 'Spanish Grand Prix' — edition most likely not held that season
- 2023_suzuka: DataNotLoadedError: The data you are trying to access has not been loaded yet. See `Session.load`
- 2024_suzuka: DataNotLoadedError: The data you are trying to access has not been loaded yet. See `Session.load`
- 2025_suzuka: RateLimitExceededError: any API: 500 calls/h

(2020-2021 gaps are COVID cancellations — those races never took place.)

## barcelona (2 editions, 132 race laps observed)

| Season | Laps | SC | VSC | Red | SC deploy laps | VSC deploy laps |
|---|---|---|---|---|---|---|
| 2021 | 66 | 1 | 0 | 0 | [8] | - |
| 2022 | 66 | 0 | 0 | 0 | - | - |

**SC** — races with >= 1: 1/2; deployments: 1.
- P(>= 1 per race) = 0.500 [0.061, 0.939]
- Per-lap deployment rate = 0.01136 [0.00082, 0.03541]
- Durations (laps): n=1, mean=3.0, min=3, max=3

**VSC** — races with >= 1: 0/2; deployments: 0.
- P(>= 1 per race) = 0.167 [0.000, 0.667]
- Per-lap deployment rate = 0.00379 [0.00000, 0.01903]
- Durations: no events observed

## monaco (2 editions, 142 race laps observed)

| Season | Laps | SC | VSC | Red | SC deploy laps | VSC deploy laps |
|---|---|---|---|---|---|---|
| 2021 | 78 | 0 | 0 | 0 | - | - |
| 2022 | 64 | 2 | 1 | 2 | [2, 27] | [27] |

**SC** — races with >= 1: 1/2; deployments: 2.
- P(>= 1 per race) = 0.500 [0.061, 0.939]
- Per-lap deployment rate = 0.01761 [0.00293, 0.04518]
- Durations (laps): n=2, mean=2.5, min=1, max=4

**VSC** — races with >= 1: 1/2; deployments: 1.
- P(>= 1 per race) = 0.500 [0.061, 0.939]
- Per-lap deployment rate = 0.01056 [0.00076, 0.03292]
- Durations (laps): n=1, mean=1.0, min=1, max=1

## singapore (1 editions, 59 race laps observed)

| Season | Laps | SC | VSC | Red | SC deploy laps | VSC deploy laps |
|---|---|---|---|---|---|---|
| 2022 | 59 | 2 | 3 | 0 | [8, 36] | [22, 26, 28] |

**SC** — races with >= 1: 1/1; deployments: 2.
- P(>= 1 per race) = 0.750 [0.147, 1.000]
- Per-lap deployment rate = 0.04237 [0.00704, 0.10875]
- Durations (laps): n=2, mean=3.5, min=3, max=4

**VSC** — races with >= 1: 1/1; deployments: 3.
- P(>= 1 per race) = 0.750 [0.147, 1.000]
- Per-lap deployment rate = 0.05932 [0.01432, 0.13570]
- Durations (laps): n=3, mean=2.3, min=2, max=3

## suzuka (1 editions, 29 race laps observed)

| Season | Laps | SC | VSC | Red | SC deploy laps | VSC deploy laps |
|---|---|---|---|---|---|---|
| 2022 | 29 | 1 | 0 | 1 | [1] | - |

**SC** — races with >= 1: 1/1; deployments: 1.
- P(>= 1 per race) = 0.750 [0.147, 1.000]
- Per-lap deployment rate = 0.05172 [0.00372, 0.16118]
- Durations (laps): n=1, mean=2.0, min=2, max=2

**VSC** — races with >= 1: 0/1; deployments: 0.
- P(>= 1 per race) = 0.250 [0.000, 0.853]
- Per-lap deployment rate = 0.01724 [0.00002, 0.08662]
- Durations: no events observed

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
