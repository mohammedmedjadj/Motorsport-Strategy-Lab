# Phase 3 (WEC) — strategy simulator

Same philosophy as the F1 engine: every constant measured, uncertainty
propagated per draw, common random numbers across candidates, a distribution
returned rather than a single "pit on lap N". `src/simulator/endurance.py`.

## Measured inputs per circuit (nothing assumed)

| Circuit | Green pace (s) | Pit loss (s) | FCY ratio | SC ratio | Fuel range (laps) | Net degradation slope (2024) |
|---|---|---|---|---|---|---|
| Spa | 130.7 | 63.0 | 1.77 | 2.17 | 28 | **+0.0404** (significant) |
| Fuji | 93.0 | 79.0 | 1.37 | 1.53 | 42 | **+0.0135** (significant) |
| Bahrain | 114.6 | 80.6 | 1.89 | 1.91 | 32 | **+0.0493** (significant) |
| Imola | 94.9 | **26.8** | 1.61 | 1.71 | 36 | **−0.0198** (significant, anomalous) |

These are each circuit's 2024 fit (the demo scenario below uses it);
[Phase 2](degradation_phase2.md) has 2023/2025 fits too (or 2025 only for
Imola), where every circuit's slope moves between seasons — Bahrain is the
sole exception, staying in a tight +0.042 to +0.049 band. The simulator's
degradation input for a real decision should use the season actually being
raced, not a value frozen from a different year.

Pit loss is measured exactly as in F1, and Imola stands out: **26.8 s**, a third
of Spa/Fuji/Bahrain's 63-81 s — a genuinely shorter or faster pit lane at that
circuit, the WEC analogue of the F1 project's own finding that Monaco's pit
loss (19.1 s) is very different from Singapore's (27.3 s). It is reported as
measured, not treated as suspicious.

## WEC-specific: two neutralisation kinds, both modelled

Unlike IMSA, WEC has real Safety Car (`SF`) laps at every scoped circuit
([Phase 3](safety_car_phase3.md) found SC is used *more* than FCY everywhere),
so the engine samples **both hazards independently per draw** and prices each
lap by whichever kind is active, exactly mirroring how the F1 engine handles
SC vs VSC. The Safety Car pace ratio is measured directly from each race's own
`SF`-flagged laps (`sc_ratio_measured = True` everywhere in WEC) rather than
borrowed from the FCY ratio — and it is consistently the **slower** of the two
(2.17 vs 1.77 at Spa; 1.53 vs 1.37 at Fuji), consistent with a full Safety Car
bunching the field more than a Full Course Yellow does.

## Demo scenario per circuit (mid-race, 8 laps of fuel and tyre age used)

| Circuit | Best-median pit lap | P(best) | Spread across candidates |
|---|---|---|---|
| Spa | 90 | 0.88 | 35.5 s |
| Fuji | 140 | 0.79 | 28.0 s |
| Bahrain | 141 | 0.92 | 93.4 s |
| Imola | 103 | 0.95 | 34.1 s |

All four give decisive recommendations (P(best) 0.79-0.98) — consistent with
every WEC circuit in scope having a degradation slope clear of zero (unlike
three of IMSA's four circuits). At Spa specifically, the recommended lap
(90) is not the tyre-optimal lap: with 71 laps remaining and a clearly
positive slope, tyres alone would want a stop nearer lap 106, but the fuel tank
runs dry at lap 90 — the simulator lands exactly on that boundary. **The
binding constraint is fuel, not tyre wear**, a situation with no F1 equivalent
and pinned by a regression test (`test_spa_optimum_is_pinned_by_the_fuel_constraint`).

## Track-position value (overtaking difficulty)

The endurance schema has no per-lap position, so on-track order is reconstructed
from cumulative race time within the class, then the adjacent-pair swap rate is
measured exactly as for F1 (`data/derived/endurance/endurance_overtaking_difficulty.csv`):

| Circuit | Adjacent swap rate / green lap | P(hold 15 laps) |
|---|---|---|
| Fuji | 0.031 | 0.63 |
| Bahrain | 0.031 | 0.63 |
| Imola | 0.035 | 0.58 |
| Spa | 0.043 | 0.52 |

HYPERCAR racing is far more fluid than an F1 street circuit (Monaco 0.004):
a BoP-equalised prototype field changes position often, so track position won
in the pits is only provisional. This is the primitive the adversarial rival
model consumes.

## Adversarial rival (the rival covers)

The same two-player pit-stop game as F1 ([adversarial_rival.md](../f1/adversarial_rival.md)),
on the endurance engine: `src/simulator/adversarial_endurance.py`. The rival
covers instead of following a fixed plan; the exchange is resolved lap by lap
and the lead locked in with the measured endurance overtaking difficulty above.

The endurance result is a clean one: **the value of covering scales with the
circuit's degradation.** At Bahrain — steep, significant net slope (+0.049 s/lap)
— an uncovered undercut is enormously powerful, so assuming the rival keeps its
plan overstates the ego car's win probability by **~0.44** (0.90 if the rival
sits out, 0.47 once it covers). Where degradation is flat (Watkins Glen, IMSA)
the undercut is weak and covering barely moves the number (~0.08). A frozen-rival
simulator is therefore most dangerously optimistic exactly where tyres matter
most — which the model quantifies rather than assumes.

## Inter-class traffic cost (endurance's unique problem)

A HYPERCAR never runs in clean air for long — it is forever lapping LMGT3 cars,
and each one it fights past costs time. No single-class F1 project models this;
here it is measurable. On-track order across classes is recovered from
start/finish crossing times (a GT that crosses the line just before a prototype
is right ahead of it, whatever lap either is on — the lapping problem solved
without positions), and for each prototype green lap we count the GT cars that
crossed within 12 s ahead, then measure how much slower that lap runs than the
car's own clean pace. Every in-scope season is now measured, not one, so the
figure below is a **mean across seasons with its season-to-season spread**
(`endurance_traffic_cost.csv` per race, `endurance_traffic_stability.csv` pooled):

| Circuit | Clear-air vs in-traffic mean (SD) | Cost per GT car ahead mean (SD) | Seasons |
|---|---|---|---|
| Spa | **+0.58** (±0.29) | **+0.21** (±0.09) | 3 |
| Imola | +0.15 (±0.05) | −0.01 (±0.01, no signal) | 2 |
| Fuji | +0.14 (±0.05) | +0.04 (±0.02) | 3 |
| Bahrain | +0.13 (±0.14) | +0.10 (±0.04) | 3 |

Spa is still the clearest case — the largest traffic cost measured in either
series — but the multi-season view **corrects a single-season overclaim**: the
+0.95 s/lap reported earlier was Spa's 2024 alone, its steepest edition; across
2023-2025 the mean is **+0.58 s/lap** (the three seasons run 0.25 / 0.95 / 0.55).
The per-GT-car slope is the more stable signal, holding at ~0.21 s. The result
is **honestly non-uniform** across both circuits and seasons, and now the spread
is quantified rather than hidden: Bahrain's clear-vs-traffic contrast even flips
sign in 2023 (a HYPERCAR there rarely saw clear air), Imola's per-car slope is
flat, and clear air beats the car's own median at 20 of 21 race-seasons (WEC
Bahrain 2023 the lone +0.03 s exception). Honest caveats remain: the "clean
pace" baseline is the car's own median, so races with little clear air compress
the contrast; the 12 s window is a parameter. Feeding a stochastic traffic cost
into the simulator's per-lap time is the natural next step.

## Pit-stop procedure: tyres cost far more than in IMSA (measured)

WEC's rulebook forbids touching the tyres until the fuel hose is out — refuel
**then** tyres, in sequence — whereas IMSA services both at once. That rule
leaves a measurable fingerprint in the raw stop durations, pooled across all
scoped races (`data/derived/endurance/endurance_pit_procedure.csv`):

| Series | Fuel-only stop | Fuel + tyres | Tyre-change premium |
|---|---|---|---|
| WEC (sequential) | 56.0 s | 78.5 s | **+22.5 s** |
| IMSA (parallel) | 63.0 s | 69.6 s | +6.6 s |

Fitting tyres in WEC costs **~3x** what it does in IMSA relative to a fuel-only
splash. Strategically that raises the bar for a tyre change: a WEC splash-and-go
is comparatively cheap, so tyres are only worth taking when the pace gain
clearly outweighs the ~22 s. (The simulator currently prices a stop with a
single measured pit loss; splitting it by whether tyres are taken, using this
premium, is the natural next refinement.)

## Limitations

- **Single next stop.** The engine evaluates the next stop, not the 5-10 stops
  a 6-8h race actually needs.
- **No rivals, no track position** — unlike the F1 engine, there is no
  `P(ahead)`; WEC is multi-class (HYPERCAR racing among LMGT3 traffic) with
  heavy traffic that a two-car abstraction would not represent honestly.
- **No driver-stint regulatory constraints** (WEC mandates 3 drivers minimum)
  are modelled.
- **SC and FCY hazards are sampled independently**, though Phase 2 notes an
  FCY can in reality escalate into an SC, so the two rates are not fully
  independent — the same caveat the F1 phase states for its own SC/VSC pair.
- **Cross-season stability is poor almost everywhere, and now measured, not
  assumed.** [Phase 2](degradation_phase2.md)'s leave-one-season-out CV (3
  seasons at Spa/Fuji/Bahrain, 2 at Imola) shows near-zero or negative mean R²
  at Spa and Imola; Fuji is modest; **Bahrain is a genuine exception**, with a
  tightly-banded slope and R² around +0.21. The demo above uses each circuit's
  2024 fit specifically, not a value assumed stable.
- Imola's anomalous negative net slope (Phase 1) propagates into this
  simulator as-is.
