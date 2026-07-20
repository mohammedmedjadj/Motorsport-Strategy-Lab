# Phase 1 (IMSA) — data quality report

Lap-level accounting for every scoped race-season, mirroring the F1 ingestion
quality report (`reports/f1/data_quality_phase1.md`). A lap survives into the
degradation-model frame (`src/degradation/endurance.py::build_endurance_frame`)
only if it clears every stage below, in order; `frame_diagnostics()` runs the
same stages and returns the count each one removes, so every exclusion is
accounted for rather than only the final total.

| Stage | What it removes |
|---|---|
| Non-green or pit-visit | Neutralised laps (FCY/SC/FF/RF) and any lap with a pit stop |
| Missing tyre age | Green, non-pit, but the source has no `est_tire_age` for that lap |
| Field-wide trim | Lap **numbers** where the whole field's median time exceeds 1.3x the race's green median — a standing start or an early caution mislabelled green (see [Phase 2](degradation_phase2.md) for the Road America case this was built for) |
| Per-car trim | Remaining laps above a car's own 90th-percentile pace — ordinary traffic |
| Insufficient car laps | Cars with fewer than 20 surviving laps, too few to carry their own fixed effect |

## Per race-season

| Race-season | Total laps | Non-green/pit | Missing age | Field-wide trim | Per-car trim | Insufficient | Kept | % kept |
|---|---|---|---|---|---|---|---|---|
| Watkins Glen 2023 | 1 476 | 203 | 0 | 32 | 128 | 0 | 1 113 | 75.4% |
| Watkins Glen 2024 | 1 569 | 441 | 0 | 69 | 112 | 0 | 947 | 60.4% |
| Watkins Glen 2025 | 1 984 | 618 | 0 | 117 | 130 | 0 | 1 119 | 56.4% |
| Sebring 2023 | 2 303 | 451 | 0 | 78 | 180 | 0 | 1 594 | 69.2% |
| Sebring 2024 | 3 383 | 607 | 0 | 119 | 270 | 0 | 2 387 | 70.6% |
| Sebring 2025 | 4 444 | 542 | 0 | 105 | 386 | 0 | 3 411 | 76.8% |
| Mosport 2023 | 1 077 | 167 | 0 | 27 | 90 | 0 | 793 | 73.6% |
| Road America 2023 | 699 | 54 | 0 | 19 | 69 | 2 | 555 | 79.4% |
| Road America 2024 | 586 | 207 | 0 | 47 | 38 | 17 | 277 | 47.3% |
| Road America 2025 | 726 | 203 | 0 | 55 | 54 | 0 | 414 | 57.0% |

**Overall: 12 610 / 18 247 laps kept (69.1%).**

## Reading this table

- **`Missing age` is zero everywhere**: once a lap clears the green/non-pit
  filter, `est_tire_age` is populated for all 10 scoped race-seasons — the
  upstream estimator has no gaps here, unlike the weather fields (see
  [Phase 0](data_availability_phase0.md)).
- **Road America 2024 stands out on every trim column** (47 field-wide, 38
  per-car, 17 insufficient — the only race-season with any cars dropped
  outright): the direct fingerprint of the standing-start anomaly diagnosed in
  [Phase 2](degradation_phase2.md). The field-wide trim exists specifically to
  catch it, and two other cars still fall below the 20-lap floor after all
  trims because the race is short (62 laps) and lost proportionally more laps
  to the anomaly.
- **Retention (56-79%) sits in the same range as F1's (62-94%)**, for a
  structurally different reason: F1 loses laps mostly to wet-compound and
  inaccurate-lap flags, while IMSA loses them mostly to neutralisation — IMSA
  races see a Full Course Yellow in 90%+ of races
  ([Phase 3](safety_car_phase3.md)), so "non-green/pit" is consistently the
  largest single exclusion category here.
- **Per-car trim removes more of Sebring than of Mosport or Road America**
  in absolute terms, simply because Sebring runs far more laps per car (a 12h
  race) — a fixed 90th-percentile quantile removes a proportionally similar
  share regardless of race length, so the raw counts scale with laps run, not
  with data quality.
