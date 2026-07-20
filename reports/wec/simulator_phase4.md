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
