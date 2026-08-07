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

- Best median pit lap: **35** — recommended window (medians within 0.5s): **[32, 33, 34, 35, 36, 37]**.
- Outcome spread at the best lap (p10-p90): 252.7s — this is the honest uncertainty of any single-race outcome.
- vs car_ahead: P(ahead) = 0.38 at lap 35; maximised at lap 45 (0.44).
- vs car_behind: P(ahead) = 0.69 at lap 35; maximised at lap 29 (0.74).

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_car_ahead | p_ahead_car_behind |
|---|---|---|---|---|---|---|---|
| 29 | 3533.18 | 3594.93 | 3512.66 | 3766.81 | 0.02 | 0.31 | 0.74 |
| 30 | 3532.72 | 3594.75 | 3512.84 | 3766.79 | 0.02 | 0.31 | 0.73 |
| 31 | 3532.23 | 3594.60 | 3512.93 | 3766.47 | 0.02 | 0.33 | 0.73 |
| 32 | 3531.96 | 3594.48 | 3513.15 | 3766.35 | 0.01 | 0.34 | 0.72 |
| 33 | 3531.72 | 3594.40 | 3513.18 | 3766.03 | 0.01 | 0.36 | 0.71 |
| 34 | 3531.61 | 3594.33 | 3513.21 | 3765.66 | 0.02 | 0.37 | 0.70 |
| 35 | 3531.55 | 3594.24 | 3512.98 | 3765.67 | 0.02 | 0.38 | 0.69 |
| 36 | 3531.71 | 3594.19 | 3512.72 | 3765.51 | 0.01 | 0.39 | 0.69 |
| 37 | 3531.97 | 3594.15 | 3512.43 | 3764.99 | 0.02 | 0.41 | 0.67 |
| 38 | 3532.15 | 3594.15 | 3512.11 | 3764.44 | 0.01 | 0.41 | 0.66 |
| 39 | 3532.50 | 3594.16 | 3511.62 | 3763.90 | 0.02 | 0.42 | 0.66 |
| 40 | 3532.94 | 3594.20 | 3511.13 | 3763.82 | 0.01 | 0.42 | 0.65 |

### monaco (lap 26/78, MEDIUM age 26 -> HARD)

- Best median pit lap: **36** — recommended window (medians within 0.5s): **[27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39]**.
- Outcome spread at the best lap (p10-p90): 190.1s — this is the honest uncertainty of any single-race outcome.
- vs car_ahead: P(ahead) = 0.42 at lap 36; maximised at lap 27 (0.45).
- vs car_behind: P(ahead) = 0.57 at lap 36; maximised at lap 29 (0.61).

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_car_ahead | p_ahead_car_behind |
|---|---|---|---|---|---|---|---|
| 30 | 4033.64 | 4056.93 | 3977.38 | 4169.58 | 0.01 | 0.44 | 0.60 |
| 31 | 4033.59 | 4057.05 | 3977.88 | 4169.69 | 0.01 | 0.44 | 0.60 |
| 32 | 4033.43 | 4057.19 | 3978.37 | 4169.48 | 0.01 | 0.44 | 0.59 |
| 33 | 4033.53 | 4057.32 | 3978.61 | 4169.23 | 0.01 | 0.43 | 0.59 |
| 34 | 4033.49 | 4057.49 | 3978.91 | 4169.15 | 0.01 | 0.43 | 0.58 |
| 35 | 4033.30 | 4057.66 | 3979.27 | 4169.83 | 0.01 | 0.42 | 0.58 |
| 36 | 4033.25 | 4057.83 | 3979.23 | 4169.32 | 0.01 | 0.42 | 0.57 |
| 37 | 4033.34 | 4057.99 | 3979.42 | 4169.04 | 0.01 | 0.42 | 0.57 |
| 38 | 4033.38 | 4058.18 | 3979.69 | 4169.06 | 0.01 | 0.41 | 0.56 |
| 39 | 4033.66 | 4058.37 | 3980.00 | 4169.01 | 0.01 | 0.40 | 0.55 |
| 40 | 4033.92 | 4058.56 | 3980.31 | 4169.55 | 0.01 | 0.40 | 0.55 |
| 41 | 4034.35 | 4058.78 | 3980.32 | 4169.49 | 0.01 | 0.40 | 0.54 |

### singapore (lap 20/62, MEDIUM age 20 -> HARD)

- Best median pit lap: **39** — recommended window (medians within 0.5s): **[35, 36, 37, 38, 39, 40]**.
- Outcome spread at the best lap (p10-p90): 341.6s — this is the honest uncertainty of any single-race outcome.
- vs car_ahead: P(ahead) = 0.53 at lap 39; maximised at lap 36 (0.54).
- vs car_behind: P(ahead) = 0.84 at lap 39; maximised at lap 35 (0.86).

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_car_ahead | p_ahead_car_behind |
|---|---|---|---|---|---|---|---|
| 33 | 4245.89 | 4261.54 | 4119.91 | 4462.83 | 0.06 | 0.51 | 0.85 |
| 34 | 4245.74 | 4261.27 | 4119.59 | 4461.91 | 0.06 | 0.52 | 0.85 |
| 35 | 4245.34 | 4261.07 | 4119.41 | 4461.31 | 0.08 | 0.53 | 0.86 |
| 36 | 4245.15 | 4260.95 | 4119.35 | 4461.00 | 0.09 | 0.54 | 0.85 |
| 37 | 4245.44 | 4260.94 | 4119.26 | 4461.01 | 0.08 | 0.54 | 0.85 |
| 38 | 4245.14 | 4261.01 | 4119.27 | 4460.62 | 0.08 | 0.54 | 0.85 |
| 39 | 4244.99 | 4261.18 | 4119.44 | 4461.00 | 0.06 | 0.53 | 0.84 |
| 40 | 4245.45 | 4261.41 | 4119.71 | 4461.54 | 0.04 | 0.52 | 0.83 |
| 41 | 4245.52 | 4261.73 | 4120.05 | 4462.19 | 0.04 | 0.50 | 0.82 |
| 42 | 4245.94 | 4262.18 | 4120.43 | 4462.26 | 0.03 | 0.48 | 0.81 |
| 43 | 4246.29 | 4262.63 | 4121.06 | 4462.38 | 0.03 | 0.46 | 0.79 |
| 44 | 4246.94 | 4263.21 | 4121.63 | 4462.73 | 0.03 | 0.44 | 0.77 |

### suzuka (lap 17/53, MEDIUM age 17 -> HARD)

- Best median pit lap: **27** — recommended window (medians within 0.5s): **[25, 26, 27, 28, 29, 30]**.
- Outcome spread at the best lap (p10-p90): 172.6s — this is the honest uncertainty of any single-race outcome.
- vs car_ahead: P(ahead) = 0.34 at lap 27; maximised at lap 31 (0.37).
- vs car_behind: P(ahead) = 0.70 at lap 27; maximised at lap 24 (0.73).

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_car_ahead | p_ahead_car_behind |
|---|---|---|---|---|---|---|---|
| 21 | 3459.92 | 3499.70 | 3432.04 | 3607.24 | 0.03 | 0.31 | 0.70 |
| 22 | 3459.19 | 3499.45 | 3432.28 | 3606.93 | 0.03 | 0.31 | 0.72 |
| 23 | 3458.39 | 3499.23 | 3432.56 | 3607.03 | 0.03 | 0.31 | 0.73 |
| 24 | 3457.82 | 3499.03 | 3432.76 | 3606.34 | 0.02 | 0.31 | 0.73 |
| 25 | 3457.57 | 3498.88 | 3432.98 | 3606.00 | 0.03 | 0.32 | 0.72 |
| 26 | 3457.46 | 3498.79 | 3433.10 | 3605.53 | 0.02 | 0.33 | 0.71 |
| 27 | 3457.16 | 3498.75 | 3433.18 | 3605.76 | 0.03 | 0.34 | 0.70 |
| 28 | 3457.34 | 3498.76 | 3433.16 | 3605.76 | 0.03 | 0.35 | 0.68 |
| 29 | 3457.38 | 3498.80 | 3433.05 | 3605.81 | 0.03 | 0.36 | 0.67 |
| 30 | 3457.64 | 3498.91 | 3433.05 | 3606.44 | 0.02 | 0.36 | 0.66 |
| 31 | 3458.15 | 3499.09 | 3433.03 | 3606.87 | 0.02 | 0.37 | 0.64 |
| 32 | 3458.73 | 3499.32 | 3432.98 | 3607.86 | 0.03 | 0.36 | 0.62 |

## Model scope (assumptions restated)

- Field bunching behind the SC (gap resets) is NOT modelled; the
  simulator captures the discounted-stop effect only. Recommendations
  in SC-heavy scenarios are conservative about SC upside.
- Red flags, traffic loss on rejoin, and tyre warm-up laps are out
  of scope (each documented in earlier phases or here).
- Rivals follow fixed announced plans; no strategic reaction.
- One remaining stop; compound-usage rules are the user's job.
