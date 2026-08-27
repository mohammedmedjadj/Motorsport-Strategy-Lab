# WEC — one class, Hypercar

The FIA World Endurance Championship is modelled on its **Hypercar** class only.
Unlike IMSA and ELMS it needs no class branch: one modelled class, so the series
directory *is* the class directory, and the complete per-race tables sit in
[`hypercar/`](hypercar/).

| | Hypercar |
|---|---|
| race-seasons | 28 |
| circuits | 11 |
| seasons | 2022–2026 |
| raw laps | 84,679 (78.4% kept) |
| median net slope | +0.0139 s/lap |
| tyre-change premium | 21.6 s |
| Safety Car in | 19 of 33 races |

## What makes WEC different from the other two endurance series

- **It runs a genuine Safety Car procedure** and prefers it over Full Course
  Yellow. IMSA has shown a Safety Car in **none** of 63 races; ELMS shows one in
  23 of 29. Three championships, three neutralisation regimes, and a pooled
  "endurance" model would describe none of them.
- **It services tyres sequentially, not in parallel with refuelling.** That is
  why a tyre change costs 21.6 s here against IMSA GTP's 8.7 s, and it is the
  variable behind this project's cross-series strategy rule.
- **It is the only class with no tyre-limited race anywhere.** All 11 measured
  circuit-seasons take exactly their fuel-minimum stop count — a consequence of
  an expensive stop rather than of endurance racing, which is the correction
  [`when_tyres_beat_fuel.md`](../cross_series/when_tyres_beat_fuel.md) records.

## Documents

Phase reports, all Hypercar-scoped:
[phase 0](data_availability_phase0.md) ·
[phase 1](data_quality_phase1.md) ·
[phase 2](degradation_phase2.md) ·
[phase 3](safety_car_phase3.md) ·
[phase 4](simulator_phase4.md) ·
[phase 7](packaging_phase7.md)

Plus [`audit_cases.md`](audit_cases.md), [`reliability.md`](reliability.md) and
the full write-up, [`methodology.md`](methodology.md).

## The complete tables

Generated from the committed CSVs, covering all 28 race-seasons:
[lap accounting](hypercar/data_quality_all_races.md) ·
[fitted slopes](hypercar/degradation_all_races.md) ·
[transfer between seasons](hypercar/transfer_all_races.md) ·
[full-race strategy](hypercar/strategy_all_races.md)
