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

- Best median pit lap: **33** — recommended window (medians within 0.5s): **[31, 32, 33, 34, 35, 36, 37, 38]**.
- Outcome spread at the best lap (p10-p90): 252.2s — this is the honest uncertainty of any single-race outcome.
- vs car_ahead: P(ahead) = 0.35 at lap 33; maximised at lap 42 (0.40).
- vs car_behind: P(ahead) = 0.73 at lap 33; maximised at lap 30 (0.74).

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_car_ahead | p_ahead_car_behind |
|---|---|---|---|---|---|---|---|
| 27 | 3530.05 | 3595.26 | 3516.94 | 3770.14 | 0.02 | 0.29 | 0.72 |
| 28 | 3529.56 | 3595.00 | 3516.91 | 3770.04 | 0.02 | 0.30 | 0.73 |
| 29 | 3529.23 | 3594.79 | 3516.92 | 3769.93 | 0.02 | 0.31 | 0.73 |
| 30 | 3528.92 | 3594.61 | 3516.92 | 3769.82 | 0.02 | 0.32 | 0.74 |
| 31 | 3528.65 | 3594.46 | 3516.86 | 3769.37 | 0.02 | 0.33 | 0.74 |
| 32 | 3528.41 | 3594.33 | 3516.75 | 3769.44 | 0.02 | 0.35 | 0.73 |
| 33 | 3528.28 | 3594.25 | 3516.60 | 3768.81 | 0.02 | 0.35 | 0.73 |
| 34 | 3528.32 | 3594.17 | 3516.47 | 3767.92 | 0.02 | 0.36 | 0.73 |
| 35 | 3528.31 | 3594.07 | 3516.28 | 3767.22 | 0.02 | 0.37 | 0.73 |
| 36 | 3528.32 | 3594.01 | 3516.02 | 3766.91 | 0.02 | 0.38 | 0.72 |
| 37 | 3528.44 | 3593.96 | 3515.69 | 3766.16 | 0.02 | 0.39 | 0.71 |
| 38 | 3528.59 | 3593.95 | 3515.41 | 3765.29 | 0.01 | 0.39 | 0.70 |

### monaco (lap 26/78, MEDIUM age 26 -> HARD)

- Best median pit lap: **27** — recommended window (medians within 0.5s): **[27, 28, 29, 30, 31]**.
- Outcome spread at the best lap (p10-p90): 175.7s — this is the honest uncertainty of any single-race outcome.
- vs car_ahead: P(ahead) = 0.45 at lap 27; maximised at lap 27 (0.45).
- vs car_behind: P(ahead) = 0.61 at lap 27; maximised at lap 27 (0.61).

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_car_ahead | p_ahead_car_behind |
|---|---|---|---|---|---|---|---|
| 27 | 4024.20 | 4056.20 | 3987.92 | 4163.61 | 0.41 | 0.45 | 0.61 |
| 28 | 4024.40 | 4056.24 | 3988.07 | 4163.72 | 0.02 | 0.45 | 0.60 |
| 29 | 4024.49 | 4056.34 | 3988.24 | 4163.50 | 0.02 | 0.45 | 0.60 |
| 30 | 4024.32 | 4056.42 | 3988.43 | 4163.38 | 0.02 | 0.45 | 0.60 |
| 31 | 4024.59 | 4056.55 | 3988.75 | 4163.32 | 0.02 | 0.44 | 0.60 |
| 32 | 4024.84 | 4056.70 | 3989.04 | 4163.50 | 0.02 | 0.44 | 0.60 |
| 33 | 4024.89 | 4056.84 | 3989.24 | 4163.03 | 0.02 | 0.43 | 0.59 |
| 34 | 4025.23 | 4057.02 | 3989.58 | 4162.89 | 0.01 | 0.43 | 0.58 |
| 35 | 4025.56 | 4057.20 | 3989.87 | 4163.08 | 0.01 | 0.42 | 0.57 |
| 36 | 4025.69 | 4057.38 | 3990.02 | 4163.33 | 0.01 | 0.42 | 0.57 |
| 37 | 4025.85 | 4057.56 | 3990.22 | 4164.23 | 0.01 | 0.41 | 0.56 |
| 38 | 4025.97 | 4057.77 | 3990.49 | 4164.66 | 0.01 | 0.40 | 0.56 |

### singapore (lap 20/62, MEDIUM age 20 -> HARD)

- Best median pit lap: **36** — recommended window (medians within 0.5s): **[35, 36, 37, 38, 39]**.
- Outcome spread at the best lap (p10-p90): 342.2s — this is the honest uncertainty of any single-race outcome.
- vs car_ahead: P(ahead) = 0.54 at lap 36; maximised at lap 37 (0.54).
- vs car_behind: P(ahead) = 0.86 at lap 36; maximised at lap 35 (0.86).

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_car_ahead | p_ahead_car_behind |
|---|---|---|---|---|---|---|---|
| 30 | 4247.72 | 4263.01 | 4122.12 | 4465.49 | 0.02 | 0.44 | 0.81 |
| 31 | 4247.18 | 4262.43 | 4121.50 | 4465.01 | 0.03 | 0.47 | 0.82 |
| 32 | 4246.73 | 4261.98 | 4121.04 | 4464.57 | 0.03 | 0.49 | 0.84 |
| 33 | 4246.33 | 4261.58 | 4120.62 | 4463.70 | 0.05 | 0.51 | 0.85 |
| 34 | 4246.15 | 4261.32 | 4120.33 | 4462.49 | 0.06 | 0.52 | 0.86 |
| 35 | 4245.74 | 4261.12 | 4120.11 | 4462.06 | 0.09 | 0.53 | 0.86 |
| 36 | 4245.41 | 4261.00 | 4119.98 | 4462.15 | 0.15 | 0.54 | 0.86 |
| 37 | 4245.51 | 4260.99 | 4119.94 | 4462.89 | 0.14 | 0.54 | 0.86 |
| 38 | 4245.56 | 4261.07 | 4119.98 | 4462.28 | 0.08 | 0.54 | 0.86 |
| 39 | 4245.83 | 4261.25 | 4120.12 | 4463.00 | 0.04 | 0.53 | 0.85 |
| 40 | 4246.10 | 4261.48 | 4120.36 | 4462.77 | 0.02 | 0.52 | 0.84 |
| 41 | 4246.54 | 4261.81 | 4120.72 | 4463.42 | 0.02 | 0.50 | 0.83 |

### suzuka (lap 17/53, MEDIUM age 17 -> HARD)

- Best median pit lap: **26** — recommended window (medians within 0.5s): **[23, 24, 25, 26, 27, 28, 29]**.
- Outcome spread at the best lap (p10-p90): 166.2s — this is the honest uncertainty of any single-race outcome.
- vs car_ahead: P(ahead) = 0.33 at lap 26; maximised at lap 28 (0.33).
- vs car_behind: P(ahead) = 0.73 at lap 26; maximised at lap 24 (0.73).

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_car_ahead | p_ahead_car_behind |
|---|---|---|---|---|---|---|---|
| 20 | 3454.87 | 3500.09 | 3437.31 | 3603.41 | 0.03 | 0.27 | 0.67 |
| 21 | 3454.28 | 3499.73 | 3437.13 | 3603.17 | 0.04 | 0.29 | 0.69 |
| 22 | 3454.00 | 3499.48 | 3436.98 | 3602.96 | 0.04 | 0.30 | 0.71 |
| 23 | 3453.55 | 3499.26 | 3436.77 | 3602.92 | 0.04 | 0.30 | 0.72 |
| 24 | 3453.34 | 3499.06 | 3436.63 | 3602.88 | 0.05 | 0.31 | 0.73 |
| 25 | 3453.28 | 3498.91 | 3436.60 | 3602.69 | 0.04 | 0.31 | 0.73 |
| 26 | 3453.27 | 3498.81 | 3436.54 | 3602.74 | 0.05 | 0.33 | 0.73 |
| 27 | 3453.30 | 3498.77 | 3436.42 | 3603.21 | 0.05 | 0.33 | 0.73 |
| 28 | 3453.38 | 3498.78 | 3436.41 | 3603.22 | 0.04 | 0.33 | 0.72 |
| 29 | 3453.61 | 3498.81 | 3436.48 | 3603.34 | 0.04 | 0.33 | 0.71 |
| 30 | 3453.83 | 3498.92 | 3436.38 | 3603.49 | 0.04 | 0.33 | 0.70 |
| 31 | 3454.09 | 3499.10 | 3436.33 | 3603.69 | 0.04 | 0.33 | 0.68 |

## Model scope (assumptions restated)

- Field bunching behind the SC (gap resets) is NOT modelled; the
  simulator captures the discounted-stop effect only. Recommendations
  in SC-heavy scenarios are conservative about SC upside.
- Red flags, traffic loss on rejoin, and tyre warm-up laps are out
  of scope (each documented in earlier phases or here).
- Rivals follow fixed announced plans; no strategic reaction.
- One remaining stop; compound-usage rules are the user's job.
