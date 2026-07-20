# Phase 1 (WEC) — tyre degradation model

Fitted per race on green, non-pit, traffic-trimmed laps (`src/degradation/endurance.py`):
`lap_time = a_{car,driver} + n * tyre_age`, where `n` is the **net within-stint
pace slope** — fuel gain (car gets lighter) plus tyre loss (rubber goes off),
combined. Car-**and**-driver fixed effects, since WEC's 3-driver-minimum rule
rotates drivers within a car and driver pace differences are large.
Cross-validated leave-one-race-out across the 4 scoped circuits
(`src/degradation/endurance_validation.py`), the same protocol as F1 and IMSA.

## Why only the net slope, never a fuel/degradation split

The original plan was that fuel-only pit visits (refuel without a tyre change)
would decouple a `laps_since_refuel` regressor from `tyre_age`, giving a
cleaner split than F1 enjoys. **The data refuted it**: at every scoped
circuit, the large majority of pit visits also change tyres —

| Circuit | Pit visits | Also changed tyres |
|---|---|---|
| Spa | 97 | 90 (93%) |
| Fuji | 115 | 108 (94%) |
| Bahrain | 138 | 136 (99%) |
| Imola | 141 | 119 (84%) |

— leaving the two regressors correlated **+0.95 to +1.00** after fixed effects
at every circuit (table below). Fitting both yields a collinear ridge, not a
measurement, so only the identified **net** slope is reported; the
decomposition is kept solely as a diagnostic behind a `separable` flag
(`EnduranceFit.separable`), which is `False` everywhere in this dataset.

## Per-circuit results

| Circuit | Laps | Cars | Net slope (s/lap) | 95% CI | Significant? | RMSE | Fuel/deg corr |
|---|---|---|---|---|---|---|---|
| Spa | 1 764 | 19 | **+0.0421** | [+0.0312, +0.0530] | **significantly positive** | 1.42 s | +0.95 |
| Fuji | 2 872 | 18 | **+0.0137** | [+0.0115, +0.0160] | **significantly positive** | 0.59 s | +0.99 |
| Bahrain | 3 296 | 18 | **+0.0511** | [+0.0477, +0.0544] | **significantly positive** | 0.81 s | +0.99 |
| Imola | 3 068 | 19 | **−0.0441** | [−0.0550, −0.0332] | **significantly negative** | 2.66 s | +1.00 |

Three of four circuits show a clearly **positive** net slope — real,
measurable within-stint pace loss, unlike most of IMSA's four circuits, where
the net effect is statistically zero. Imola is the exception, with a
significantly *negative* slope and a visibly higher RMSE (2.66 s vs 0.6-1.4 s
elsewhere) — a signature of changing conditions during the race (track
evolution or a temperature swing) rather than a physically backwards tyre
effect. Reported as measured, flagged as an outlier, not smoothed away.

## Leave-one-race-out: slopes do not transfer across circuits, and can flip sign

| Held-out circuit | Slope pooled from the other 3 | This circuit's own slope | Within-stint R² |
|---|---|---|---|
| Spa | +0.0070 | +0.0421 | +0.010 |
| Fuji | +0.0079 | +0.0137 | +0.040 |
| Bahrain | −0.0064 | +0.0511 | **−0.059** |
| Imola | +0.0319 | −0.0441 | **−0.040** |
| **Mean** | | | **−0.012** |

The mean R² is **negative** — a pooled slope from three circuits predicts a
fourth's within-stint pace evolution *worse* than a flat line. Two folds
(Bahrain, Imola) show the pooled and own slopes disagreeing in **sign**. This
is the F1 project's central finding — degradation coefficients do not
transfer, so they must be carried as distributions, never point values —
reproduced independently in WEC, and here even more starkly than in IMSA (mean
R² −0.012 vs +0.002).

## Interpreting these numbers

- **Spa, Fuji and Bahrain give real, usable positive slopes** for a
  single-race strategy call at that specific event ([Phase 3](simulator_phase3.md)
  uses them to give decisive recommendations). What they must not be used for
  is predicting a *different* circuit or a *different* running of the same
  circuit — the LORO result above is the proof.
- **RMSE varies more here than in IMSA** (0.59-2.66 s/lap) — Imola's 2.66 s is
  a flag that conditions were less stable during that race, not a modelling
  defect.
- **The fuel/degradation split is never usable here** (correlation ≥ 0.95
  everywhere); quoting it would fabricate a decomposition the data does not
  support.

## Limitations (stated, not hidden)

- **Single-season fit** (2024). Cross-season stability has not yet been tested
  for WEC; the LORO result above is cross-*circuit*, not cross-season.
- **No tyre compound in the source at all** — degradation is a single net
  slope, not a per-compound polynomial as in F1.
- **Traffic trim (90th percentile per car) and a 20-lap minimum** are applied
  exactly as documented in `src/degradation/endurance.py`; WEC is heavily
  multi-class (HYPERCAR racing among LMGT3 traffic), so this trim matters.
- **Classical (homoscedastic) standard errors**, matching the F1 model's own
  stated limitation.
- Imola's negative slope and elevated RMSE are reported, not explained away —
  a genuine open question for future work.
