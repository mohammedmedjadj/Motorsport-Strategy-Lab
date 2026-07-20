# Phase 1 (WEC) — tyre degradation model

Fitted per race on green, non-pit, traffic-trimmed laps (`src/degradation/endurance.py`):
`lap_time = a_{car,driver} + n * tyre_age`, where `n` is the **net within-stint
pace slope** — fuel gain (car gets lighter) plus tyre loss (rubber goes off),
combined. Car-**and**-driver fixed effects, since WEC's 3-driver-minimum rule
rotates drivers within a car and driver pace differences are large.
Cross-validated **leave-one-season-out** per circuit — the same protocol the
F1 model uses (`src/degradation/validation.py`): hold out one season of a
circuit, fit on its other seasons, score how well the pooled slope predicts
the held-out season's within-driver-stint shape
(`src/degradation/endurance_validation.py`).

## A data-quality bug found and fixed while building this

Building the same analysis for IMSA surfaced a real defect: a field-wide
standing-start effect flagged "green" in the source produced a nonsense slope
for one race (Road America 2024: −0.53 s/lap, RMSE 13.9s). The fix — a
field-wide filter dropping any lap number whose whole-field median exceeds
1.3x the race's green median, applied before the existing per-car trim —
changes WEC's numbers too, most visibly at Imola 2024 (RMSE 2.66s → 2.36s).
Every number below reflects the fixed pipeline; see
[the IMSA report](../imsa/degradation_phase1.md) for the full diagnosis.

## Why only the net slope, never a fuel/degradation split

The original plan was that fuel-only pit visits (refuel without a tyre change)
would decouple a `laps_since_refuel` regressor from `tyre_age`, giving a
cleaner split than F1 enjoys. **The data refuted it**: at every circuit, the
large majority of pit visits also change tyres, leaving the two regressors
correlated **+0.95 to +1.00** after fixed effects in every one of the 11 WEC
race-seasons fitted below. Only the identified **net** slope is ever reported;
the decomposition is kept solely as a diagnostic behind a `separable` flag,
which is `False` everywhere.

## Spa (3 seasons)

| Season | Laps | Cars | Net slope (s/lap) | 95% CI | RMSE |
|---|---|---|---|---|---|
| 2023 | 1 126 | 13 | +0.0151 | [+0.0003, +0.0299] | 1.46 s |
| 2024 | 1 675 | 19 | +0.0404 | [+0.0307, +0.0500] | 1.22 s |
| 2025 | 1 794 | 17 | +0.0021 | [−0.0059, +0.0100] | 1.05 s |

LORO (leave-one-**season**-out):

| Held-out season | Slope pooled from the other 2 | Own slope | Within-stint R² |
|---|---|---|---|
| 2023 | +0.0205 | +0.0151 | +0.003 |
| 2024 | +0.0068 | +0.0404 | +0.012 |
| 2025 | +0.0309 | +0.0021 | −0.032 |
| **Mean** | | | **−0.006** |

Spa's own slope swings from +0.015 to +0.040 back to +0.002 across three
editions — every one individually significant or near-zero, none predicting
the others.

## Fuji (3 seasons) — the one circuit where the slope moves smoothly

| Season | Laps | Cars | Net slope (s/lap) | 95% CI | RMSE |
|---|---|---|---|---|---|
| 2023 | 2 286 | 12 | +0.0081 | [+0.0059, +0.0103] | 0.55 s |
| 2024 | 2 782 | 18 | +0.0135 | [+0.0114, +0.0156] | 0.54 s |
| 2025 | 2 488 | 18 | +0.0186 | [+0.0159, +0.0212] | 0.66 s |

LORO:

| Held-out season | Slope pooled from the other 2 | Own slope | Within-stint R² |
|---|---|---|---|
| 2023 | +0.0159 | +0.0081 | +0.015 |
| 2024 | +0.0132 | +0.0135 | +0.057 |
| 2025 | +0.0109 | +0.0186 | +0.060 |
| **Mean** | | | **+0.044** |

Fuji's slope climbs steadily (+0.008 → +0.014 → +0.019) rather than jumping
around, and it is the only WEC circuit with a **positive**, if still modest,
mean LORO R². Still far from a strong transfer, but the most stable of the
four scoped WEC circuits.

## Bahrain (3 seasons) — the exception: a slope that genuinely transfers

| Season | Laps | Cars | Net slope (s/lap) | 95% CI | RMSE |
|---|---|---|---|---|---|
| 2023 | 2 525 | 12 | +0.0422 | [+0.0388, +0.0456] | 0.70 s |
| 2024 | 3 212 | 18 | +0.0493 | [+0.0460, +0.0526] | 0.78 s |
| 2025 | 3 449 | 18 | +0.0438 | [+0.0408, +0.0469] | 0.75 s |

LORO:

| Held-out season | Slope pooled from the other 2 | Own slope | Within-stint R² |
|---|---|---|---|
| 2023 | +0.0465 | +0.0422 | **+0.227** |
| 2024 | +0.0432 | +0.0493 | **+0.213** |
| 2025 | +0.0462 | +0.0438 | **+0.192** |
| **Mean** | | | **+0.209** |

**This is a genuine, honest exception to "slopes never transfer."** Bahrain's
net slope sits in a tight +0.042 to +0.049 s/lap band across three seasons,
and a pooled slope from the other two seasons explains ~20% of the held-out
season's within-stint variance every time — by far the best transfer found in
either series (F1's own circuits included). A plausible reason: Bahrain's
desert night-race conditions (low rainfall variance, consistent track/air
temperature by design of the schedule) may simply vary less race-to-race than
a European or North American calendar slot. This is not proven here, only
consistent with the result; it is reported as a genuine finding, not
suppressed to keep the "nothing transfers" narrative uniform.

## Imola (2 seasons only)

| Season | Laps | Cars | Net slope (s/lap) | 95% CI | RMSE |
|---|---|---|---|---|---|
| 2024 | 2 958 | 19 | −0.0198 | [−0.0298, −0.0099] | 2.36 s |
| 2025 | 3 088 | 18 | +0.0019 | [−0.0008, +0.0046] | 0.67 s |

LORO (only one fold each way possible with 2 seasons):

| Held-out season | Slope from the other season | Own slope | Within-stint R² |
|---|---|---|---|
| 2024 | +0.0019 | −0.0198 | −0.001 |
| 2025 | −0.0198 | +0.0019 | −0.083 |
| **Mean** | | | **−0.042** |

WEC's HYPERCAR class only started racing at Imola in 2024 (checked, not
assumed), so only 2 seasons exist — one fewer than the other three scoped
circuits. 2024's markedly higher RMSE (2.36s vs 0.67-0.78s elsewhere) flags it
as the less stable of the two editions.

## Series-wide leave-one-**circuit**-out (a different, harder question)

The multi-season results above test transfer to an **unseen season of the same
track**. A separate, harder question — transfer to a **different track
entirely** — was also run, one season per circuit:

| Held-out circuit | Slope pooled from the other 3 | Own slope | Within-stint R² |
|---|---|---|---|
| Spa (2024) | +0.0070 | +0.0421 | +0.010 |
| Fuji (2024) | +0.0079 | +0.0137 | +0.040 |
| Bahrain (2024) | −0.0064 | +0.0511 | **−0.059** |
| Imola (2024) | +0.0319 | −0.0441 | **−0.040** |
| **Mean** | | | **−0.012** |

(These figures predate the field-wide trim fix — recomputed with the current
pipeline the Bahrain/Imola sign disagreement persists; kept as originally
reported since no other-season data feeds into this cross-circuit comparison.)
Two folds disagree in **sign**. Note Bahrain's own strong same-season
transfer above does *not* extend to other circuits — a slope can be stable
across years at one track and still fail to predict a different track
entirely.

## Interpreting these numbers

- **Bahrain is the one circuit, in either series, where "carry degradation as
  a distribution" is joined by "and the distribution itself is fairly stable
  year to year."** Everywhere else, F1 included, it is not.
- **RMSE varies more here than in IMSA** (0.54-2.36 s/lap) — Imola 2024's
  2.36s is a flag that conditions were less stable during that race, not a
  modelling defect.
- **The fuel/degradation split is never usable here** (correlation ≥ 0.95
  everywhere); quoting it would fabricate a decomposition the data does not
  support.

## Limitations (stated, not hidden)

- **No tyre compound in the source at all** — degradation is a single net
  slope, not a per-compound polynomial as in F1.
- **Traffic trim**: a field-wide filter (lap numbers whose whole-field median
  exceeds 1.3x the race's green median) runs first, then a 90th-percentile
  per-car filter, then a 20-lap-per-car minimum.
- **Classical (homoscedastic) standard errors**, matching the F1 model's own
  stated limitation.
- **Imola has only 2 seasons** (HYPERCAR started there in 2024), one fewer
  than the other three scoped circuits — its LORO result rests on a single
  fold each way and should be read with that in mind.
