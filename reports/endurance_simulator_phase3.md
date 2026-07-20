# Phase 3 (endurance) — strategy simulator

Same philosophy as the F1 engine — every constant measured, uncertainty
propagated, distributions rather than a single answer — applied to a decision
problem that differs from F1 in three material ways.

## Measured inputs (nothing assumed)

| Input | IMSA Watkins Glen 2023 (GTP) | WEC Spa 2024 (HYPERCAR) | F1 for scale |
|---|---|---|---|
| Green pace | 96.2 s | 130.7 s | 78-99 s |
| Green-flag pit loss | **60.6 s** (IQR 26.1, n=43) | **63.0 s** (IQR 17.8, n=66) | 19-27 s |
| Neutralised pace ratio | **2.03** | **1.77** | ~1.4 (SC) |
| Fuel range | **34 laps** | **28 laps** | n/a (no refuelling) |
| Net degradation slope | −0.007 s/lap (covers 0) | +0.042 s/lap | per-compound |

Pit loss is measured exactly as in F1 — in-lap + out-lap minus twice the car's
own green pace, restricted to stops where both laps ran green — with the same
2× median trim, which here removes cars sitting in the garage for repairs
(one "stop" exceeded 6 800 s).

## Three structural differences from F1

**1. Fuel range is a hard constraint.** An F1 car may choose not to stop; an
endurance car cannot. The candidate set is bounded above by the tank, not by
taste. This *binds* in practice: at Spa, with 71 laps left and a clearly positive
degradation slope, tyres want the stop near the middle of the remaining race
(~lap 106), but the tank runs dry at lap 90 — and the simulator lands exactly on
that boundary. The binding constraint is fuel, not tyres. A regression test pins
this, because it is the single biggest way endurance strategy departs from F1.

**2. Neutralisations are frequent and brutally slow.** A lap under FCY takes
**2.03×** green at Watkins Glen (1.77× at Spa) against ~1.4× for an F1 safety
car, and IMSA sees roughly one FCY every 48 laps (Phase 2). Stopping under
caution is therefore worth far more than in F1, and the engine prices a stop at
`pit_loss / pace_ratio`.

**3. No compound choice.** Tyre compound is absent from the source, so
degradation enters as the single net slope from Phase 1 rather than a
per-compound polynomial.

## Behaviour on the two real races

The simulator's output tracks each race's Phase 1 finding, which is the point:

- **Spa** (net slope +0.042, interval clear of zero): a decisive recommendation,
  `p_best` > 0.9 concentrated on the fuel-boundary lap.
- **Watkins Glen** (net slope −0.007, interval covering zero): median race time
  varies by **12 s across all 26 candidate laps — 0.1% of the remaining race**.
  The honest reading is that no stop lap is distinguishable, and the model says
  so rather than manufacturing confidence. That is the intended behaviour when
  Phase 1 found no measurable net degradation, not a failure.

Uncertainty propagated per draw: net slope resampled from its Phase 1 interval,
FCY rate from its Phase 2 Gamma posterior, FCY durations from the observed pool,
plus lap noise at the Phase 1 residual scale. Candidates share realisations
(common random numbers), so `p_best` is a clean per-draw argmin.

## Limitations

- **Single next stop.** The engine evaluates the next stop, not the full
  remaining sequence of 5-10 stops a 6 h race needs. Multi-stop scheduling is the
  obvious next step and is not claimed here.
- **No rivals, no track position.** Unlike the F1 engine, there is no rival model
  and so no `P(ahead)`; endurance is multi-class with heavy traffic and modelling
  that honestly needs the class interaction, not a two-car abstraction.
- **No driver-stint constraints.** Minimum/maximum driving-time rules per driver
  are real regulatory constraints and are not modelled.
- **Per-race, not per-circuit.** Both models are fitted on one race each. The F1
  project's leave-one-race-out finding — that slopes move materially between
  events — should be assumed to apply until tested here.
- Neutralised laps carry no degradation or noise term, as in the F1 engine.
