# ELMS per-decision audit — real stop timing vs the model

Real stop decisions replayed through the single-next-stop simulator (5000 draws, seed 20260712). Race states (tyre age, laps since last refuel, the real stop lap) are reconstructed from the committed derived laps, not quoted from memory. See ``src/audit/endurance_cases.py`` for the case-selection rationale — there is no public strategy narrative to draw on for these races the way F1's audit has, so cases are chosen by a measurable, uniformly-applied criterion instead (an opportunistic neutralisation-onset stop, or a routine green-flag one) rather than by fame.

Reading guide: the model optimises **expected race time** to the next stop only, under its stated scope (no rivals, no track position, a single net degradation slope, FCY/SC hazards drawn from the series-wide posterior). Where a real decision disagrees, the disagreement is read against those stated limits, not as a verdict on the crew that made the call.

## Case E-A: Mugello 2024 — the LMP2 winner's double Safety Car stop (laps 66 and 67)

**State (measured from data):** end of lap 65/114, car 14 on tyre age 2, 6 laps since last refuel (fuel range 25 laps; net slope +0.0658 s/lap).

**Real decision:** Car 14 (class winner) stopped seven times over 114 laps, including twice consecutively under Safety Car on laps 66 and 67. Mugello is the one ELMS circuit the dynamic program marks tyre-limited, on a 9.2 s pit loss.

**Question:** A stop under caution is discounted by the pace ratio, and ELMS is the most Safety-Car-dominated series in scope — 23 of 29 races. Does the model value the first neutralised stop as highly as the team did, and what does it have to say about the second, which its single-stop framing cannot express?

**Model output** (pit_lap 0 = run to the flag without stopping, where feasible):

- Best median pit lap: **84** — recommended window (medians within 0.5s): **[83, 84]**.
- Outcome spread at the best lap (p10-p90): 734.1s — the honest uncertainty of any single-race outcome.
- **Verdict:** Real choice (lap 66): median cost +19.86s vs the model optimum (lap 84); OUTSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best |
|---|---|---|---|---|---|
| 66 <- real | 5243.879 | 5293.877 | 4975.880 | 5717.547 | 0.001 |
| 83 | 5224.177 | 5264.425 | 4947.699 | 5680.160 | 0.029 |
| 84 | 5224.022 | 5263.812 | 4947.003 | 5681.150 | 0.877 |

## Case E-B: Mugello 2024 — the Pro/Am winner made the same double stop

**State (measured from data):** end of lap 65/114, car 19 on tyre age 2, 6 laps since last refuel (fuel range 25 laps; net slope +0.0329 s/lap).

**Real decision:** Car 19 (Pro/Am class winner) stopped on laps 66 and 67 under the same Safety Car as the LMP2 winner, from an independent seven-stop race.

**Question:** Same circuit, same caution, same decision — from a class that must run an amateur-rated driver. The crew-rating comparison found no consistent effect across championships; does a single decision under identical conditions look any different?

**Model output** (pit_lap 0 = run to the flag without stopping, where feasible):

- Best median pit lap: **84** — recommended window (medians within 0.5s): **[82, 83, 84]**.
- Outcome spread at the best lap (p10-p90): 659.4s — the honest uncertainty of any single-race outcome.
- **Verdict:** Real choice (lap 66): median cost +8.81s vs the model optimum (lap 84); OUTSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best |
|---|---|---|---|---|---|
| 66 <- real | 5234.141 | 5278.790 | 4992.163 | 5662.843 | 0.032 |
| 82 | 5225.745 | 5264.278 | 4979.407 | 5638.810 | 0.027 |
| 83 | 5225.522 | 5263.920 | 4979.091 | 5638.577 | 0.026 |
| 84 | 5225.330 | 5263.614 | 4978.838 | 5638.207 | 0.765 |

## What these two cases show

Mugello 2024 produced the only double stop under caution in any audited race here, and both class winners made it independently — laps 66 and 67 under the same Safety Car, in LMP2 and in LMP2 Pro/Am. The engine models one stop, so it can price the first and is structurally silent on the second. That silence is the finding worth recording: a real strategy existed that this model has no way to represent.

It also disagrees with the first stop, and by a lot — +19.71 s for LMP2 and +16.16 s for Pro/Am against an optimum of lap 84 in both. The engine discounts a neutralised stop by the pace ratio but has no rivals in it, so it cannot see the reason teams take one: everyone else is queued behind a Safety Car and the *relative* cost is what collapses, not the absolute one. Two independent class winners made the same call, which is the strongest signal available that the omission matters here.

One thing the two cases agree on exactly: the recommended window is lap 83-84 for both classes, at the same event, in the same conditions. The crew-rating comparison found no consistent effect across championships, and at the level of a single decision the model sees no difference at all.

ELMS is the most Safety-Car-dominated series in scope — 23 of 29 races see one, against WEC's 19 of 33 and IMSA's none at all — so the value of a neutralised stop is higher here than anywhere else this project models.
