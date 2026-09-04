# External data — what does *not* come with the clone

Three layers of this project read from `data/external/`, which is **gitignored**.
Their inputs are third-party exports this repository does not redistribute, so
**those three layers cannot be regenerated from a fresh clone.** Their outputs
are committed, so everything downstream works; only the regeneration is blocked.

This file exists because the README claimed unqualified fresh-clone
reproduction in four places while three layers could not deliver it. That is the
first thing a reviewer checks.

## What is blocked

| script | reads | writes | consumed by |
|---|---|---|---|
| `scripts/run_f1_history_degradation.py` | `f1/lap_times.csv`, `f1/races.csv`, `f1/circuits.csv`, `f1/pit_stops.csv` | `data/derived/f1/history_degradation.csv`, `history_pit_loss.csv` | the breadth layer; **and the independent cross-source check in `run_slope_bias_check.py`** |
| `scripts/run_f1_reliability.py` | `f1/results.csv`, `f1/races.csv`, `f1/status.csv` | `data/derived/f1/reliability.csv` | `reports/f1/reliability.md` |
| `scripts/run_wec_reliability.py` | `wec/wec_data.csv` | `data/derived/wec/reliability.csv` | `reports/wec/reliability.md` |

The middle column is why this matters beyond tidiness: the slope-bias check
that **rejected one of the two explanations for the audit's 12-lap gap** rests
on the breadth layer, and that layer's provenance is a file a reader cannot
obtain from this repository. Anyone reproducing that result needs the source
below.

Everything else — F1 core, WEC, IMSA, ELMS, the simulator, the audits, the
cross-series work — runs offline from a clone with no external download.

## What to put here

### `data/external/f1/`

A relational Formula 1 history in the Ergast schema, as distributed on Kaggle.
The loader (`src/data/f1_history_loader.py`) expects these files by name:

```
circuits.csv  constructor_results.csv  constructor_standings.csv
constructors.csv  driver_standings.csv  drivers.csv  lap_times.csv
pit_stops.csv  qualifying.csv  races.csv  results.csv  seasons.csv
sprint_results.csv  status.csv
```

Only four are actually read: `lap_times.csv` (~17 MB, the per-lap history),
`races.csv`, `circuits.csv`, `pit_stops.csv`. The rest come with the export.

Identifying columns the code depends on: `lap_times` needs
`raceId, driverId, lap, milliseconds`; `races` needs `raceId, year, circuitId`;
`circuits` needs `circuitId, circuitRef`. `circuitRef` is the join key that
`BREADTH_CIRCUIT_ALIASES` in `src/ingestion/config.py` maps onto this project's
circuit slugs.

> **Fill in the exact dataset URL here once you have opened it and checked its
> licence.** It is deliberately blank: the schema above identifies the dataset
> unambiguously, and a link written from memory that turns out to point
> somewhere else is worse than no link. Record the licence too — whether it
> permits redistribution decides whether this whole file can be replaced by
> committing the four files that matter.

### `data/external/wec/wec_data.csv`

A results-level WEC history: 3,035 car-entries, 2011–2023, all classes. One row
per car per race with its finishing status, which is what the attrition model
consumes. Same instruction as above about the URL and the licence.

## The three ways out of this, and why none is taken yet

1. **Commit the inputs.** ~21 MB, and it depends entirely on a licence neither
   file records. Check the licence — if it permits redistribution, committing
   the four F1 files the code actually reads plus the WEC export removes this
   limitation completely, and it is the best outcome.
2. **Script the acquisition.** Kaggle's API needs credentials, so a clone still
   would not reproduce these layers *offline*, which is the property the rest of
   the project holds. It converts a blocked layer into a credentialed one.
3. **Restrict the claim** — what is done today, plus this file, plus
   `tests/test_reproducibility_claims.py`, which fails if any document promises
   unqualified fresh-clone reproduction while a script here still reads from
   `data/external/`.

Option 1 is the right end state and needs a licence check, not code.
