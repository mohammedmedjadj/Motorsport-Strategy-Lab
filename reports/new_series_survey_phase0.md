# Survey: what else can be added at this project's standard?

A scoping document, not a results document. Anything that survives it gets its
own per-series reports at every phase, as F1, WEC and IMSA each do — nothing
here is a licence to merge series.

## The bar

The three finished series are not modelled from lap times alone. Every model
in this project needs, per lap and per car:

| requirement | used by | what fails without it |
|---|---|---|
| lap time | degradation, simulator | everything |
| tyre age / stint structure | degradation | no degradation curve at all |
| **race-control flag** (green / caution) | neutralisation model, and the green-lap filter every other model depends on | a degradation fit silently trained on caution laps |
| enough distinct circuits | leave-one-circuit-out CV | the project's main validation cannot run |
| enough seasons | leave-one-season-out CV | the transfer finding cannot be tested |

The flag column is the one that kills candidates. WEC 2021 and ELMS 2021 both
carry complete lap times and tyre ages with the `flags` column empty — races
that look healthy on every other measure and would have been fitted on a frame
that cannot tell racing from a caution.

The standing rule for this survey: **if a source cannot reach the level of the
F1, WEC and IMSA work, adding it is not worth doing.**

## GT3 — available now, and it clears the bar comfortably

First a correction of terms, because it changes the answer: **GT3 is not a
series.** It is a car category raced *inside* IMSA (GTD, GTD PRO), WEC (LMGT3),
ELMS (LMGT3) and others. So "adding GT3" means extending existing series to
their GT classes, each with its own deliverable — not creating a fourth series
that pools them.

Queried directly against the same verified DuckDB the endurance work already
uses (`session = 'race'`):

| series | class | race laps | seasons | events | cars | flags NULL | tyre age NULL |
|---|---|---|---|---|---|---|---|
| imsa | **GTD** | 201,249 | 2021-2026 | **16** | 64 | **0.0%** | **0.0%** |
| imsa | GTD PRO | 102,465 | 2022-2026 | 13 | 37 | 0.0% | 0.0% |
| wec | LMGT3 | 59,633 | 2024-2026 | 8 | 37 | 0.0% | 0.0% |
| elms | LMGT3 | 14,549 | 2024-2025 | 7 | 15 | 0.0% | 0.0% |

IMSA GTD is the strongest addition available anywhere: **more race laps than
the whole of WEC across all its classes** (201k against 207k), over 16
circuits against Hypercar's 11, six seasons, and not a single missing value in
either of the two columns that usually end a survey. It needs no new ingestion
path, no new loader and no new schema — it is the same source, the same
`laps_with_metadata` view, and the same normalised lap frame.

It is also a genuinely different modelling problem rather than more of the
same. GTD is a **Pro/Am category**: every entry must field a bronze- or
silver-rated driver, so within-race pace varies by crew in a way GTP and
Hypercar do not. That makes the amateur-driver effect measurable, which is the
same question ELMS's LMP2 Pro/Am split raises
([`reports/elms/data_availability_phase0.md`](elms/data_availability_phase0.md)).

### The "no new ingestion path" claim, tested rather than asserted

Two GTD races were pulled and put through the existing endurance pipeline
unchanged — the same `EnduranceLoader`, the same `build_endurance_frame`, the
same `fit_endurance_degradation`, no new code and no new schema:

| race | raw laps | kept | cars | car-driver units | net slope (s/lap) | 95% CI | RMSE |
|---|---|---|---|---|---|---|---|
| GTD Watkins Glen 2024 | 2,612 | 1,470 (56.3%) | 20 | 59 | +0.0229 | [+0.0045, +0.0413] | 1.06 s |
| GTD Road Atlanta 2025 | 5,273 | 4,050 (76.8%) | 15 | 43 | +0.0199 | [+0.0172, +0.0225] | 0.61 s |

It runs. Both slopes are positive with intervals excluding zero, and both sit
close to IMSA GTP's median of +0.0155 s/lap, so nothing about a GT3 field
breaks the model's assumptions.

Two details worth noting from even this small slice. **Roughly three
car-driver units per car** (59 across 20 cars) against GTP's usual two: the
Pro/Am driver-rotation requirement gives the fixed-effects structure *more*
intercepts to work with, not fewer. And Road Atlanta's residual RMSE of 0.61 s
is tighter than typical GTP fits — a BoP-equalised GT3 field is more
homogeneous in pace than a manufacturer-prototype one, which is the opposite
of what "amateur drivers make it noisier" would predict and is worth
explaining rather than assuming in phase 1.

Cluster-robust inference behaves as designed here too: G is 20 and 15 cars, so
these intervals already use a t(19) and t(14) reference rather than a normal.

**Balance of Performance — checked, and the first version of this caveat was
too strong.** GT3 is governed by BoP adjusted *during* a season, which looks
at first like F1's 2026 regulation boundary: a coefficient fitted across the
change describing neither side of it. Reading the model structure rather than
assuming, that is not the case here.

The endurance degradation model fits **one race at a time**
(`fit_endurance_degradation` takes a single race's frame), and the pooled
leave-one-race-out fit qualifies every fixed effect by the race key
(`endurance_validation.py::_fit_net_slope`), so each race-car-driver carries
its own intercept. A BoP adjustment shifts a car's pace *level*, and a
per-race intercept absorbs a level shift completely. There is no channel by
which it contaminates a slope.

What remains is real but is a finding rather than a defect: BoP changes weight
and power, which can move the tyre-wear *slope* itself. When it does, the
slope genuinely differs between races — which is exactly the quantity the
leave-one-race-out transfer analysis already measures and reports. GT3 would
then be the series where that instability has a *nameable* cause, instead of
the unexplained season-to-season variation measured everywhere else. That is
an argument for adding it, not a hazard to guard against.

## IndyCar — declined, on evidence

IndyCar was the other request. It fails the bar, and the failure is about data
availability rather than interest.

**What was checked, and what it actually contains:**

- [`TMCabrera/indycarpy`](https://github.com/TMCabrera/indycarpy) (GPL-3.0, the
  most complete open-source IndyCar scraper found) returns **session-level
  results, not lap-level data**. Its own documented columns are `BestLapTime`,
  `ElapsedTime`, `LapsComplete`, `LapsDown`, `LapsLed` — one row per car per
  session. There is no per-lap time, no flag column and no tyre field. This is
  the same shape as the results-level WEC export this project already restricts
  to reliability/attrition work precisely because it cannot feed a degradation
  or neutralisation model.
- [`DSC-SPIDAL/IndyCar`](https://github.com/DSC-SPIDAL/IndyCar) is streaming
  infrastructure — a React dashboard, TensorFlow model checkpoints, anomaly
  detection — not a dataset. It commits no lap-level race data, and it carries
  **no licence at all**, which independently rules out building on it.
- Commercial feeds ([Sportradar's IndyCar
  API](https://developer.sportradar.com/racing/reference/indycar-overview))
  do carry the depth, but their terms do not permit redistributing derived data,
  and this project commits its derived CSVs so that every result is reproducible
  offline from a clone. A source that cannot be committed breaks the property
  the whole repository is built on.

**Not ruled out forever:** IndyCar publishes per-session "Race Analysis" PDFs
that do contain lap-by-lap times, and a PDF-extraction project exists
([`JohnQuintero08/indicar_scraping_pdf`](https://github.com/JohnQuintero08/indicar_scraping_pdf)).
That route was not taken here for two reasons stated rather than assumed: PDF
layout scraping is fragile in a way a maintained database is not, and the
redistribution status of those documents is unclear. If either changes, the
decision should be revisited.

## Recommendation

1. **IMSA GTD** is the highest-value next addition and the lowest-risk: it
   clears every requirement on already-verified data, and it asks a question
   (crew-rating effects) the current three series cannot. Its own reports, and
   never pooled with GTP.
2. **ELMS LMP2** remains viable at phase 0, with the class-relabelling
   decision still open.
3. **IndyCar** is declined until a lap-level source exists that can be
   committed. Recorded with its evidence so the decision can be re-opened on a
   change in the data, not on a change of mind.

## Sources

- [TMCabrera/indycarpy](https://github.com/TMCabrera/indycarpy)
- [DSC-SPIDAL/IndyCar](https://github.com/DSC-SPIDAL/IndyCar)
- [JohnQuintero08/indicar_scraping_pdf](https://github.com/JohnQuintero08/indicar_scraping_pdf)
- [Sportradar IndyCar API](https://developer.sportradar.com/racing/reference/indycar-overview)
- Lap data queried from `hf://datasets/tobil/imsa/imsa.duckdb`, the source the
  endurance work already uses.
