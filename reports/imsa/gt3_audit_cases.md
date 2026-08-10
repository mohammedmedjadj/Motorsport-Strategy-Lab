# IMSA GT3 per-decision audit — GTD and GTD PRO, where an extra stop can pay

Real stop decisions replayed through the single-next-stop simulator (5000 draws, seed 20260712). Race states (tyre age, laps since last refuel, the real stop lap) are reconstructed from the committed derived laps, not quoted from memory. See ``src/audit/endurance_cases.py`` for the case-selection rationale — there is no public strategy narrative to draw on for these races the way F1's audit has, so cases are chosen by a measurable, uniformly-applied criterion instead (an opportunistic neutralisation-onset stop, or a routine green-flag one) rather than by fame.

Reading guide: the model optimises **expected race time** to the next stop only, under its stated scope (no rivals, no track position, a single net degradation slope, FCY/SC hazards drawn from the series-wide posterior). Where a real decision disagrees, the disagreement is read against those stated limits, not as a verdict on the crew that made the call.

## Case G-A: VIR 2025 — the GTD winner stopped past the fuel minimum, but not to the optimum

**State (measured from data):** end of lap 27/81, car 021 on tyre age 18, 19 laps since last refuel (fuel range 32 laps; net slope +0.0606 s/lap).

**Real decision:** Car 021 (class winner) took three green-flag stops over 81 laps — laps 8, 28 and 53 — where the fuel minimum is two. The exact dynamic program, on this race's 4.9 s pit loss and its +0.060 s/lap slope (the steepest GTD reads anywhere), puts the optimum at five.

**Question:** The team moved in the model's direction and stopped short of it: three stops against a fuel minimum of two and an optimum of five. Does the single-stop engine show that same pressure at the lap-28 decision, and is the residual gap a real opportunity or the time-only objective ignoring what two more stops cost in track position on a short circuit?

**Model output** (pit_lap 0 = run to the flag without stopping, where feasible):

- Best median pit lap: **40** — recommended window (medians within 0.5s): **[39, 40]**.
- Outcome spread at the best lap (p10-p90): 774.8s — the honest uncertainty of any single-race outcome.
- **Verdict:** Real choice (lap 28): median cost +14.33s vs the model optimum (lap 40); OUTSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best |
|---|---|---|---|---|---|
| 28 <- real | 6202.604 | 6271.175 | 5946.086 | 6719.579 | 0.002 |
| 39 | 6188.726 | 6257.392 | 5931.062 | 6705.731 | 0.043 |
| 40 | 6188.271 | 6256.813 | 5930.410 | 6705.207 | 0.882 |

## Case G-B: Laguna Seca 2026 — the GTD PRO winner's first stop (lap 45)

**State (measured from data):** end of lap 44/111, car 3 on tyre age 42, 43 laps since last refuel (fuel range 48 laps; net slope +0.0331 s/lap).

**Real decision:** Car 3 (class winner) stopped laps 45, 55 and 106 over 111 laps; the second of those fell under a full-course yellow. Laguna Seca is tyre-limited for GTD PRO on a 7.7 s pit loss.

**Question:** Same GT3 car and same Balance of Performance as GTD, with an all-professional crew. Does the recommended window differ between the two classes at all, or are their fitted slopes too close to move a decision?

**Model output** (pit_lap 0 = run to the flag without stopping, where feasible):

- Best median pit lap: **49** — recommended window (medians within 0.5s): **[48, 49]**.
- Outcome spread at the best lap (p10-p90): 473.8s — the honest uncertainty of any single-race outcome.
- **Verdict:** Real choice (lap 45): median cost +2.57s vs the model optimum (lap 49); OUTSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best |
|---|---|---|---|---|---|
| 45 <- real | 5913.096 | 5947.267 | 5733.822 | 6207.444 | 0.016 |
| 48 | 5910.970 | 5945.529 | 5731.915 | 6206.633 | 0.027 |
| 49 | 5910.529 | 5945.058 | 5731.400 | 6205.229 | 0.925 |

## What these two cases show

Both circuits are tyre-limited: the exact dynamic program wants more stops than the fuel minimum, which no prototype race in scope ever reaches. The single-stop engine cannot express "stop more often", so read its window as where the *next* stop belongs given that pressure, not as agreement or disagreement with the full plan.

The two layers of the model disagree with each other at VIR, and saying so is more useful than picking one. The full-race dynamic program wants five stops where the winner took three and the fuel minimum is two — stop *more often*. The single-stop engine, asked about the lap-28 decision in isolation, wants that particular stop **later** (lap 40, +14.24 s). Both are consistent: more stops overall and each one later is only contradictory if you assume the extra visits come at the front of the race, and nothing in the DP says they do.

What neither layer has is a term for track position. A time-only optimum cannot price what two extra stops cost on a short circuit where passing is hard, which is the same limitation the F1 audit documents at Monaco. A gap this size is a question about the model as much as about the strategy.
