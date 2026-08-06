# Phase 4 — Monte Carlo strategy simulator

5000 draws per scenario, seed 20260712 (bit-reproducible).
Per draw, the engine resamples: degradation/fuel coefficients from
their Phase 2 CIs, SC/VSC per-lap hazards from their Phase 3 Gamma
posteriors, neutralisation durations from observed events, and lap
noise at the Phase 2 CV RMSE. Candidates share realisations (common
random numbers), so P(best) is a clean per-draw argmin.

## Data-derived inputs (measured, not assumed)

| Circuit | Green pace (s) | Pit loss (s, n) | SC pace ratio | VSC pace ratio | Lap noise (s) |
|---|---|---|---|---|---|
| barcelona | 80.6 | 23.5 (n=123) | 1.43 | 1.27 (pooled) | 0.57 |
| monaco | 78.5 | 19.1 (n=51) | 1.42 (pooled) | 1.37 | 1.26 |
| singapore | 98.7 | 27.3 (n=47) | 1.43 | 1.18 | 0.83 |
| suzuka | 96.4 | 23.5 (n=84) | 1.38 | 1.15 | 0.64 |

## Demo scenarios

Illustrative state: one third into the race on the starting MEDIUM,
target HARD; a rival 2.5s ahead planning to stop in 8 laps and one
3.0s behind planning to stop in 5.

### barcelona (lap 22/66, MEDIUM age 22 -> HARD)

- Best median pit lap: **35** — recommended window (medians within 0.5s): **[31, 32, 33, 34, 35, 36, 37, 38]**.
- Outcome spread at the best lap (p10-p90): 160.3s — this is the honest uncertainty of any single-race outcome.
- vs car_ahead: P(ahead) = 0.37 at lap 35; maximised at lap 45 (0.40).
- vs car_behind: P(ahead) = 0.74 at lap 35; maximised at lap 32 (0.75).

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_car_ahead | p_ahead_car_behind |
|---|---|---|---|---|---|---|---|
| 29 | 3531.35 | 3578.33 | 3517.66 | 3678.22 | 0.03 | 0.30 | 0.74 |
| 30 | 3530.89 | 3578.16 | 3517.57 | 3677.69 | 0.02 | 0.31 | 0.74 |
| 31 | 3530.61 | 3577.99 | 3517.49 | 3677.40 | 0.03 | 0.33 | 0.74 |
| 32 | 3530.43 | 3577.86 | 3517.36 | 3677.49 | 0.03 | 0.34 | 0.75 |
| 33 | 3530.25 | 3577.75 | 3517.23 | 3677.41 | 0.02 | 0.35 | 0.74 |
| 34 | 3530.20 | 3577.65 | 3517.15 | 3677.09 | 0.02 | 0.36 | 0.74 |
| 35 | 3530.17 | 3577.54 | 3517.04 | 3677.39 | 0.02 | 0.37 | 0.74 |
| 36 | 3530.26 | 3577.53 | 3516.81 | 3678.08 | 0.02 | 0.37 | 0.73 |
| 37 | 3530.31 | 3577.50 | 3516.63 | 3678.35 | 0.02 | 0.39 | 0.72 |
| 38 | 3530.55 | 3577.48 | 3516.38 | 3678.56 | 0.02 | 0.39 | 0.71 |
| 39 | 3530.78 | 3577.50 | 3516.12 | 3679.15 | 0.02 | 0.40 | 0.70 |
| 40 | 3531.18 | 3577.51 | 3515.89 | 3679.72 | 0.02 | 0.40 | 0.69 |

### monaco (lap 26/78, MEDIUM age 26 -> HARD)

- Best median pit lap: **27** — recommended window (medians within 0.5s): **[27, 28, 29, 30]**.
- Outcome spread at the best lap (p10-p90): 278.3s — this is the honest uncertainty of any single-race outcome.
- vs car_ahead: P(ahead) = 0.45 at lap 27; maximised at lap 27 (0.45).
- vs car_behind: P(ahead) = 0.60 at lap 27; maximised at lap 30 (0.60).

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_car_ahead | p_ahead_car_behind |
|---|---|---|---|---|---|---|---|
| 27 | 4073.29 | 4105.46 | 3993.59 | 4271.88 | 0.34 | 0.45 | 0.60 |
| 28 | 4073.40 | 4105.52 | 3993.61 | 4271.29 | 0.01 | 0.45 | 0.60 |
| 29 | 4073.47 | 4105.57 | 3993.77 | 4271.09 | 0.01 | 0.45 | 0.60 |
| 30 | 4073.65 | 4105.63 | 3993.93 | 4270.50 | 0.02 | 0.44 | 0.60 |
| 31 | 4073.92 | 4105.75 | 3994.14 | 4271.26 | 0.02 | 0.44 | 0.60 |
| 32 | 4073.81 | 4105.87 | 3994.35 | 4271.23 | 0.02 | 0.43 | 0.59 |
| 33 | 4073.89 | 4106.02 | 3994.42 | 4271.56 | 0.02 | 0.43 | 0.59 |
| 34 | 4074.00 | 4106.14 | 3994.60 | 4271.41 | 0.02 | 0.42 | 0.58 |
| 35 | 4074.16 | 4106.30 | 3994.82 | 4271.33 | 0.02 | 0.42 | 0.58 |
| 36 | 4074.57 | 4106.49 | 3995.10 | 4271.19 | 0.02 | 0.41 | 0.57 |
| 37 | 4074.69 | 4106.69 | 3995.24 | 4271.47 | 0.02 | 0.41 | 0.56 |
| 38 | 4075.13 | 4106.91 | 3995.47 | 4272.69 | 0.01 | 0.40 | 0.56 |

### singapore (lap 20/62, MEDIUM age 20 -> HARD)

- Best median pit lap: **38** — recommended window (medians within 0.5s): **[37, 38, 39]**.
- Outcome spread at the best lap (p10-p90): 516.1s — this is the honest uncertainty of any single-race outcome.
- vs car_ahead: P(ahead) = 0.50 at lap 38; maximised at lap 37 (0.51).
- vs car_behind: P(ahead) = 0.82 at lap 38; maximised at lap 36 (0.83).

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_car_ahead | p_ahead_car_behind |
|---|---|---|---|---|---|---|---|
| 32 | 4405.54 | 4431.04 | 4187.96 | 4705.50 | 0.04 | 0.46 | 0.81 |
| 33 | 4405.19 | 4430.75 | 4187.73 | 4704.73 | 0.05 | 0.48 | 0.82 |
| 34 | 4404.67 | 4430.52 | 4187.58 | 4703.93 | 0.05 | 0.50 | 0.83 |
| 35 | 4404.60 | 4430.37 | 4187.67 | 4703.89 | 0.06 | 0.50 | 0.83 |
| 36 | 4403.80 | 4430.24 | 4187.90 | 4704.45 | 0.07 | 0.50 | 0.83 |
| 37 | 4403.64 | 4430.19 | 4187.92 | 4704.48 | 0.07 | 0.51 | 0.82 |
| 38 | 4403.22 | 4430.24 | 4187.60 | 4703.71 | 0.06 | 0.50 | 0.82 |
| 39 | 4403.39 | 4430.37 | 4187.69 | 4703.35 | 0.05 | 0.50 | 0.82 |
| 40 | 4403.86 | 4430.60 | 4187.75 | 4703.69 | 0.05 | 0.49 | 0.81 |
| 41 | 4404.21 | 4430.89 | 4188.25 | 4703.08 | 0.05 | 0.48 | 0.80 |
| 42 | 4404.99 | 4431.24 | 4188.30 | 4704.61 | 0.05 | 0.46 | 0.79 |
| 43 | 4404.77 | 4431.59 | 4188.74 | 4704.65 | 0.04 | 0.44 | 0.77 |

### suzuka (lap 17/53, MEDIUM age 17 -> HARD)

- Best median pit lap: **27** — recommended window (medians within 0.5s): **[24, 25, 26, 27, 28, 29]**.
- Outcome spread at the best lap (p10-p90): 419.6s — this is the honest uncertainty of any single-race outcome.
- vs car_ahead: P(ahead) = 0.33 at lap 27; maximised at lap 30 (0.34).
- vs car_behind: P(ahead) = 0.70 at lap 27; maximised at lap 22 (0.72).

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_car_ahead | p_ahead_car_behind |
|---|---|---|---|---|---|---|---|
| 21 | 3594.15 | 3628.32 | 3442.77 | 3862.24 | 0.04 | 0.30 | 0.69 |
| 22 | 3593.83 | 3628.07 | 3442.58 | 3863.00 | 0.04 | 0.31 | 0.72 |
| 23 | 3593.52 | 3627.88 | 3442.23 | 3863.40 | 0.04 | 0.31 | 0.71 |
| 24 | 3593.47 | 3627.70 | 3441.92 | 3863.40 | 0.04 | 0.31 | 0.71 |
| 25 | 3593.47 | 3627.58 | 3441.78 | 3862.07 | 0.04 | 0.30 | 0.70 |
| 26 | 3593.27 | 3627.43 | 3441.75 | 3862.57 | 0.05 | 0.32 | 0.70 |
| 27 | 3593.01 | 3627.37 | 3441.62 | 3861.24 | 0.04 | 0.33 | 0.70 |
| 28 | 3593.13 | 3627.41 | 3441.67 | 3862.26 | 0.04 | 0.33 | 0.70 |
| 29 | 3593.39 | 3627.46 | 3441.85 | 3862.45 | 0.04 | 0.34 | 0.69 |
| 30 | 3593.55 | 3627.53 | 3442.02 | 3863.07 | 0.04 | 0.34 | 0.68 |
| 31 | 3593.68 | 3627.69 | 3442.18 | 3863.23 | 0.04 | 0.34 | 0.67 |
| 32 | 3593.95 | 3627.89 | 3442.33 | 3863.34 | 0.04 | 0.33 | 0.66 |

## Model scope (assumptions restated)

- Field bunching behind the SC (gap resets) is NOT modelled; the
  simulator captures the discounted-stop effect only. Recommendations
  in SC-heavy scenarios are conservative about SC upside.
- Red flags, traffic loss on rejoin, and tyre warm-up laps are out
  of scope (each documented in earlier phases or here).
- Rivals follow fixed announced plans; no strategic reaction.
- One remaining stop; compound-usage rules are the user's job.
