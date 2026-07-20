# Phase 3 (IMSA) — strategy simulator

Same philosophy as the F1 engine: every constant measured, uncertainty
propagated per draw, common random numbers across candidates, a distribution
returned rather than a single "pit on lap N". `src/simulator/endurance.py`.

## Measured inputs per circuit (nothing assumed)

| Circuit | Green pace (s) | Pit loss (s) | FCY pace ratio | Fuel range (laps) | Net degradation slope |
|---|---|---|---|---|---|
| Watkins Glen | 96.2 | 60.6 | 2.03 | 34 | −0.0074 (covers 0) |
| Sebring | 111.6 | 72.1 | 1.90 | 29 | +0.0040 (covers 0) |
| Mosport | 69.7 | 56.9 | 1.93 | 50 | −0.0038 (covers 0) |
| Road America | 112.4 | 76.7 | 2.18 | 29 | **−0.0358** (significant) |

Pit loss is measured exactly as in F1 (in-lap + out-lap minus twice the car's
own green pace, green-flanked stops only), which here averages **~66 s**
against F1's 19-27 s, because IMSA stops refuel and usually change driver.

IMSA has **no observed Safety Car** in 63 races ([Phase 2](safety_car_phase2.md)),
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
| Watkins Glen | 103 | 0.55 | 15.6 s |
| Sebring | 182 | 0.60 | 13.5 s |
| Mosport | 80 | 0.37 | **1.3 s** |
| Road America | 44 | 0.65 | **40.0 s** |

Road America — the one circuit with a significant (if physically puzzling,
see [Phase 1](degradation_phase1.md)) degradation slope — gives the most
decisive recommendation of the four, exactly as expected: the simulator's
confidence tracks the strength of the underlying degradation signal, not a
fixed per-circuit assumption.

## Limitations

- **Single next stop.** The engine evaluates the next stop, not the full
  multi-stop sequence a 6-12h race needs.
- **No rivals, no track position** — unlike the F1 engine, there is no
  `P(ahead)`; IMSA is multi-class (GTP/GTD/GTDPRO/LMP2/LMP3) with heavy
  traffic that a two-car abstraction would not represent honestly.
- **No driver-stint regulatory constraints** (minimum/maximum driving time per
  driver) are modelled.
- **Per-race, not per-season.** Each circuit's model is fitted on one 2023
  race; [Phase 1](degradation_phase1.md)'s cross-*circuit* LORO already shows
  slopes do not transfer, and cross-season stability has not yet been tested.
- Road America's negative net slope (Phase 1) propagates into this simulator
  as-is — the honest but unresolved anomaly is not hidden by the strategy
  layer either.
