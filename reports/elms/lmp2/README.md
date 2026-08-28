# ELMS LMP2 — the near-spec control

An **Oreca 07 chassis with a Gibson GK428 engine** for essentially the whole
field: no manufacturer variety, no Balance of Performance.
**25 race-seasons, 9 circuits, 2021–2025.**

| | |
|---|---|
| median net slope | +0.0161 s/lap |
| median pit loss | 61.7 s |
| tyre-change premium | 25.1 s |
| tyre-limited races | 1 of 25 (Mugello 2024, on a 9.2 s stop) |
| best season-to-season transfer | +0.035 (Barcelona) |

## This class exists to falsify a hypothesis, and it did

Degradation slopes fitted on one season fail to predict another, everywhere
this project has looked. The comfortable explanation was the **machinery**: F1
cars differ by design, and Hypercar and GTP are manufacturer prototypes
equalised by a Balance of Performance adjusted between events. A slope might
legitimately not transfer because it is not the same car.

That explanation is testable, and LMP2 is the test. The prediction was recorded
in [`../data_availability_phase0.md`](../data_availability_phase0.md) **before
the fit was run**, and it pointed the inconvenient way: a transfer result here
would have undermined three phases of prior work.

**Slopes still fail.** Leave-one-race-out R² is at or below zero at every
circuit, reaching −0.067 at Portimao. A slope fitted on a circuit's other
seasons explains none of the held-out season's within-stint variance, on a field
where the chassis and engine are identical for everyone.

**The instability is not the car.** That is a negative result, and it is the
most useful thing this series contributed.

## The complete tables

Generated from the committed artifacts by
[`scripts/run_class_reports.py`](../../../scripts/run_class_reports.py), so they
cannot drift from the data:

- [lap accounting, every race](data_quality_all_races.md)
- [every fitted slope with its interval](degradation_all_races.md)
- [season-to-season transfer, every fold](transfer_all_races.md)
- [full-race stop plans, every race](strategy_all_races.md)

Plus the series documents, which report both LMP2 classes side by side:
[`../methodology.md`](../methodology.md) · [`../results.md`](../results.md) ·
[`../crew_rating_findings.md`](../crew_rating_findings.md).
