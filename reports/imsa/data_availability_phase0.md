# Phase 0 (IMSA) — data availability

FastF1 covers only Formula 1, so IMSA needed a new ingestion path
(`src/data/endurance_loader.py`). Source: a community-maintained DuckDB at
`hf://datasets/tobil/imsa/imsa.duckdb`, whose `laps_with_metadata` view carries
IMSA, WEC, ELMS and ALMS together — verified by direct query, not assumed.

Same discipline as the F1 Phase 0: **verify the data before freezing any scope
or architecture.**

## Scope frozen after verification

**4 GTP races, 2023 season** (the top prototype class), chosen to contrast
sprint- and endurance-length formats and a spread of circuit types:

| Event | Laps | Cars | Drivers | Race length | Weather coverage | FCY laps | Pit visits | Tyre changes |
|---|---|---|---|---|---|---|---|---|
| Watkins Glen | 201 | 8 | 18 | 364 min | **0%** | 151 | 64 | 56 |
| Sebring | 322 | 8 | 24 | 723 min (12h) | **0%** | 394 | 116 | 99 |
| Mosport | 120 | 9 | 18 | 162 min | 100% | 143 | 29 | 29 |
| Road America | 80 | 10 | 20 | 163 min | 100% | 27 | 19 | 19 |

96 GTP-class races are available across IMSA 2021-2026 in total (used in full
for the Phase 2 neutralisation model, which needs the largest sample it can
get); these 4 were selected for degradation/simulator work to span a 2h40
sprint (Road America), two ~2h40-3h format races (Mosport, Watkins Glen) and a
12-hour enduro (Sebring).

## Two traps found by verification (both handled and regression-tested)

**1. The source mixes practice/qualifying/warmup/test with race laps** in the
same view. An unfiltered query on the #01 GTP car at Watkins Glen returned 266
laps of what is really a 201-lap race, with implausible ~1000s "pit stops" (a
car sitting in the garage during practice). `EnduranceLoader.load_laps` always
pins `session='race'`, and `normalise()` raises if anything else is present —
this is asserted, not just filtered silently.

**2. `stint_number` is the *driver* stint, not the tyre stint.** Checked on the
#01 GTP car at Watkins Glen: lap 21 is a pit stop with `est_tire_age` resetting
14 → 0 (new tyres) but `stint_number` unchanged; lap 34 is where `stint_number`
increments *and* the driver changes (Bourdais → van der Zande). Three
endurance concerns are therefore kept as separate signals in the normalised
schema (`src/data/base_loader.py::LAP_COLUMNS`): pit visits (`is_pit_lap`),
tyre changes (`is_tyre_change`), and driver stints (`driver_stint`). At
Watkins Glen the #01 car made 13 pit visits across only 4 driver stints — the
gap is fuel-only stops.

## Coverage gaps found — and corrected after seeing more races

With only Watkins Glen materialised, the first version of this report claimed
"IMSA ships no weather on the race session" as a series-wide fact. **That was
premature generalisation from n=1.** With Sebring, Mosport and Road America
added, the truth is race-specific: Watkins Glen and Sebring carry **no
weather at all** on the race session (`air_temp_f`, `track_temp_f`,
`humidity_percent`, `raining` all empty), while Mosport and Road America are
**fully populated**. The loader surfaces the gap as `NaN`, never imputed;
which races have it is now a measured fact rather than an assumption.

`pit_time` semantics are pit-*visit* duration on that lap (refuelling +
driver change + tyre change combined where applicable), not yet a clean
strategic pit-loss measurement — that is derived separately in Phase 3
(`estimate_pit_loss`), following the F1 method (in/out-lap pair vs pace
baseline), not read off `pit_time` directly.

## What this unblocks, and what it does not

Delivered: a verified source, a normalised schema shared with WEC
(`src/data/base_loader.py`), a tested loader, and four real committed races
spanning sprint to 12-hour formats.

Not built by this phase: degradation, neutralisation and simulator models —
see [degradation](degradation_phase1.md), [neutralisations](safety_car_phase2.md)
and [simulator](simulator_phase3.md).
