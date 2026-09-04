# IMSA GTD PRO — GT3, all-professional

**The same cars as GTD, under the same Balance of Performance**, entered with
all-professional line-ups instead of a mandatory amateur-rated driver.
**47 race-seasons, 12 circuits, 2022–2026.**

| | GTD PRO | GTD (Pro/Am) |
|---|---|---|
| median net slope | +0.0190 s/lap | +0.0200 |
| median pit loss | 39.6 s | 24.4 s |
| tyre-change premium | **16.9 s** | **17.6 s** |
| tyre-limited races | 7 of 46 | 15 of 58 |
| best transfer | +0.497 (Lime Rock) | +0.573 (Lime Rock) |

## Why this class exists as a separate scope

**The class boundary *is* the crew rating.** Same car, same regulations, same
weekends, same circuits — the only difference is whether an amateur-rated
driver is mandatory. That makes two questions measurable without any external
driver-rating data, and no other pairing in this project has that property
except ELMS's two LMP2 classes.

**The tyre-change premium is the car, not the crew.** 16.9 s here against GTD's
17.6 s — holding the car fixed and changing only the driver rating moves it
0.7 s. Changing the car moves it nine seconds, to GTP's 8.7 s.

**No crew effect on tyre wear survives.** Pro/Am crews fit a slope +0.0040 s/lap
steeper over 44 matched races, at a paired Wilcoxon p = 0.032. That p-value
does not survive a sign test (0.096), dropping the in-progress season (0.094),
or dropping races hit by the known track-evolution defect (0.054). ELMS's
equivalent test points the *other* way. Two natural experiments, neither robust,
disagreeing in sign — which is why this project reports no crew effect rather
than the one significant-looking result.

Full argument: [`../gtd/findings.md`](../gtd/findings.md) and
[`../../elms/crew_rating_findings.md`](../../elms/crew_rating_findings.md).

## The audits

**215 replayed first-stop decisions** across this class's races, on the same
uniform criterion used for every series
([`../systematic_audit.md`](../systematic_audit.md)). The model runs to the
fuel deadline in 69% of them and sits +13 laps from the real stop — the
signature of a championship that neutralises constantly, not of this class in
particular.

Its per-decision case study is **Laguna Seca 2026**, filed with GTD's because
the two classes share a car and the comparison between them is the point:
[`../gt3_audit_cases.md`](../gt3_audit_cases.md) case G-B. The question it asks
is whether the recommended window differs at all between the same car with a
professional crew and with an amateur one.

## The complete tables

Generated from the committed artifacts by
[`scripts/run_class_reports.py`](../../../scripts/run_class_reports.py), so they
cannot drift from the data:

- [lap accounting, every race](data_quality_all_races.md)
- [every fitted slope with its interval](degradation_all_races.md)
- [season-to-season transfer, every fold](transfer_all_races.md)
- [full-race stop plans, every race](strategy_all_races.md)
