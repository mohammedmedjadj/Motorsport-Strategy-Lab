# Phase 0 (WEC) — data availability

FastF1 covers only Formula 1, so WEC needed a new ingestion path
(`src/data/endurance_loader.py`). Source: a community-maintained DuckDB at
`hf://datasets/tobil/imsa/imsa.duckdb`, whose `laps_with_metadata` view carries
IMSA, WEC, ELMS and ALMS together — verified by direct query, not assumed. The
original plan proposed a second, separate WEC-specific API (Al Kamel Systems);
that turned out to be unnecessary once this source was found to already cover
WEC, and the unverified Al Kamel API was never adopted.

Same discipline as the F1 Phase 0: **verify the data before freezing any scope
or architecture.**

## Scope frozen after verification

**4 HYPERCAR races, 2024 season** (the top prototype class), spanning short
and long formats and three continents:

| Event | Laps | Cars | Drivers | Race length | Weather coverage | FCY laps | SC laps | Pit visits | Tyre changes |
|---|---|---|---|---|---|---|---|---|---|
| Spa | 141 | 19 | 48 | 360 min (6h) | 100% | 71 | 220 | 97 | 90 |
| Fuji | 213 | 18 | 52 | 362 min (6h) | 100% | 31 | 257 | 115 | 108 |
| Bahrain | 235 | 18 | 53 | 484 min (8h) | 100% | 33 | 110 | 138 | 136 |
| Imola | 205 | 19 | 56 | 362 min (6h) | 100% | 118 | 108 | 141 | 119 |

**Le Mans 2024 was deliberately rejected.** The source holds only 43 HYPERCAR
laps for it (a 24h race runs 300+), i.e. the event is incomplete upstream.
Picking it because it is the famous race would have poisoned every model built
on it — the same Phase 0 discipline that dropped it from the F1 project's
scope for incomplete sessions. 33 HYPERCAR-class WEC races are available across
2021-2026 in total and were used in full for the Phase 2 neutralisation model.

## The Safety Car / FCY distinction — found by verification, not assumed

WEC's race-control flags include `SF`, which does **not** appear at all in
IMSA. Checked across all 96 available races: `SF` occurs only in WEC
(2022-2026), in contiguous runs, and is adjacent to `FCY` exactly **once** in
the entire dataset. That pattern — a distinct flag, never fused with FCY —
means WEC runs a genuine Safety Car procedure separate from the Full Course
Yellow, and both are modelled ([Phase 2](safety_car_phase2.md)). At all four
scoped races the Safety Car is used *more* than the FCY (e.g. Spa: 220 SC laps
vs 71 FCY laps) — the opposite balance from IMSA, which has no Safety Car flag
at all.

## Stint bookkeeping — the same trap as IMSA, on the same schema

`stint_number` is the **driver** stint, not the tyre stint, exactly as found on
the IMSA side: tyre life lives in `est_tire_age` and resets independently of
the driver-stint counter. Both series share the normalised schema
(`src/data/base_loader.py::LAP_COLUMNS`) precisely so this distinction — pit
visit (`is_pit_lap`) vs tyre change (`is_tyre_change`) vs driver stint
(`driver_stint`) — is never collapsed for either series.

## Coverage: better than IMSA on weather, worse on nothing found so far

All four WEC races carry complete weather (`air_temp_f`, `track_temp_f`,
`humidity_percent`, `raining`) on the race session — unlike IMSA, where two of
four scoped races (Watkins Glen, Sebring) have none at all. No WEC-specific
coverage gap has been found in the scoped races; this section will be updated
plainly if one is.

## What this unblocks, and what it does not

Delivered: a verified source, the normalised schema shared with IMSA, a tested
loader, and four real committed races spanning three continents and two race
lengths.

Not built by this phase: degradation, neutralisation and simulator models —
see [degradation](degradation_phase1.md), [neutralisations](safety_car_phase2.md)
and [simulator](simulator_phase3.md).
