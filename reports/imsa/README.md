# IMSA — three classes, never pooled

The IMSA WeatherTech SportsCar Championship is modelled as **three separate
classes**. They share a loader, an estimator and a simulator; they share no
fitted number.

The split is not bookkeeping. The prototype and the GT3 classes **disagree on
this project's headline endurance conclusion**: "every measured race is
fuel-limited on stop count" holds for GTP and fails for GTD, which is
tyre-limited at a third of its circuits. Pooling them would have averaged that
away, and for a while it did.

| class | what it is | race-seasons | circuits | seasons | median slope |
|---|---|---|---|---|---|
| [**GTP**](gtp/) | manufacturer prototype, Hypercar-adjacent | 33 | 10 | 2023–2026 | +0.0166 s/lap |
| [**GTD**](gtd/) | GT3, **Pro/Am** — a bronze- or silver-rated driver is mandatory | 60 | 13 | 2021–2026 | +0.0200 s/lap |
| [**GTD PRO**](gtdpro/) | GT3, **all-professional** line-ups | 47 | 12 | 2022–2026 | +0.0190 s/lap |

**201,249 GTD laps, 102,465 GTD PRO, 82,348 GTP** — 73% kept for modelling in
each.

## Why GTD and GTD PRO are separate

They are the *same cars under the same Balance of Performance*, entered with
different crews. That makes the class boundary **exactly** the crew rating, so
the amateur-driver question is measurable without any external driver-rating
data — no other pairing in this project has that property except ELMS's two
LMP2 classes, and the two disagree.

Two results came out of keeping them apart:

- **The tyre-change premium is the car, not the crew.** Holding the GT3 car
  fixed and changing only the driver rating moves it 17.6 s → 16.9 s. Changing
  the car — GT3 to prototype — moves it 8.7 s → 17.6 s.
- **No crew effect on tyre wear survives.** Pro/Am crews fit a slope
  +0.0040 s/lap steeper over 44 matched pairs (p = 0.032), and that p-value
  does not survive any of three robustness checks. ELMS's equivalent test
  points the other way. See [`gtd/findings.md`](gtd/findings.md) and
  [`../elms/crew_rating_findings.md`](../elms/crew_rating_findings.md).

## What is series-level, and what is per class

Series-level, because it genuinely describes the championship rather than one
class:

- [`data_availability_phase0.md`](data_availability_phase0.md) — the source,
  what it carries, and the two verification traps it hides
- [`methodology.md`](methodology.md) — the full write-up
- [`packaging_phase7.md`](packaging_phase7.md) — reproduction from a fresh clone

Everything else lives under the class it describes. The phase reports were
written against GTP and now sit in [`gtp/`](gtp/) rather than at series level,
because a document titled "Phase 1 (IMSA) — data quality" that accounts for 10
of 140 race-seasons is not a series document.

## The complete tables

Each class carries four generated files covering **all** of its race-seasons —
not a sample, and not the handful an author happened to load:

| | GTP | GTD | GTD PRO |
|---|---|---|---|
| lap accounting | [33 races](gtp/data_quality_all_races.md) | [60 races](gtd/data_quality_all_races.md) | [47 races](gtdpro/data_quality_all_races.md) |
| fitted slopes | [gtp](gtp/degradation_all_races.md) | [gtd](gtd/degradation_all_races.md) | [gtdpro](gtdpro/degradation_all_races.md) |
| transfer between seasons | [gtp](gtp/transfer_all_races.md) | [gtd](gtd/transfer_all_races.md) | [gtdpro](gtdpro/transfer_all_races.md) |
| full-race strategy | [gtp](gtp/strategy_all_races.md) | [gtd](gtd/strategy_all_races.md) | [gtdpro](gtdpro/strategy_all_races.md) |

They are written by [`scripts/run_class_reports.py`](../../scripts/run_class_reports.py)
from the committed CSVs, so they cannot drift from the data.
