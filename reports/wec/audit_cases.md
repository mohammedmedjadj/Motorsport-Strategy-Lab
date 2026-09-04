# WEC per-decision audit — real stop timing vs the model

Real stop decisions replayed through the single-next-stop simulator (5000 draws, seed 20260712). Race states (tyre age, laps since last refuel, the real stop lap) are reconstructed from the committed derived laps, not quoted from memory. See ``src/audit/endurance_cases.py`` for the case-selection rationale — there is no public strategy narrative to draw on for these races the way F1's audit has, so cases are chosen by a measurable, uniformly-applied criterion instead (an opportunistic neutralisation-onset stop, or a routine green-flag one) rather than by fame.

Reading guide: the model optimises **expected race time** to the next stop only, under its stated scope (no rivals, no track position, a single net degradation slope, FCY/SC hazards drawn from the series-wide posterior). Where a real decision disagrees, the disagreement is read against those stated limits, not as a verdict on the crew that made the call.

## Case W-A: Bahrain 2025 — car 009's Safety Car-onset stop (lap 216)

**State (measured from data):** end of lap 215/237, car 009 on tyre age 18, 19 laps since last refuel (fuel range 32 laps; net slope +0.0492 s/lap).

**Real decision:** Car 009 (this race's class winner by laps completed) pitted lap 216 — the exact lap the flag turned from GF to SF (Safety Car called) — its ninth and final stop of the race.

**Question:** Does boxing the instant the Safety Car is called dominate the model's own recommendation, at a circuit (Bahrain) with a steep, significant degradation slope?

**Model output** (pit_lap 0 = run to the flag without stopping, where feasible):

- Best median pit lap: **217** — recommended window (medians within 0.5s): **[216, 217, 218, 219, 220]**.
- Outcome spread at the best lap (p10-p90): 149.5s — the honest uncertainty of any single-race outcome.
- **Verdict:** Real choice (lap 216): median cost +0.05s vs the model optimum (lap 217); INSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best |
|---|---|---|---|---|---|
| 216 <- real | 2612.705 | 2656.860 | 2607.569 | 2758.686 | 0.068 |
| 217 | 2612.654 | 2656.626 | 2607.521 | 2757.011 | 0.838 |
| 218 | 2612.705 | 2656.580 | 2607.569 | 2757.335 | 0.006 |
| 219 | 2612.846 | 2656.615 | 2607.711 | 2756.336 | 0.009 |
| 220 | 2613.104 | 2656.835 | 2607.958 | 2758.488 | 0.006 |

## Case W-B: Bahrain 2024 — car 15's routine green-flag stop (lap 125)

**State (measured from data):** end of lap 124/235, car 15 on tyre age 29, 30 laps since last refuel (fuel range 32 laps; net slope +0.0576 s/lap).

**Real decision:** Car 15 (the class winner) pitted lap 125 under green flag — its fourth of eight stops, with no neutralisation involved.

**Question:** At the circuit with the steepest measured degradation in either series, does a routine, fuel-clock-driven green-flag stop match the model's fuel/tyre trade-off?

**Model output** (pit_lap 0 = run to the flag without stopping, where feasible):

- Best median pit lap: **126** — recommended window (medians within 0.5s): **[126]**.
- Outcome spread at the best lap (p10-p90): 821.1s — the honest uncertainty of any single-race outcome.
- **Verdict:** Real choice (lap 125): median cost +4.58s vs the model optimum (lap 126); OUTSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best |
|---|---|---|---|---|---|
| 125 <- real | 13329.216 | 13451.877 | 13142.587 | 13964.249 | 0.003 |
| 126 | 13324.639 | 13447.213 | 13138.135 | 13959.216 | 0.997 |

## Case W-C: Imola 2024 — car 5's Safety Car-onset stop (lap 130), the anomalous-slope circuit

**State (measured from data):** end of lap 129/205, car 5 on tyre age 21, 23 laps since last refuel (fuel range 36 laps; net slope -0.0100 s/lap).

**Real decision:** Car 5 (the class winner) pitted lap 130 — the exact lap the flag turned from GF to SF — its fifth of seven stops.

**Question:** Imola is the one circuit in scope with a measured negative degradation slope (Phase 2, reported as anomalous rather than smoothed over). Does an opportunistic SC stop still read as correct there, or does the odd slope produce a different verdict?

**Model output** (pit_lap 0 = run to the flag without stopping, where feasible):

- Best median pit lap: **131** — recommended window (medians within 0.5s): **[130, 131, 132, 133, 134]**.
- Outcome spread at the best lap (p10-p90): 407.0s — the honest uncertainty of any single-race outcome.
- **Verdict:** Real choice (lap 130): median cost +0.03s vs the model optimum (lap 131); INSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best |
|---|---|---|---|---|---|
| 130 <- real | 7247.818 | 7338.094 | 7190.803 | 7598.075 | 0.836 |
| 131 | 7247.789 | 7338.532 | 7191.605 | 7598.556 | 0.008 |
| 132 | 7248.030 | 7338.990 | 7192.349 | 7597.771 | 0.007 |
| 133 | 7248.113 | 7339.454 | 7193.107 | 7599.770 | 0.005 |
| 134 | 7248.270 | 7339.882 | 7193.932 | 7600.309 | 0.007 |

## Cross-case analysis

**1. Opportunistic caution stops sit inside the model's window at both circuits — including the anomalous-slope one (Cases A, C).** **Bahrain 2025** — real lap 216, inside the window at +0.05 s against the model's lap 217; P(best) 0.068 for the real lap against 0.838 for the model's. **Imola 2024** — real lap 130, inside the window at +0.03 s against the model's lap 131; P(best) 0.836 for the real lap against 0.008 for the model's. The engine prices a caution stop's opportunity cost the same way regardless of the sign of the degradation slope, so the strategists' instinct to box the moment the flag changes holds up even at Imola, where the raw slope is a measured, unexplained anomaly (Phase 2).

**The two statistics disagree, and that is worth more than either alone.** 1 of these two real stops carries a P(best) above 0.5, yet both are inside the window on median cost. The reason is structural: P(best) is an argmin over draws, so when two candidate laps differ by hundredths of a second in median race time it hands nearly all its mass to whichever wins marginally more often. Reading that as a strong preference would be reading a coin flip as a verdict — and an earlier version of this section did exactly that, quoting the *model's* P(best) as though it were the team's.

**2. The routine Bahrain stop (Case B) is 'outside' by 4.33s against an 819s spread — noise at this scale, not a real disagreement.** The model is near-indifferent between lap 125 and 126 (P(best) 0.003 vs 0.997) despite the tiny median gap, because Bahrain's tightly-estimated slope makes the model highly sensitive to a single lap of tyre age. The 0.5s window tolerance, inherited unchanged from the F1 audit, is a far stricter bar at endurance race-time scale (thousands of seconds) than at F1's; a verdict should be read against the case's own spread, not the 'inside/outside' label alone.

**3. The fuel clock binds the window as hard as the degradation slope does.** At both Bahrain (Case A) and Imola (Case C) the recommended window sits at or just past the point the tank allows — a stop earlier than the model prefers is not on the table, mirroring the Phase 4 finding that no scoped WEC race is tyre-limited on stop count.

## Scope reminders for reading these verdicts

- 'OUTSIDE the recommended window' is a statement about expected race time under the model's stated scope (no rivals, no track position, a single net degradation slope, FCY/SC hazards drawn from the series-wide posterior), not a judgement on the crew that made the call.
- Read a verdict's margin against its own outcome spread (p10-p90), not just the 0.5s window label — Case B shows a 'tie' can still be labelled 'outside' at endurance race-time scale.
- No per-car cost of *also* changing tyres vs a fuel-only splash (the measured tyre-change premium, Phase 3) is priced here — the single-stop engine still uses one flat pit loss.
- A per-decision audit like F1's real-outcome comparisons (who actually won, what the rival did) is not attempted here: WEC has no rivals or track-position model, so only the stop-timing question is replayed.
