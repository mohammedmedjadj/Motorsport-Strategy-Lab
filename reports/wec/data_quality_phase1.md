# Phase 1 (WEC) — data quality report

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
| Field-wide trim | Lap **numbers** where the whole field's median time exceeds 1.3x the race's green median — a standing start or an early caution mislabelled green (found and fixed on the IMSA side, see [the IMSA report](../imsa/data_quality_phase1.md)) |
| Per-car trim | Remaining laps above a car's own 90th-percentile pace — ordinary traffic |
| Insufficient car laps | Cars with fewer than 20 surviving laps, too few to carry their own fixed effect |

## Per race-season

| Race-season | Total laps | Non-green/pit | Missing age | Field-wide trim | Per-car trim | Insufficient | Kept | % kept |
|---|---|---|---|---|---|---|---|---|
| Spa 2023 | 1 603 | 270 | 0 | 76 | 131 | 0 | 1 126 | 70.2% |
| Spa 2024 | 2 361 | 395 | 0 | 94 | 197 | 0 | 1 675 | 70.9% |
| Spa 2025 | 2 463 | 307 | 0 | 130 | 213 | 19 | 1 794 | 72.8% |
| Fuji 2023 | 2 661 | 109 | 0 | 12 | 254 | 0 | 2 286 | 85.9% |
| Fuji 2024 | 3 588 | 393 | 0 | 96 | 317 | 0 | 2 782 | 77.5% |
| Fuji 2025 | 3 408 | 500 | 0 | 136 | 284 | 0 | 2 488 | 73.0% |
| Bahrain 2023 | 2 943 | 113 | 0 | 23 | 282 | 0 | 2 525 | 85.8% |
| Bahrain 2024 | 3 953 | 285 | 0 | 90 | 366 | 0 | 3 212 | 81.3% |
| Bahrain 2025 | 4 228 | 290 | 0 | 95 | 394 | 0 | 3 449 | 81.6% |
| Imola 2024 | 3 769 | 351 | 0 | 126 | 334 | 0 | 2 958 | 78.5% |
| Imola 2025 | 3 805 | 292 | 0 | 76 | 349 | 0 | 3 088 | 81.2% |

**Overall: 27 383 / 34 782 laps kept (78.7%).**

## Reading this table

- **`Missing age` is zero everywhere**: once a lap clears the green/non-pit
  filter, `est_tire_age` is populated for all 11 scoped race-seasons.
- **Retention is consistently higher than IMSA's** (70-86% vs 47-79%) — a
  direct consequence of [Phase 3](safety_car_phase3.md)'s own finding: WEC
  races are neutralised far less often than IMSA's (FCY alone appears in only
  ~28% of WEC races against ~96% of IMSA races), so fewer laps are lost to the
  `non_green_or_pit` stage before the traffic trims even run.
- **Fuji and Bahrain 2023 both exceed 85% retention** — both have the fewest
  cars of any scoped race-season (12), and with only 8-12 cars competing for
  track position there is simply less GT-class traffic for the leading
  prototypes to encounter than in the fuller 18-19-car fields of 2024-2025.
- **Only one race-season drops any car outright**: Spa 2025 (19 laps,
  one car). Every other race-season has enough green running from every car
  to clear the 20-lap floor without exception — unlike IMSA, where Road
  America 2024 alone accounts for the vast majority of insufficient-car drops
  across both series.
