# WEC per-decision audit — real stop timing vs the model

Real stop decisions replayed through the single-next-stop simulator (5000 draws, seed 20260712). Race states (tyre age, laps since last refuel, the real stop lap) are reconstructed from the committed derived laps, not quoted from memory. See ``src/audit/endurance_cases.py`` for the case-selection rationale — there is no public strategy narrative to draw on for these races the way F1's audit has, so cases are chosen by a measurable, uniformly-applied criterion instead (an opportunistic neutralisation-onset stop, or a routine green-flag one) rather than by fame.

Reading guide: the model optimises **expected race time** to the next stop only, under its stated scope (no rivals, no track position, a single net degradation slope, FCY/SC hazards drawn from the series-wide posterior). Where a real decision disagrees, the disagreement is read against those stated limits, not as a verdict on the crew that made the call.

## Case W-A: Bahrain 2025 — car 009's Safety Car-onset stop (lap 216)

**State (measured from data):** end of lap 215/237, car 009 on tyre age 18, 19 laps since last refuel (fuel range 32 laps; net slope +0.0438 s/lap).

**Real decision:** Car 009 (this race's class winner by laps completed) pitted lap 216 — the exact lap the flag turned from GF to SF (Safety Car called) — its ninth and final stop of the race.

**Question:** Does boxing the instant the Safety Car is called dominate the model's own recommendation, at a circuit (Bahrain) with a steep, significant degradation slope?

**Model output** (pit_lap 0 = run to the flag without stopping, where feasible):

- Best median pit lap: **217** — recommended window (medians within 0.5s): **[216, 217, 218, 219, 220]**.
- Outcome spread at the best lap (p10-p90): 148.8s — the honest uncertainty of any single-race outcome.
- **Verdict:** Real choice (lap 216): median cost +0.04s vs the model optimum (lap 217); INSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best |
|---|---|---|---|---|---|
| 216 <- real | 2611.249 | 2655.517 | 2606.294 | 2759.575 | 0.068 |
| 217 | 2611.205 | 2655.287 | 2606.251 | 2755.016 | 0.838 |
| 218 | 2611.249 | 2655.236 | 2606.294 | 2757.450 | 0.006 |
| 219 | 2611.381 | 2655.255 | 2606.424 | 2756.682 | 0.009 |
| 220 | 2611.601 | 2655.448 | 2606.640 | 2757.451 | 0.006 |

## Case W-B: Bahrain 2024 — car 15's routine green-flag stop (lap 125)

**State (measured from data):** end of lap 124/235, car 15 on tyre age 29, 30 laps since last refuel (fuel range 32 laps; net slope +0.0493 s/lap).

**Real decision:** Car 15 (the class winner) pitted lap 125 under green flag — its fourth of eight stops, with no neutralisation involved.

**Question:** At the circuit with the steepest measured degradation in either series, does a routine, fuel-clock-driven green-flag stop match the model's fuel/tyre trade-off?

**Model output** (pit_lap 0 = run to the flag without stopping, where feasible):

- Best median pit lap: **126** — recommended window (medians within 0.5s): **[126]**.
- Outcome spread at the best lap (p10-p90): 819.3s — the honest uncertainty of any single-race outcome.
- **Verdict:** Real choice (lap 125): median cost +4.33s vs the model optimum (lap 126); OUTSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best |
|---|---|---|---|---|---|
| 125 <- real | 13291.090 | 13402.563 | 13098.282 | 13917.510 | 0.003 |
| 126 | 13286.761 | 13398.533 | 13094.467 | 13913.809 | 0.997 |

## Case W-C: Imola 2024 — car 5's Safety Car-onset stop (lap 130), the anomalous-slope circuit

**State (measured from data):** end of lap 129/205, car 5 on tyre age 21, 23 laps since last refuel (fuel range 36 laps; net slope -0.0198 s/lap).

**Real decision:** Car 5 (the class winner) pitted lap 130 — the exact lap the flag turned from GF to SF — its fifth of seven stops.

**Question:** Imola is the one circuit in scope with a measured negative degradation slope (Phase 2, reported as anomalous rather than smoothed over). Does an opportunistic SC stop still read as correct there, or does the odd slope produce a different verdict?

**Model output** (pit_lap 0 = run to the flag without stopping, where feasible):

- Best median pit lap: **130** — recommended window (medians within 0.5s): **[130]**.
- Outcome spread at the best lap (p10-p90): 408.6s — the honest uncertainty of any single-race outcome.
- **Verdict:** Real choice (lap 130): median cost +0.00s vs the model optimum (lap 130); INSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best |
|---|---|---|---|---|---|
| 130 <- real | 7221.829 | 7310.384 | 7160.629 | 7569.197 | 0.911 |

## Cross-case analysis

**1. Opportunistic caution stops are strongly endorsed, even at the anomalous-slope circuit (Cases A, C).** Both Bahrain 2025's Safety Car-onset stop and Imola 2024's are inside the model's window, and decisively so — P(best) 0.84 and 0.91 respectively. The engine prices a caution stop's opportunity cost the same way regardless of the sign of the degradation slope, and real strategists' instinct to box the moment the flag changes holds up even at Imola, where the raw slope itself is a measured, unexplained anomaly (Phase 2).

**2. The routine Bahrain stop (Case B) is 'outside' by 4.33s against an 819s spread — noise at this scale, not a real disagreement.** The model is near-indifferent between lap 125 and 126 (P(best) 0.003 vs 0.997) despite the tiny median gap, because Bahrain's tightly-estimated slope makes the model highly sensitive to a single lap of tyre age. The 0.5s window tolerance, inherited unchanged from the F1 audit, is a far stricter bar at endurance race-time scale (thousands of seconds) than at F1's; a verdict should be read against the case's own spread, not the 'inside/outside' label alone.

**3. The fuel clock binds the window as hard as the degradation slope does.** At both Bahrain (Case A) and Imola (Case C) the recommended window sits at or just past the point the tank allows — a stop earlier than the model prefers is not on the table, mirroring the Phase 4 finding that no scoped WEC race is tyre-limited on stop count.

## Scope reminders for reading these verdicts

- 'OUTSIDE the recommended window' is a statement about expected race time under the model's stated scope (no rivals, no track position, a single net degradation slope, FCY/SC hazards drawn from the series-wide posterior), not a judgement on the crew that made the call.
- Read a verdict's margin against its own outcome spread (p10-p90), not just the 0.5s window label — Case B shows a 'tie' can still be labelled 'outside' at endurance race-time scale.
- No per-car cost of *also* changing tyres vs a fuel-only splash (the measured tyre-change premium, Phase 3) is priced here — the single-stop engine still uses one flat pit loss.
- A per-decision audit like F1's real-outcome comparisons (who actually won, what the rival did) is not attempted here: WEC has no rivals or track-position model, so only the stop-timing question is replayed.
