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
- Outcome spread at the best lap (p10-p90): 250.9s — this is the honest uncertainty of any single-race outcome.
- vs car_ahead: P(ahead) = 0.38 at lap 35; maximised at lap 44 (0.42).
- vs car_behind: P(ahead) = 0.73 at lap 35; maximised at lap 32 (0.74).

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_car_ahead | p_ahead_car_behind |
|---|---|---|---|---|---|---|---|
| 29 | 3529.72 | 3598.50 | 3516.71 | 3769.02 | 0.02 | 0.31 | 0.74 |
| 30 | 3529.40 | 3598.32 | 3516.68 | 3768.81 | 0.02 | 0.32 | 0.74 |
| 31 | 3529.20 | 3598.17 | 3516.72 | 3768.81 | 0.02 | 0.33 | 0.74 |
| 32 | 3528.95 | 3598.04 | 3516.70 | 3768.59 | 0.02 | 0.34 | 0.74 |
| 33 | 3528.84 | 3597.87 | 3516.52 | 3768.06 | 0.03 | 0.36 | 0.74 |
| 34 | 3528.84 | 3597.76 | 3516.36 | 3767.80 | 0.02 | 0.37 | 0.74 |
| 35 | 3528.78 | 3597.67 | 3516.16 | 3767.07 | 0.02 | 0.38 | 0.73 |
| 36 | 3528.88 | 3597.62 | 3515.89 | 3767.14 | 0.02 | 0.39 | 0.73 |
| 37 | 3529.03 | 3597.57 | 3515.67 | 3766.08 | 0.02 | 0.39 | 0.73 |
| 38 | 3529.22 | 3597.54 | 3515.36 | 3765.60 | 0.02 | 0.40 | 0.72 |
| 39 | 3529.53 | 3597.58 | 3515.00 | 3765.38 | 0.02 | 0.41 | 0.71 |
| 40 | 3529.81 | 3597.62 | 3514.78 | 3765.43 | 0.02 | 0.41 | 0.70 |

### monaco (lap 26/78, MEDIUM age 26 -> HARD)

- Best median pit lap: **27** — recommended window (medians within 0.5s): **[27, 28, 29, 30, 31, 32, 33]**.
- Outcome spread at the best lap (p10-p90): 170.4s — this is the honest uncertainty of any single-race outcome.
- vs car_ahead: P(ahead) = 0.44 at lap 27; maximised at lap 27 (0.44).
- vs car_behind: P(ahead) = 0.60 at lap 27; maximised at lap 27 (0.60).

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_car_ahead | p_ahead_car_behind |
|---|---|---|---|---|---|---|---|
| 27 | 4023.32 | 4055.02 | 3988.23 | 4158.65 | 0.40 | 0.44 | 0.60 |
| 28 | 4023.37 | 4055.08 | 3988.41 | 4158.42 | 0.01 | 0.44 | 0.60 |
| 29 | 4023.71 | 4055.18 | 3988.68 | 4158.29 | 0.01 | 0.43 | 0.60 |
| 30 | 4023.67 | 4055.27 | 3988.84 | 4158.62 | 0.02 | 0.43 | 0.60 |
| 31 | 4023.62 | 4055.38 | 3989.04 | 4159.19 | 0.02 | 0.43 | 0.59 |
| 32 | 4023.72 | 4055.53 | 3989.30 | 4158.84 | 0.02 | 0.42 | 0.58 |
| 33 | 4023.76 | 4055.68 | 3989.50 | 4159.01 | 0.02 | 0.42 | 0.58 |
| 34 | 4024.03 | 4055.84 | 3989.69 | 4159.32 | 0.01 | 0.41 | 0.57 |
| 35 | 4024.34 | 4056.01 | 3989.98 | 4159.58 | 0.01 | 0.41 | 0.57 |
| 36 | 4024.46 | 4056.17 | 3990.15 | 4159.94 | 0.01 | 0.40 | 0.56 |
| 37 | 4024.80 | 4056.39 | 3990.33 | 4159.98 | 0.01 | 0.39 | 0.56 |
| 38 | 4025.11 | 4056.55 | 3990.57 | 4160.01 | 0.01 | 0.39 | 0.55 |

### singapore (lap 20/62, MEDIUM age 20 -> HARD)

- Best median pit lap: **38** — recommended window (medians within 0.5s): **[37, 38, 39, 40]**.
- Outcome spread at the best lap (p10-p90): 344.7s — this is the honest uncertainty of any single-race outcome.
- vs car_ahead: P(ahead) = 0.54 at lap 38; maximised at lap 37 (0.54).
- vs car_behind: P(ahead) = 0.86 at lap 38; maximised at lap 37 (0.86).

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_car_ahead | p_ahead_car_behind |
|---|---|---|---|---|---|---|---|
| 32 | 4248.63 | 4264.05 | 4120.91 | 4464.89 | 0.03 | 0.49 | 0.84 |
| 33 | 4248.30 | 4263.69 | 4120.53 | 4465.11 | 0.04 | 0.51 | 0.85 |
| 34 | 4248.22 | 4263.42 | 4120.25 | 4464.84 | 0.06 | 0.52 | 0.86 |
| 35 | 4247.84 | 4263.23 | 4120.08 | 4464.51 | 0.10 | 0.53 | 0.86 |
| 36 | 4247.70 | 4263.16 | 4119.99 | 4464.47 | 0.14 | 0.54 | 0.86 |
| 37 | 4247.05 | 4263.14 | 4119.94 | 4464.37 | 0.13 | 0.54 | 0.86 |
| 38 | 4246.82 | 4263.18 | 4120.00 | 4464.70 | 0.08 | 0.54 | 0.86 |
| 39 | 4247.09 | 4263.33 | 4120.22 | 4464.56 | 0.04 | 0.53 | 0.85 |
| 40 | 4247.27 | 4263.55 | 4120.49 | 4464.47 | 0.02 | 0.52 | 0.84 |
| 41 | 4247.73 | 4263.85 | 4120.89 | 4465.09 | 0.03 | 0.50 | 0.83 |
| 42 | 4248.39 | 4264.28 | 4121.30 | 4465.25 | 0.03 | 0.48 | 0.82 |
| 43 | 4248.88 | 4264.82 | 4121.81 | 4466.18 | 0.02 | 0.46 | 0.80 |

### suzuka (lap 17/53, MEDIUM age 17 -> HARD)

- Best median pit lap: **27** — recommended window (medians within 0.5s): **[24, 25, 26, 27, 28, 29, 30]**.
- Outcome spread at the best lap (p10-p90): 167.6s — this is the honest uncertainty of any single-race outcome.
- vs car_ahead: P(ahead) = 0.32 at lap 27; maximised at lap 28 (0.32).
- vs car_behind: P(ahead) = 0.73 at lap 27; maximised at lap 25 (0.73).

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_car_ahead | p_ahead_car_behind |
|---|---|---|---|---|---|---|---|
| 21 | 3454.47 | 3499.19 | 3437.36 | 3604.97 | 0.04 | 0.27 | 0.69 |
| 22 | 3454.02 | 3498.91 | 3437.19 | 3604.51 | 0.04 | 0.29 | 0.71 |
| 23 | 3453.65 | 3498.68 | 3437.20 | 3604.47 | 0.04 | 0.30 | 0.72 |
| 24 | 3453.29 | 3498.48 | 3437.10 | 3604.51 | 0.04 | 0.30 | 0.73 |
| 25 | 3453.06 | 3498.32 | 3437.05 | 3604.01 | 0.05 | 0.31 | 0.73 |
| 26 | 3452.88 | 3498.20 | 3436.93 | 3604.06 | 0.05 | 0.32 | 0.73 |
| 27 | 3452.80 | 3498.17 | 3436.82 | 3604.43 | 0.04 | 0.32 | 0.73 |
| 28 | 3452.93 | 3498.17 | 3436.73 | 3604.13 | 0.05 | 0.32 | 0.72 |
| 29 | 3453.01 | 3498.24 | 3436.64 | 3604.71 | 0.04 | 0.32 | 0.71 |
| 30 | 3453.14 | 3498.34 | 3436.66 | 3604.51 | 0.04 | 0.32 | 0.71 |
| 31 | 3453.62 | 3498.47 | 3436.73 | 3604.93 | 0.04 | 0.32 | 0.70 |
| 32 | 3453.97 | 3498.68 | 3436.72 | 3605.50 | 0.04 | 0.32 | 0.68 |

## Implementation notes

### Vectorised Monte Carlo

The engine is fully vectorised over draws: fuel/degradation coefficients
and per-lap noise are batch-sampled once, and each candidate pit lap and
rival is evaluated with a single broadcast pass across all draws rather
than a Python loop of per-draw calls. The batched path is bit-identical
to the earlier per-draw scalar path (max abs diff 0.0); common random
numbers and seed reproducibility are unchanged. Effect: a 5000-draw,
32-candidate, 2-rival scenario runs in ~1.8s instead of ~22s (~12x).

### Optional quasi-Monte Carlo sampling (`sampler="qmc"`)

The smooth, globally-shared input subspace — fuel slope, degradation
coefficients, and every per-lap noise vector — can be drawn from a
scrambled Sobol' sequence (inverse-CDF mapped to the same Normal
marginals) instead of i.i.d. Gaussians. Scrambling keeps it an unbiased,
seed-reproducible estimator (randomised QMC).

Measured effect on the RMSE of the estimated per-candidate mean lap time
(vs a 10^5-draw reference), synthetic circuit:

| Regime | n=256 | n=1024 | n=4096 |
|---|---|---|---|
| SC/VSC hazards ~0 (smooth integrand) | **15.4x** | 5.4x | 3.2x |
| Realistic SC/VSC hazards | ~1.0x | ~1.0x | ~1.0x |

The honest finding: QMC delivers a large variance reduction **only when
the integrand is smooth**. Under realistic hazards the estimator variance
is dominated by the *discrete* SC/VSC jump process — which stays on plain
Monte Carlo, because a variable-length run-length walk does not admit a
clean fixed-dimension QMC embedding — so the smooth-subspace gain is
masked. QMC is therefore worthwhile for low-neutralisation circuits and
for any downstream quantity that is smooth in the coefficients (expected
degradation, fuel-corrected pace deltas), and a no-op elsewhere. Default
stays `"mc"`; nothing about the reported results above changes.

## Model scope (assumptions restated)

- Field bunching behind the SC (gap resets) is NOT modelled; the
  simulator captures the discounted-stop effect only. Recommendations
  in SC-heavy scenarios are conservative about SC upside.
- Red flags, traffic loss on rejoin, and tyre warm-up laps are out
  of scope (each documented in earlier phases or here).
- Rivals follow fixed announced plans; no strategic reaction.
- One remaining stop; compound-usage rules are the user's job.
