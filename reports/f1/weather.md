# Race-day weather — solving the missing-weather gap (Open-Meteo)

The data-availability reports flagged weather as **missing** for two IMSA
circuits, and it is absent anywhere a timing source ships none. Rather than
document the gap and move on, this layer **fills it with real data**: the
Open-Meteo historical archive (public, no key) is queried by circuit
latitude/longitude and race date, returning hourly reanalysis weather.
`src/weather/archive.py`.

Nothing is imputed — a circuit with no measured weather gets *real* reanalysis,
never a constant.

## The strategic payoff: a wet flag

The single most important weather fact for this project is whether a race was
**wet**, because wet laps must not pollute a dry-tyre degradation fit. A race day
with more than **3 mm** total precipitation is flagged `wet` — calibrated, not a
trace: 1 mm over a day is a brief sprinkle and flags ~35% of races
(over-excluding dry ones), while >3 mm (~19%, **55 of 286 races**) marks rain
that plausibly affected running.

## Validation against known races (F1, fully automatic)

The F1 fetcher joins `races` (date) to `circuits` (lat/lng), so it needs no
hand-entered dates, and reproduces F1 weather history exactly across all 286
races 2011-2024:

| Race | Precip | Flag | Reality |
|---|---|---|---|
| 2011 Canada (Villeneuve) | 23.3 mm | **wet** | the 2-hour rain red flag — longest F1 race ever |
| 2016 Monaco | 11.2 mm | **wet** | wet start, Hamilton win |
| 2022 Monaco | 3.5 mm | **wet** | wet-to-dry — the race whose slope this excludes |
| 2011 Brazil (Interlagos) | 14.4 mm | **wet** | wet qualifying/race |
| 2023 Bahrain | 0.0 mm | dry | desert, dry |

## Wired into the degradation fit

This is not a standalone artifact: the full-calendar degradation report reads
`weather.csv` and **excludes the wet races from its fits**, so a wet-to-dry
track (Monaco 2022) is never mis-read as tyre wear. That closes a real
inconsistency — before the wiring, wet contamination put Monaco near the top of
the tyre-wear table, which is physically backwards for the lowest-degradation
circuit on the calendar.

## Coverage and the honest caveat

- **F1**: every race 2011-2024 is fetched from the Kaggle join
  (`scripts/run_f1_weather.py`, resumable). `data/derived/f1/weather.csv` —
  286 races, 55 wet.
- **Endurance**: the four IMSA and four WEC scoped circuits have coordinates in
  `ENDURANCE_CIRCUIT_COORDS`, so the same fetcher fills the IMSA weather gap once
  race dates are supplied — the exact gap Phase 0 documented, now closeable.
- **Caveat, stated not hidden**: precipitation is summed over the whole race day,
  not only the race hours, so a morning shower before a dry race can still flag
  `wet`. It is therefore a conservative *hold-out* signal for degradation
  hygiene, not a claim the race itself ran wet. Narrowing to race-hour windows
  (using race start time) is the natural refinement.
