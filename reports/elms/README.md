# ELMS — two classes, never pooled

The European Le Mans Series is modelled as **two separate classes**, `LMP2` and
`LMP2 Pro/Am`. They share the source, the code and the car; they share no
fitted number.

ELMS was not added for breadth. It was added because it is the one championship
that could **falsify a hypothesis this project had carried since its Formula 1
phase**, and it did. Full argument: [`methodology.md`](methodology.md).

| class | what it is | race-seasons | circuits | seasons | median slope |
|---|---|---|---|---|---|
| [**LMP2**](lmp2/) | near-spec Oreca 07 / Gibson; professional crews from 2023 | 25 | 9 | 2021–2025 | +0.0161 s/lap |
| [**LMP2 Pro/Am**](lmp2_proam/) | the same car, a bronze-rated driver mandatory | 17 | 8 | 2023–2025 | +0.0205 s/lap |

**52,472 race laps, ~70% kept for modelling.** Fields run 7–17 cars, so the
cluster-robust `t(G−1)` reference is doing real work: at 7 cars it is a `t(6)`,
whose 95% interval is 22% wider than the normal's.

## The label trap, and why every comparison starts at 2023

**Before 2023 the `LMP2` label covers every LMP2 entry**, not the professional
subset. Pairing the full 2021–2025 range against `LMP2 Pro/Am` would compare a
*mixed* field against a Pro/Am one and report the difference as a crew effect.

Every cross-class comparison here is restricted to 2023 onward for that reason,
and the restriction lives in code
([`src/degradation/crew_rating.py`](../../src/degradation/crew_rating.py)),
not in a reader's memory.

## What this series settled

- **Slope instability is not the machinery.** LMP2 is close to a one-make
  formula — one chassis, one engine, no Balance of Performance. Degradation
  slopes still fail to transfer between seasons, exactly as they do in the
  BoP-adjusted classes: leave-one-race-out R² is at or below zero at every
  circuit, reaching −0.455 at Portimao for Pro/Am. A negative control, and the
  most useful thing this series contributed.
- **A second crew-rating experiment, disagreeing with IMSA's.** Pro/Am crews
  here fit a slope **−0.0053 s/lap shallower** (17 pairs, p = 0.148) where
  IMSA's fit +0.0040 steeper (p = 0.032). Neither survives its own robustness
  checks. [`crew_rating_findings.md`](crew_rating_findings.md).
- **A third neutralisation regime.** A Safety Car in 23 of 29 races, against
  WEC's 19 of 33 and IMSA's 0 of 63.

## What is series-level, and what is per class

The phase reports stay at series level because they genuinely report **both
classes side by side**, in the same tables — which is the honest form for a
series whose whole point is the comparison between its two classes:

- [`data_availability_phase0.md`](data_availability_phase0.md) ·
  [`data_quality_phase1.md`](data_quality_phase1.md) ·
  [`degradation_phase2.md`](degradation_phase2.md) ·
  [`safety_car_phase3.md`](safety_car_phase3.md) ·
  [`simulator_phase4.md`](simulator_phase4.md) ·
  [`packaging_phase7.md`](packaging_phase7.md)
- [`results.md`](results.md) · [`crew_rating_findings.md`](crew_rating_findings.md)
  · [`audit_cases.md`](audit_cases.md) · [`methodology.md`](methodology.md)

## The complete tables

| | LMP2 | LMP2 Pro/Am |
|---|---|---|
| lap accounting | [25 races](lmp2/data_quality_all_races.md) | [17 races](lmp2_proam/data_quality_all_races.md) |
| fitted slopes | [lmp2](lmp2/degradation_all_races.md) | [lmp2_proam](lmp2_proam/degradation_all_races.md) |
| transfer between seasons | [lmp2](lmp2/transfer_all_races.md) | [lmp2_proam](lmp2_proam/transfer_all_races.md) |
| full-race strategy | [lmp2](lmp2/strategy_all_races.md) | [lmp2_proam](lmp2_proam/strategy_all_races.md) |
