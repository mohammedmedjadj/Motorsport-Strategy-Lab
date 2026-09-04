# IMSA GTD — GT3, Pro/Am

GT3 machinery with a **mandatory bronze- or silver-rated driver**. The largest
class in this project: **60 race-seasons, 13 circuits, 2021–2026**, 201,249 raw
laps.

| | |
|---|---|
| median net slope | +0.0200 s/lap |
| median pit loss | **24.4 s** — the cheapest in the project |
| tyre-change premium | 17.6 s |
| tyre-limited races | **15 of 58** — a quarter |
| best season-to-season transfer | **+0.573** (Lime Rock) — the best anywhere |

## GTD broke two of this project's published conclusions

**"Every measured endurance race is fuel-limited on stop count."** That was
true of the prototype classes it was measured on and stated as a fact about
endurance racing. GTD is tyre-limited in a quarter of its races, and at Laguna
Seca it takes six stops against a fuel minimum of two. The rule that replaced
it is about the *stop cost*, not the car: no race above a 22.5 s pit loss is
tyre-limited anywhere in 205 race-seasons.

**"A degradation slope never transfers between seasons."** GTD's Lime Rock
reaches a leave-one-race-out R² of **+0.573** — more than double WEC's Bahrain,
which held the project record until the GT3 classes were scoped. Short circuits
with cheap stops are predictable in a way long ones are not.

Both corrections came from the same source: a class that looked like a
lower-priority addition and turned out to sit at the opposite end of the one
variable that matters.

## The complete tables

Generated from the committed artifacts by
[`scripts/run_class_reports.py`](../../../scripts/run_class_reports.py), so they
cannot drift from the data:

- [lap accounting, every race](data_quality_all_races.md)
- [every fitted slope with its interval](degradation_all_races.md)
- [season-to-season transfer, every fold](transfer_all_races.md)
- [full-race stop plans, every race](strategy_all_races.md)

Plus [`findings.md`](findings.md) — the class write-up, including the
crew-rating comparison against GTD PRO — and
[`../gt3_audit_cases.md`](../gt3_audit_cases.md).
