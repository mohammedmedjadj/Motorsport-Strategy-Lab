# Formula 1

One class, **26 circuits, 2022–2026**. FastF1 supplies per-lap timing, tyre
compound and per-lap track status, which is more than the endurance source
carries — so F1 is the only series here with a **per-compound** degradation
model rather than a single net slope.

| | F1 |
|---|---|
| circuits in scope | 26 (25 fitted; Madrid's first race is not yet run) |
| rounds ingested | 104 of 115 |
| fitting window | 2022–2025; 2026 held out as a new regulation era |
| degradation | per compound, 73 coefficients, cluster-robust intervals |
| neutralisations | Safety Car **and** VSC, 25 circuits, 152 editions, 229 events |
| track position | 25 circuits, 0.0047 (Monaco) to 0.064 (Las Vegas) |
| decision audit | 357 replayed stops across 74 races |

## What F1 settled that the endurance series could not

- **Fuel burn and tyre wear are separable.** No refuelling since 2010 means
  fuel mass is a whole-race function of the lap while tyre age resets each
  stint, so a two-regressor fit identifies both. In endurance they are
  inseparable in all but 6 of 210 races, because teams change tyres at
  essentially every fuel stop.
- **Compound is a modelled variable.** The endurance source does not record it
  at all.
- **Track position is measurable and stable.** Adjacent cars swap places at
  0.0047 per lap at Monaco against 0.064 at Las Vegas — a 14-fold range that,
  unlike degradation, transfers between seasons. It is the primitive the
  adversarial-rival model is built on.

## Documents

**The pipeline, phase by phase**
[phase 0 — data availability](data_availability_phase0.md) ·
[phase 1 — data quality](data_quality_phase1.md) ·
[phase 2 — degradation](degradation_phase2.md) ·
[phase 3 — Safety Car / VSC](safety_car_phase3.md) ·
[phase 4 — simulator](simulator_phase4.md) ·
[phase 6 — methodology](methodology.md)

**Decision audits**
[systematic_audit.md](systematic_audit.md) — every first stop on the calendar,
357 decisions on a uniform criterion. This is the one to read.
[audit_cases.md](audit_cases.md) — five races examined in depth, including one
chosen because the model *cannot* see what happened (a red-flag tyre change).

**Extensions**
[adversarial_rival.md](adversarial_rival.md) — the pit stop as a two-player
game, where the rival covers ·
[track_position.md](track_position.md) — overtaking difficulty per circuit ·
[reliability.md](reliability.md) · [weather.md](weather.md)

**The breadth layer** — 35 circuits back to 2011 from a public per-lap history,
trading compound and flag fidelity for fourteen seasons:
[degradation_history.md](degradation_history.md) ·
[pit_loss_history.md](pit_loss_history.md)

## The honest headline

The simulator **stops too late on 80% of the calendar**, by a median of 12 laps.
The audit measures it, refutes the obvious explanation (safety cars the model
cannot foresee — the bias is present on green-flag stops too), and names what
remains untested: the engine optimises one car's time with no track position,
so nothing in it rewards an undercut. See
[`systematic_audit.md`](systematic_audit.md).
