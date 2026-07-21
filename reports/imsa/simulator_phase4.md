# Phase 3 (IMSA) — strategy simulator

Same philosophy as the F1 engine: every constant measured, uncertainty
propagated per draw, common random numbers across candidates, a distribution
returned rather than a single "pit on lap N". `src/simulator/endurance.py`.

## Measured inputs per circuit (nothing assumed)

| Circuit | Green pace (s) | Pit loss (s) | FCY pace ratio | Fuel range (laps) | Net degradation slope (2023) |
|---|---|---|---|---|---|
| Watkins Glen | 96.2 | 60.6 | 2.03 | 34 | −0.0047 (covers 0) |
| Sebring | 111.6 | 72.1 | 1.90 | 29 | +0.0026 (covers 0) |
| Mosport | 69.7 | 56.9 | 1.93 | 50 | −0.0015 (covers 0) |
| Road America | 112.4 | 76.7 | 2.18 | 29 | **−0.0221** (significant) |

These are each circuit's 2023 fit (the demo scenario below uses it); Road
America and Watkins Glen additionally have 2024/2025 fits in
[Phase 2](degradation_phase2.md), where the slope moves considerably between
seasons — the simulator's degradation input for a real decision should always
use the season actually being raced, not a value frozen from a different year.

Pit loss is measured exactly as in F1 (in-lap + out-lap minus twice the car's
own green pace, green-flanked stops only), which here averages **~66 s**
against F1's 19-27 s, because IMSA stops refuel and usually change driver.

IMSA has **no observed Safety Car** in 63 races ([Phase 3](safety_car_phase3.md)),
so the simulator's Safety Car pace ratio falls back to the FCY ratio at every
circuit (flagged via `sc_ratio_measured = False`) rather than a Safety-Car-free
model silently pretending the state cannot occur — Phase 2's near-zero Gamma
posterior is still sampled, it is just vanishingly rare in practice.

## Two structural differences from F1 (both bind in practice)

**1. Fuel range is a hard constraint, not a preference.** An F1 car may choose
to run to the flag; an IMSA car cannot beyond its tank. The candidate set is
capped at `current_lap + (fuel_range_laps - laps_since_refuel)`, and a
regression test pins that the simulator rejects a scenario where fuel is
already exhausted rather than silently returning nonsense.

**2. Circuits with no measurable net degradation give an honestly flat
recommendation.** Watkins Glen, Sebring and Mosport all have a net slope whose
interval covers zero (Phase 1). Their simulated scenarios show it directly:
Mosport's spread across all candidate pit laps is **1.3 s** out of a
multi-thousand-second remaining race — the model reports indistinguishability
rather than manufacturing a confident answer.

## Demo scenario per circuit (mid-race, 8 laps of fuel and tyre age used)

| Circuit | Best-median pit lap | P(best) | Spread across candidates |
|---|---|---|---|
| Watkins Glen | 103 | 0.50 | 12.7 s |
| Sebring | 182 | 0.55 | 11.6 s |
| Mosport | 80 | 0.30 | **1.8 s** |
| Road America | 44 | 0.65 | **38.8 s** |

Road America — the one circuit with a significant (if physically puzzling,
see [Phase 2](degradation_phase2.md)) degradation slope — gives the most
decisive recommendation of the four, exactly as expected: the simulator's
confidence tracks the strength of the underlying degradation signal, not a
fixed per-circuit assumption.

## Track-position value (overtaking difficulty)

The endurance schema has no per-lap position, so on-track order is reconstructed
from cumulative race time within the class, then the adjacent-pair swap rate is
measured exactly as for F1 (`data/derived/endurance/endurance_overtaking_difficulty.csv`):

| Circuit | Adjacent swap rate / green lap | P(hold 15 laps) |
|---|---|---|
| Mosport | 0.022 | 0.72 |
| Sebring | 0.034 | 0.59 |
| Watkins Glen | 0.044 | 0.51 |
| Road America | 0.051 | 0.46 |

IMSA GTP racing is markedly more fluid than an F1 street circuit (Monaco sits at
0.004): prototypes in a BoP-equalised, multi-class field change position far
more often, so a lead won in the pits is only ever provisional here. This is the
primitive the adversarial rival model consumes.

## Adversarial rival (the rival covers)

The same two-player pit-stop game as F1 ([adversarial_rival.md](../f1/adversarial_rival.md)),
on the endurance engine: `src/simulator/adversarial_endurance.py`. The rival
covers the undercut rather than following a fixed plan.

The endurance finding is that **the value of covering scales with degradation**.
At Watkins Glen, whose net slope covers zero, the undercut is weak: assuming the
rival keeps its plan overstates the win probability by only **~0.08**, and the
cover-aware optimum barely differs. Contrast WEC Bahrain, where a steep slope
makes an uncovered undercut worth ~0.44 of win probability (see
[the WEC report](../wec/simulator_phase4.md)). So on a low-degradation IMSA
circuit the pit-timing game is nearly moot — and the model says so, instead of
manufacturing a decisive call.

## Inter-class traffic cost (endurance's unique problem)

IMSA GTP prototypes share the track with **four** slower classes (GTD, GTDPRO,
LMP2, LMP3), so lapping traffic is relentless, and each car fought past costs
time. On-track order across classes is recovered from start/finish crossing
times (a slower car crossing the line just before a GTP is right ahead of it,
whatever lap either is on), and for each GTP green lap we count the other-class
cars within 12 s ahead, then measure the pace lost versus the car's own clean
median. Every in-scope season is now measured, so the figure is a **mean across
seasons with its spread** (`endurance_traffic_cost.csv` per race,
`endurance_traffic_stability.csv` pooled):

| Circuit | Clear-air vs in-traffic mean (SD) | Cost per car ahead mean (SD) | Seasons |
|---|---|---|---|
| Watkins Glen | +0.43 (±0.12) | +0.09 (±0.03) | 3 |
| Mosport | +0.42 (single season) | +0.03 | 1 |
| Road America | +0.20 (±0.20) | +0.08 (±0.04) | 3 |
| Sebring | +0.11 (±0.09) | +0.08 (±0.02) | 3 |

Clear-air laps beat the car's own median at every IMSA race-season, and a GTP
loses ~0.2-0.4 s a lap in traffic. The multi-season view **revises one earlier
single-season read**: Sebring looked like "no signal" from 2023 alone
(−0.02 s/lap), but across 2023-2025 it averages **+0.11 s/lap** (−0.01 / +0.13 /
+0.21) — the contrast was compressed that one 12-hour, five-class year, not
absent. Watkins Glen is the most *stable* meaningful cost (+0.43 ± 0.12); Road
America is real on average but swings hardest season to season (±0.20). The
per-car slope is positive and tight everywhere. Reported as measured, spread and
all, not smoothed. See the [WEC report](../wec/simulator_phase4.md) for the
cross-series picture (Spa is the most traffic-costly circuit measured,
~+0.58 s/lap averaged over three seasons).

## Pit-stop procedure: tyres are nearly free vs WEC (measured)

IMSA services tyres **in parallel** with refuelling, so a tyre change adds little
over a fuel-only stop — the opposite of WEC, which is sequential (fuel then
tyres). Pooled across all scoped races
(`data/derived/endurance/endurance_pit_procedure.csv`):

| Series | Fuel-only stop | Fuel + tyres | Tyre-change premium |
|---|---|---|---|
| IMSA (parallel) | 63.0 s | 69.6 s | **+6.6 s** |
| WEC (sequential) | 56.0 s | 78.5 s | +22.5 s |

A tyre change costs IMSA only ~7 s over a splash, against ~23 s in WEC — a 3x
difference straight from the two series' procedural rules, and confirmed here
from the raw stop durations. Strategically it means IMSA teams can take tyres
almost whenever they stop for fuel, a flexibility WEC teams do not have. See
[the WEC report](../wec/simulator_phase4.md) for the contrast.

## Limitations

- **Single next stop.** The engine evaluates the next stop, not the full
  multi-stop sequence a 6-12h race needs.
- **No rivals, no track position** — unlike the F1 engine, there is no
  `P(ahead)`; IMSA is multi-class (GTP/GTD/GTDPRO/LMP2/LMP3) with heavy
  traffic that a two-car abstraction would not represent honestly.
- **No driver-stint regulatory constraints** (minimum/maximum driving time per
  driver) are modelled.
- **Cross-season stability is poor, and now measured, not assumed.**
  [Phase 2](degradation_phase2.md)'s leave-one-season-out CV (3 seasons at
  Watkins Glen/Sebring/Road America) shows slopes moving considerably between
  editions and a near-zero mean R², plus a separate leave-one-*circuit*-out
  result showing the same failure to transfer across tracks. The demo above
  uses each circuit's 2023 fit specifically, not a value assumed stable.
- Road America's negative net slope (Phase 1) propagates into this simulator
  as-is — the honest but unresolved anomaly is not hidden by the strategy
  layer either.
