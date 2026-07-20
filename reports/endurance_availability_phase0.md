# Phase 0 (endurance) — data availability for IMSA / WEC

Same discipline as the F1 Phase 0: **verify the data before freezing any
scope or architecture**. Nothing below is assumed; every statement was checked
by querying the source.

## Source

`hf://datasets/tobil/imsa/imsa.duckdb` — a community-maintained DuckDB,
attached read-only via DuckDB's `httpfs`. FastF1 does not cover endurance
racing, so this replaces the entire F1 ingestion path for these series.

The original plan proposed two separate sources (a DuckDB for IMSA, the
Al Kamel timing API for WEC). **That turned out to be unnecessary**: this one
source carries WEC as well, through the same view. The unverified Al Kamel
REST API was therefore never adopted.

### The view that matters

`laps_with_metadata` joins laps, driver stints, weather and event metadata in
one place, for **IMSA, WEC, ELMS and ALMS**:

| Field group | Columns |
|---|---|
| Identity | `series_code`, `year`, `event`, `circuit_name`, `session`, `session_id` |
| Car / class | `car`, `class`, `class_normalized`, `class_category`, `team_name`, `manufacturer` |
| Driver | `driver_name`, `driver_id`, `license` |
| Timing | `lap`, `lap_time`, `lap_time_s1/s2/s3`, `pit_time` |
| Stints & tyres | `stint_number`, `stint_lap`, `est_tire_age` |
| Race control | `flags` |
| Weather | `air_temp_f`, `track_temp_f`, `humidity_percent`, `raining` |
| Event | `race_duration_minutes`, `race_distance_km`, `round_number` |

Verified class coverage: IMSA 2023 = `GTP`, `GTD`, `GTDPRO`, `LMP2`, `LMP3`;
WEC 2024 = `HYPERCAR`, `LMGT3`. Race-control tokens: `GF` (green),
`FCY` (full course yellow), `FF`, `RF` (red) — the direct analogue of F1's
`TrackStatus`.

## Two traps found by verification (both now handled in the loader)

**1. Sessions are mixed in the same view.** Filtering an event without also
filtering `session='race'` returns practice, qualifying, warmup and test laps
too. The symptom is subtle: lap numbers repeat, so the #01 GTP car appeared to
run 266 laps in a 201-lap race, with implausible ~1000 s "pit times" (a car
sitting in the garage during practice). `EnduranceLoader` always pins
`session='race'` and `normalise()` refuses a frame containing anything else.

**2. `stint_number` is the *driver* stint, not the tyre stint.** Checked on the
#01 GTP car at Watkins Glen:

- lap 21 — pit stop (`pit_time` 66.9 s), `est_tire_age` resets 14 → 0
  (new tyres), but `stint_number` does **not** change;
- lap 34 — `stint_number` 1 → 2 **and** the driver changes
  (Bourdais → van der Zande).

So three endurance concerns are separately measurable, and the normalised
schema keeps them apart:

| Concern | Signal |
|---|---|
| Pit visit (incl. fuel-only) | `pit_time > 0` |
| Tyre change | `est_tire_age` resets |
| Driver change | `stint_number` increments |

The #01 car made **13 pit visits across only 4 driver stints** — the gap is
fuel-only stops. Collapsing these into one "stint" concept, as the F1 model
does, would destroy exactly the structure endurance strategy turns on.

`est_tire_age` also appears to advance on green laps only (it stagnates through
FCY sequences), which is physically sensible for wear.

## Frozen scope (materialised, committed, offline-testable)

Two real top-class races, one per series, mirroring the F1 project's
committed-derived-data pattern (`data/derived/endurance/`):

| Series | Event | Class | Laps | Cars | Race length |
|---|---|---|---|---|---|
| IMSA | Watkins Glen 2023 | GTP | 1 476 | 8 | 364 min |
| WEC | Spa 2024 | HYPERCAR | 2 361 | 19 | 360 min |

**Le Mans 2024 was deliberately rejected**: the source holds only 43 HYPERCAR
laps for it (a 24 h race runs 300+), i.e. the event is incomplete upstream.
Picking it because it is the famous race would have poisoned the first model.

## Known coverage gaps (documented, never imputed)

- **IMSA Watkins Glen 2023 carries no weather at all** on the race session
  (`air_temp_f`, `track_temp_f`, `humidity_percent`, `raining` are empty for all
  1 476 laps), while WEC Spa 2024 is fully populated. The loader surfaces this
  as `NaN`; a regression test pins it so it cannot be silently "fixed" by
  imputation later.
- `pit_time` semantics are pit-*visit* duration on that lap; it is not a clean
  pit-loss measurement yet (the F1 project measures pit loss from in/out-lap
  pairs against a pace baseline — the endurance equivalent is future work).

## What this unblocks, and what it does not

Delivered: a verified source, a normalised multi-series lap schema
(`src/data/base_loader.py`), a tested loader (`src/data/endurance_loader.py`)
and two real committed races.

**Not yet built** (the modelling layers): endurance degradation, a fuel-load
model, driver-stint optimisation, an FCY model, and multi-class traffic. Those
are the next increments and are *not* claimed by this phase.
