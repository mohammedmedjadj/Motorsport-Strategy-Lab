# Phase 1 (IMSA) — tyre degradation model

Fitted per race on green, non-pit, traffic-trimmed laps (`src/degradation/endurance.py`):
`lap_time = a_{car,driver} + n * tyre_age`, where `n` is the **net within-stint
pace slope** — fuel gain (car gets lighter) plus tyre loss (rubber goes off),
combined. Car-**and**-driver fixed effects, since IMSA rotates drivers within a
car and driver pace differences are large. Cross-validated leave-one-race-out
across the 4 scoped circuits, exactly as the F1 model is
(`src/degradation/endurance_validation.py`).

## Why only the net slope, never a fuel/degradation split

The original plan was that fuel-only pit visits (refuel without a tyre change)
would decouple a `laps_since_refuel` regressor from `tyre_age`, giving a
cleaner split than F1 enjoys. **The data refuted it**: across all four
circuits, the large majority of pit visits also change tyres —

| Circuit | Pit visits | Also changed tyres |
|---|---|---|
| Watkins Glen | 64 | 56 (88%) |
| Sebring | 116 | 99 (85%) |
| Mosport | 29 | 29 (**100%**) |
| Road America | 19 | 19 (**100%**) |

— leaving the two regressors correlated **+0.98 to +1.00** after fixed effects
at every circuit (table below). Fitting both yields a collinear ridge, not a
measurement, so only the identified **net** slope is reported; the
decomposition is kept solely as a diagnostic behind a `separable` flag
(`EnduranceFit.separable`), which is `False` everywhere in this dataset.

## Per-circuit results

| Circuit | Laps | Cars | Net slope (s/lap) | 95% CI | Significant? | RMSE | Fuel/deg corr |
|---|---|---|---|---|---|---|---|
| Watkins Glen | 1 143 | 8 | −0.0074 | [−0.0178, +0.0030] | covers 0 | 1.35 s | +0.99 |
| Sebring | 1 664 | 8 | +0.0040 | [−0.0060, +0.0140] | covers 0 | 1.41 s | +0.98 |
| Mosport | 817 | 9 | −0.0038 | [−0.0106, +0.0030] | covers 0 | 1.04 s | +0.99 |
| Road America | 572 | 9 | **−0.0358** | [−0.0555, −0.0162] | **significantly negative** | 1.57 s | +1.00 |

Three of four circuits show a net slope statistically indistinguishable from
zero — the fuel-burn gain and tyre-wear loss roughly cancel over a stint. Road
America is the exception: a **significantly negative** net slope, i.e. cars get
measurably *faster* as tyre age increases within a stint. Read literally as
"negative degradation" this is physically backwards; the honest reading is
that the net-slope model is absorbing something else at that circuit — most
likely fuel burn dominating over a short (29-lap fuel range) stint, or track
evolution (rubber laid down as the race progresses) correlated with tyre age
within a stint. It is reported as measured, not smoothed away.

## Leave-one-race-out: slopes do not transfer across circuits

| Held-out circuit | Slope pooled from the other 3 | This circuit's own slope | Within-stint R² |
|---|---|---|---|
| Watkins Glen | −0.0048 | −0.0074 | +0.002 |
| Sebring | −0.0095 | +0.0040 | +0.000 |
| Mosport | −0.0064 | −0.0038 | +0.002 |
| Road America | −0.0023 | −0.0358 | +0.003 |
| **Mean** | | | **+0.002** |

A pooled slope fitted on three circuits predicts a fourth's within-stint pace
evolution **no better than a flat line** (mean R² ≈ 0). This is the F1
project's central finding — degradation coefficients do not transfer, so they
must be carried as distributions, never point values — reproduced
independently in IMSA. It could not have been checked with one race; four
circuits earn this result.

## Interpreting these numbers

- **Net slopes near zero are not "no degradation"** — they mean fuel gain and
  tyre loss cancel over a stint at that circuit and fuel-stint length. The
  simulator ([Phase 3](simulator_phase3.md)) reflects this: at a circuit like
  Watkins Glen, no candidate pit lap is meaningfully better than another.
- **RMSE (1.0-1.6 s/lap)** is the lap-level noise scale Phase 3 uses for its
  stochastic noise term, mirroring the F1 model's convention.
- **The fuel/degradation split is never usable here** (correlation ≥ 0.98
  everywhere); quoting it would fabricate a decomposition the data does not
  support.

## Limitations (stated, not hidden)

- **Single-season fit** (2023). Cross-season stability, which the F1 project
  found to be poor, has not yet been tested for IMSA because only one season
  is materialised per circuit; the LORO result above is cross-*circuit*, not
  cross-season.
- **No tyre compound in the source at all** — degradation is a single net
  slope, not a per-compound polynomial as in F1.
- **Traffic trim (90th percentile per car) and a 20-lap minimum** are applied
  exactly as documented in `src/degradation/endurance.py`; multi-class traffic
  is the dominant non-tyre noise source in this data.
- **Classical (homoscedastic) standard errors**, matching the F1 model's own
  stated limitation.
- Road America's negative slope is reported, not explained away — a genuine
  open question for future work (see [simulator](simulator_phase3.md) for how
  the model handles it operationally).
