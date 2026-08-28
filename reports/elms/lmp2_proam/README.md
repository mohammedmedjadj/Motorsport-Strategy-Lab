# ELMS LMP2 Pro/Am — the second crew experiment

**The same Oreca 07 as LMP2**, with a bronze-rated driver mandatory.
**17 race-seasons, 8 circuits, 2023–2025.**

| | LMP2 Pro/Am | LMP2 |
|---|---|---|
| median net slope | +0.0205 s/lap | +0.0161 |
| median pit loss | 63.8 s | 61.7 s |
| tyre-change premium | 35.4 s | 25.1 s |
| tyre-limited races | 0 of 17 | 1 of 25 |
| best transfer | +0.027 | +0.035 |

## Why the comparison starts at 2023

**Before 2023 the `LMP2` label covers every entry**, not the professional
subset. Pairing the full 2021–2025 range against Pro/Am would compare a *mixed*
field against a Pro/Am one and call the difference a crew effect. The
restriction lives in code
([`src/degradation/crew_rating.py`](../../../src/degradation/crew_rating.py)),
not in a reader's memory.

## The result, and why it matters that it disagrees

Pro/Am crews here fit a slope **−0.0053 s/lap *shallower*** than the
professionals over 17 matched races (paired Wilcoxon p = 0.148). IMSA's
equivalent test finds Pro/Am **+0.0040 steeper** (p = 0.032).

Two natural experiments of the same design, disagreeing in sign, and neither
surviving its own robustness checks. **One test alone would have been written up
as a trend** — and an earlier version of this project did exactly that, in the
opposite direction, before the comparison was given code that recomputes it.

## The pit-stop difference is reported as unexplained

The tyre-change premium differs by 10.3 s between the two classes. Their
*fuel-only* stops also differ by 9.2 s, which no driver rating should change,
and the Pro/Am figure rests on 79 fuel-only stops. That pattern looks like a
difference in stop procedure or in sample rather than a crew effect, and it is
recorded as unexplained.

## The complete tables

Generated from the committed artifacts by
[`scripts/run_class_reports.py`](../../../scripts/run_class_reports.py), so they
cannot drift from the data:

- [lap accounting, every race](data_quality_all_races.md)
- [every fitted slope with its interval](degradation_all_races.md)
- [season-to-season transfer, every fold](transfer_all_races.md)
- [full-race stop plans, every race](strategy_all_races.md)
