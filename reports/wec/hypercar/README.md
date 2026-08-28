# WEC Hypercar — the expensive-stop end of the scale

The FIA World Endurance Championship's top class, and WEC's only modelled one.
**28 race-seasons, 11 circuits, 2022–2026.**

| | |
|---|---|
| median net slope | +0.0139 s/lap — the flattest in the project |
| median pit loss | **74.0 s** — the most expensive in the project |
| tyre-change premium | 21.6 s |
| tyre-limited races | **0 of 27** |
| best season-to-season transfer | +0.217 (Bahrain) |

## One fact seen three ways

A 74-second stop buys roughly **2,000 laps of degradation** at a typical
+0.03 s/lap slope. No tyre wears fast enough to repay that, so:

- not one of the 27 planned races is tyre-limited;
- the break-even slope — how much steeper wear would have to be to flip a race
  — runs from ×2.4 at Bahrain to ×62 at Interlagos;
- and WEC alone answers "is an extra stop ever worth it?" with **never**.

That "never" was published as a fact about endurance racing. It is a fact about
expensive stops: IMSA GTD, at a 24 s stop, is tyre-limited in a quarter of its
races. Sorting the six classes by pit loss sorts them by tyre-limited share with
no inversions, at a correlation of −0.982.

## What WEC does have that IMSA does not

**A genuine Safety Car procedure**, used in 19 of 33 races, where IMSA has
shown one in none of 63. Bahrain is also the only WEC circuit whose degradation
slope transfers between seasons at all (R² +0.217) — it held the project record
until IMSA's GT3 classes were scoped and reached +0.573.

## The complete tables

Generated from the committed artifacts by
[`scripts/run_class_reports.py`](../../../scripts/run_class_reports.py), so they
cannot drift from the data:

- [lap accounting, every race](data_quality_all_races.md)
- [every fitted slope with its interval](degradation_all_races.md)
- [season-to-season transfer, every fold](transfer_all_races.md)
- [full-race stop plans, every race](strategy_all_races.md)

Plus the series documents, all Hypercar-scoped:
[`../methodology.md`](../methodology.md) ·
[`../audit_cases.md`](../audit_cases.md) ·
[`../reliability.md`](../reliability.md).
