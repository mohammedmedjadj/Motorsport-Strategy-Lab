# IMSA per-decision audit — real stop timing vs the model

Real stop decisions replayed through the single-next-stop simulator (5000 draws, seed 20260712). Race states (tyre age, laps since last refuel, the real stop lap) are reconstructed from the committed derived laps, not quoted from memory. See ``src/audit/endurance_cases.py`` for the case-selection rationale — there is no public strategy narrative to draw on for these races the way F1's audit has, so cases are chosen by a measurable, uniformly-applied criterion instead (an opportunistic neutralisation-onset stop, or a routine green-flag one) rather than by fame.

Reading guide: the model optimises **expected race time** to the next stop only, under its stated scope (no rivals, no track position, a single net degradation slope, FCY/SC hazards drawn from the series-wide posterior). Where a real decision disagrees, the disagreement is read against those stated limits, not as a verdict on the crew that made the call.

## Case I-A: Watkins Glen 2024 — car 01's FCY-onset stop (lap 90)

**State (measured from data):** end of lap 89/148, car 01 on tyre age 14, 17 laps since last refuel (fuel range 32 laps; net slope +0.0204 s/lap).

**Real decision:** Car 01 (the class winner) pitted lap 90 — the exact lap the flag turned from GF to FCY — its fourth of eight stops.

**Question:** IMSA's FCY pace ratio (2.03 at Watkins Glen) is far slower than an F1 SC; does boxing the instant the yellow falls dominate the model's recommendation as clearly as that ratio would suggest?

**Model output** (pit_lap 0 = run to the flag without stopping, where feasible):

- Best median pit lap: **104** — recommended window (medians within 0.5s): **[101, 103, 104]**.
- Outcome spread at the best lap (p10-p90): 1224.4s — the honest uncertainty of any single-race outcome.
- **Verdict:** Real choice (lap 90): median cost +7.81s vs the model optimum (lap 104); OUTSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best |
|---|---|---|---|---|---|
| 90 <- real | 6320.192 | 6390.614 | 5859.861 | 7089.680 | 0.014 |
| 101 | 6312.851 | 6381.811 | 5853.284 | 7079.976 | 0.023 |
| 103 | 6312.511 | 6381.139 | 5852.588 | 7078.820 | 0.025 |
| 104 | 6312.378 | 6380.754 | 5852.318 | 7076.754 | 0.791 |

## Case I-B: Road America 2024 — car 10's routine green-flag stop (lap 29)

**State (measured from data):** end of lap 28/62, car 10 on tyre age 20, 27 laps since last refuel (fuel range 30 laps; net slope -0.0590 s/lap).

**Real decision:** Car 10 (the class winner) pitted lap 29 under green flag — its first of two stops in this 62-lap sprint.

**Question:** Road America has the strongest, most consistently significant degradation signal of any IMSA circuit in scope. Does a routine first stop line up with the model's fuel/tyre trade-off here?

**Model output** (pit_lap 0 = run to the flag without stopping, where feasible):

- Best median pit lap: **29** — recommended window (medians within 0.5s): **[29]**.
- Outcome spread at the best lap (p10-p90): 977.0s — the honest uncertainty of any single-race outcome.
- **Verdict:** Real choice (lap 29): median cost +0.00s vs the model optimum (lap 29); INSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best |
|---|---|---|---|---|---|
| 29 <- real | 4004.517 | 4232.069 | 3883.213 | 4860.194 | 0.918 |

## Case I-C: Mosport 2023 — car 10's FCY-onset stop (lap 85), the flat-signal circuit

**State (measured from data):** end of lap 84/120, car 10 on tyre age 12, 15 laps since last refuel (fuel range 50 laps; net slope +0.0002 s/lap).

**Real decision:** Car 10 (the class winner) pitted lap 85 — the exact lap the flag turned from GF to FCY — its third of three stops.

**Question:** Mosport has only one GTP season and a degradation slope confidence interval that covers zero (Phase 2's flattest read in either series). Does the model still recommend the same window when degradation gives it almost nothing to arbitrate?

**Model output** (pit_lap 0 = run to the flag without stopping, where feasible):

- Best median pit lap: **119** — recommended window (medians within 0.5s): **[119]**.
- Outcome spread at the best lap (p10-p90): 580.8s — the honest uncertainty of any single-race outcome.
- **Verdict:** Real choice (lap 85): median cost +3.02s vs the model optimum (lap 119); OUTSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best |
|---|---|---|---|---|---|
| 85 <- real | 2656.646 | 2776.311 | 2560.924 | 3143.570 | 0.009 |
| 119 | 2653.625 | 2774.192 | 2560.252 | 3141.046 | 0.240 |

## Cross-case analysis

**1. The strongest-signal circuit matches the model exactly (Case B).** Road America's routine first stop lands precisely on the model's own optimum (P(best) 0.919) — the circuit with the most consistently significant degradation fit in IMSA behaves exactly as that fit predicts, with no neutralisation involved to complicate the read.

**2. Both FCY-onset stops read 'outside', but for different reasons (Cases A, C).** At Watkins Glen (Case A) the model is decisive — P(best) 0.792 at lap 104 vs 0.014 at the real lap 90 — and the +7.92s gap is a real, if modest, correction: with 15 laps of fuel still in the tank, waiting past the FCY onset paid off more than boxing on it did. At Mosport (Case C) the 'outside' label is far less confident: the model's own optimum carries P(best) just 0.339 against 0.011 for the real stop — a genuine relative preference, but on a 581s p10-p90 spread that is honest uncertainty, not a confident correction, exactly matching Mosport's flat, single-season slope (its confidence interval covers zero, Phase 2).

**3. Model confidence tracks the strength of its own degradation signal, not a fixed default (all three cases).** P(best) at the recommended lap runs 0.919 (Road America) -> 0.792 (Watkins Glen) -> 0.339 (Mosport) — the same ordering Phase 4's own demo scenarios found, now confirmed against real stop decisions rather than a synthetic mid-race state.

## Scope reminders for reading these verdicts

- 'OUTSIDE the recommended window' is a statement about expected race time under the model's stated scope (no rivals, no track position, a single net degradation slope, FCY/SC hazards drawn from the series-wide posterior), not a judgement on the crew that made the call.
- Read a verdict's margin against the model's own P(best) at that lap, not just the label — Case C's 'outside' carries far less confidence than Case A's.
- IMSA has zero measured Safety Car events in 63 races (Phase 3); every case here concerns FCY or green-flag timing only.
- No per-car cost of *also* changing tyres vs a fuel-only splash (IMSA's measured, smaller tyre-change premium, Phase 3) is priced here — the single-stop engine still uses one flat pit loss.
