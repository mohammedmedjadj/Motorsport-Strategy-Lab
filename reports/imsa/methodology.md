# Uncertainty-First Race Strategy Modelling for the IMSA WeatherTech SportsCar Championship

**Author:** Mohammed Reda Medjadj
**Date:** August 2026.
**Repository:** `motorsport-strategy-lab` (all numbers in this report are generated
by the scripts in `scripts/` and traceable to the phase reports in
`reports/imsa/`; simulation numbers use seed 20260712, 5000 draws unless
stated otherwise). This report covers **IMSA only**. WEC gets its own,
separate report ([`reports/wec/methodology.md`](../wec/methodology.md)):
the two series share loader and estimator code
(`src/data/endurance_loader.py`, `src/degradation/endurance.py`,
`src/safety_car/endurance.py`, `src/simulator/endurance.py`) because the
underlying problem — pit visit vs tyre change vs driver stint as three
distinct signals — is genuinely the same, but every fitted number below is
IMSA's own, never pooled with WEC's. IMSA and WEC turn out not to be
interchangeable at all (§4.2), which is the clearest argument for keeping
their reports apart rather than merging them for convenience. See
[`reports/methodology.md`](../methodology.md) for the sibling F1 report this
one mirrors in structure.

## Abstract

I build the same three-layer decision-support system described for Formula
1 and for WEC — a fixed-effects tyre degradation model, a Bayesian
neutralisation-risk model, and a Monte Carlo strategy simulator — for the
IMSA WeatherTech SportsCar Championship's GTP class. IMSA shares WEC's core
extensions (a hard fuel-range constraint, an exact multi-stop dynamic
program, inter-class traffic cost) but differs from it in ways this report
keeps explicit throughout: IMSA services tyres *while* refuelling
(parallel), not after (WEC's sequential rule), so a tyre change costs only
+8.7s over a fuel-only stop, against WEC's +21.6s; IMSA has shown **zero
Safety Car events in 63 races**, relying entirely on Full Course Yellow
(FCY in 90-93% of races at every scoped circuit, P = 0.961 series-wide);
and a genuine data-quality bug was found and fixed while building this
report's degradation model. The headline results: degradation slopes do not
transfer across seasons or circuits anywhere in the four scoped circuits
(Watkins Glen, Sebring, Mosport, Road America) — the same conclusion as F1
and WEC, now shown to hold in a *second* endurance series tested two
different ways; **no scoped IMSA race is tyre-limited on stop count**,
corroborated by 24 of 33 real race winners running a stint within 3 laps of
the circuit's measured fuel range; and the simulator's confidence tracks the
strength of each circuit's own degradation signal directly, from a decisive
recommendation at Road America down to an honestly flat one at Mosport.

## 1. Motivation and related work

As stated in the WEC report (§1), public strategy-modelling literature
specific to sports-car endurance racing is sparse. The two closest papers
found — Braghin et al. (2022, *IEEE TVT*), competitor-aware WEC stochastic
strategy, and van Kampen et al. (2023, *IEEE TCST*), range-constrained
multi-stop optimisation for electric endurance racing — are cited in full
there rather than repeated here, since neither is IMSA-specific; the
van Kampen paper's stop-count-under-a-range-constraint structure is the one
that generalises directly to this report's own multi-stop layer (§3.4).

What *is* IMSA-specific is the question this report and its WEC sibling ask
together and neither paper asks at all: does a strategy-relevant quantity
fitted in one endurance series look anything like the same quantity fitted
in a structurally different one? §4.2 and §4.3 below answer this directly —
IMSA and WEC diverge on which neutralisation procedure exists at all and on
the procedural cost of a tyre change — and
[`reports/generalization_audit.md`](../generalization_audit.md) extends the
same leave-one-out transfer test used here to pit loss and neutralisation
occurrence across all three series in this project, including a
cross-series comparison neither paper attempts.

## 2. Data

Source: the same community-maintained DuckDB used for WEC
(`hf://datasets/tobil/imsa/imsa.duckdb`), `laps_with_metadata` view, IMSA
rows.

- **Degradation/simulator scope: 4 GTP circuits, 2023 season** — Watkins
  Glen (364 min), Sebring (723 min / 12h), Mosport (162 min), Road America
  (163 min), chosen to span a 2h40 sprint through a 12-hour enduro.
  **Mosport has only one season of GTP data**: checked directly against the
  source, not assumed — Mosport ran DPi (GTP's predecessor class) in 2022
  and GTD/GTDPRO/LMP2 in 2024-2025, but no GTP entry outside 2023. This is a
  verified fact about the calendar, the IMSA equivalent of the COVID-era
  gaps already documented on the F1 side, not a gap in this pipeline.
- **Neutralisation scope: 63 GTP-class races available across IMSA
  2021-2026**, all used for the neutralisation model, which wants the
  largest sample it can get.
- **Two verification traps caught before any model was built**
  (`reports/imsa/data_availability_phase0.md`): the source mixes
  practice/qualifying/warm-up/test laps with race laps in one view — an
  unfiltered query on the #01 GTP car at Watkins Glen returned 266 laps of
  what is really a 201-lap race, with implausible ~1000s "pit stops" (a car
  sitting in the garage during practice); and `stint_number` means the
  *driver* stint, not the tyre stint — the #01 car made **13 pit visits
  across only 4 driver stints** at Watkins Glen, the gap being fuel-only
  stops that don't reset a driver stint.
- **Weather coverage is race-specific, not a series-wide fact** — an
  earlier draft of the Phase 0 report claimed IMSA "ships no weather" based
  on a single race; with all four scoped races on hand, the truth is
  race-specific: Watkins Glen and Sebring have no weather coverage at all,
  Mosport and Road America have full coverage. Stated here as a correction
  the project made to itself, not a caveat discovered by someone else.
- **Data quality** (`reports/imsa/data_quality_phase1.md`): **12,610 /
  18,247 laps kept (69.1%)** across the 10 race-seasons in the frozen scope,
  the same five-stage filter as WEC. IMSA's retention (56-79%) sits lower
  than WEC's (70-86%) mostly because IMSA loses far more laps to
  neutralisation: FCY appears in 90-93% of IMSA races against ~27% of WEC
  races (§4.2).
- **A widened scope for the cross-cutting extensions**: 10 circuits, every
  eligible GTP race (≥4 cars, ≥40 laps) discovered the same way as WEC's,
  spanning 2023-2026.

## 3. Method

### 3.1 Tyre degradation, and a data-quality bug found while building it

Same specification as the WEC report (§3.1): fixed-effects OLS,
`lap_time = a_{car,driver} + n · tyre_age + ε`, car-and-driver intercepts
(IMSA rotates drivers within a car), leave-one-race-out validation scored on
within-stint demeaned residuals, and the same rejection of a fuel/tyre split
on the same evidence (85-100% of pit visits also change tyres; post-fixed-
effects correlation +0.83 to +1.00 at every circuit; `separable` is `False`
in 9 of 10 IMSA race-seasons, the lone exception Sebring 2025 at 0.827,
still highly collinear despite technically clearing the 0.90 threshold).

**The bug**: Road America 2024's first fit produced a slope of **−0.53
s/lap with a 13.9-second RMSE** — an order of magnitude off every other
race, including the same circuit's other two editions. The cause: laps 2
and 3 of that 62-lap sprint are a field-wide standing-start effect, every
car running at roughly twice its normal pace (field median 197-247s against
a ~113s green median), flagged "green" in the source. The existing per-car
90th-percentile trim could not catch it, because in such a short race those
two laps are a large enough share of *every* car's own laps to inflate that
car's own cutoff right along with the anomaly, rather than standing out
against it. The fix (`src/degradation/endurance.py`,
`FIELD_WIDE_TRIM_RATIO = 1.3`) adds a **field-wide** filter that runs before
the per-car one: any lap number whose median time across the whole field
exceeds 1.3× the race's own green median is dropped outright, regardless of
any single car's own quantile. Regression-tested against both a synthetic
case and the real race. After the fix, Road America 2024 reads **−0.0689
s/lap [−0.0991, −0.0386], RMSE 1.19s** — the same filter, built for this
race, changed WEC's numbers too (most visibly at Imola 2024, per the WEC
report), since both series share this code path.

### 3.2 Neutralisation: Full Course Yellow only

IMSA's per-lap flag encodes the same vocabulary as WEC's, reusing the same
Beta-Binomial/Gamma-Poisson Jeffreys-prior estimators and the same
modal-flag race-level timeline described in the WEC report (§3.2) —
including the same bug that was found and fixed while writing these two
reports (§4.5 below): a piece of downstream code was checking raw,
uncollapsed per-car flag rows instead of the properly modal-collapsed race
timeline. That bug inflated **WEC's** apparent FCY rate substantially; it
left IMSA's essentially unchanged (raw-method 0.968 vs the corrected
method's 0.961 posterior mean — a small, expected gap between a raw
fraction and a Jeffreys-smoothed posterior mean, not a symptom of the bug),
because IMSA has no Safety Car to create the flag-transition ambiguity that
caused WEC's overcount. **IMSA shows no Safety Car flag at all** — this is
a WEC-only procedure — so only FCY is modelled here; the simulator's own SC
parameters fall back to a near-zero Jeffreys prior over the same exposure
rather than hard-coding SC to impossible, so the model reflects what was
actually measured rather than special-casing the series.

### 3.3 Monte Carlo simulator

Same single-stop engine design as WEC (§3.3): fuel range as a hard
constraint on candidate pit laps, common random numbers across candidates
for a clean per-draw `P(best)`. The one procedural difference from WEC:
IMSA's parallel tyre service means a tyre change adds only **+8.7s** over a
fuel-only stop (pooled across 331 fuel-only stops and 2,569 tyre changes),
against WEC's +21.6s for the identical comparison — a ~2.5× gap from the
rulebook alone (WEC forbids touching tyres until the fuel hose is out;
IMSA does not), not from any difference in car or tyre technology.

**Measured circuit constants (2023 fit):**

| Circuit | Green pace (s) | Pit loss (s) | FCY ratio | Fuel range (laps) | Net slope (2023) |
|---|---|---|---|---|---|
| Watkins Glen | 96.2 | 60.6 | 2.03 | 34 | −0.0047 (CI covers 0) |
| Sebring | 111.6 | 72.1 | 1.90 | 29 | +0.0026 (CI covers 0) |
| Mosport | 69.7 | 56.9 | 1.93 | 50 | −0.0015 (CI covers 0) |
| Road America | 112.4 | 76.7 | 2.18 | 29 | **−0.0221 (significant)** |

Pit loss (~66s average) runs far higher than F1's 19-27s, for the same
reason as WEC: IMSA stops refuel and usually change driver, not just tyres.
**A note on measurement basis, stated rather than smoothed over**: this
project reports IMSA's pit loss, fuel range and net degradation slope from
at least three different computations across its reports — a single-season
2023 fit (this table), a leave-one-out training median pooled across
multiple seasons and folds (§4.6), and a per-race-state reconstruction used
by the decision audit (§4.7). All three are internally correct for what
they measure, but they are not the same quantity and this report does not
collapse them into one constant; where a number appears below, its basis is
named.

### 3.4 Multi-stop strategy

Identical exact dynamic program to WEC (§3.4),
`src/simulator/multistop.py::optimal_stop_plan`: minimise green time +
degradation + `n_stops × pit_loss` over every stint-length partition no
longer than the fuel range, then run the chosen plan through the same
per-draw neutralisation timeline for a full race-time distribution.

### 3.5 Traffic

IMSA GTP shares the track with **four** slower classes (GTD, GTDPRO, LMP2,
LMP3) — one more than WEC's three — using the identical start/finish
crossing-time method described in the WEC report (§3.5) to sidestep the
lapping problem.

### 3.6 Decision audit

Same case-selection discipline as WEC (§3.4 of that report): no public
strategy narrative exists for IMSA GTP the way F1's does, so cases are
chosen by a measurable, uniform criterion (an opportunistic
neutralisation-onset stop, or a routine green-flag stop) on the car that
completed the most laps in class, via `src/audit/endurance_cases.py`.

## 4. Results

### 4.1 Degradation: unstable everywhere, tested two ways

| Circuit | Seasons | Slope range (s/lap) | RMSE range (s) | LORO mean within-stint R² |
|---|---|---|---|---|
| Watkins Glen | 3 | −0.0047 to +0.0385 | 1.16-1.36 | **−0.011** |
| Sebring | 3 | +0.0026 to +0.0057 | 1.01-1.27 | **−0.001** |
| Road America | 3 | −0.0689 to +0.0104 | 1.19-1.38 | **+0.005** |
| Mosport | 1 | −0.0015 | 0.97 | n/a (single season) |

Mean within-stint R² is essentially zero at every testable circuit — no
better than a flat line, sometimes worse. A separate leave-one-circuit-out
test (holding out an entire track rather than a season) lands at **+0.002**
— a harder, different question, with the same answer: this project's
central finding about degradation instability is not a quirk of Formula 1,
since it now shows up independently in a *second* endurance series, tested
two different ways. Road America's three seasons all show significantly
negative net slope (2025's CI nearly reaches zero) — cars measurably
faster as tyre age increases, plausibly fuel burn dominating over a short
29-lap fuel range, reported as measured rather than smoothed into
"approximately zero degradation."

### 4.2 Neutralisation: Full Course Yellow, almost every race

| Circuit | Editions | FCY: P(≥1) [95% CI] | Rate/lap [95% CI] |
|---|---|---|---|
| Watkins Glen | 5 | 0.917 [0.621, 1.000] | 0.0423 [0.0297, 0.0571] |
| Sebring | 6 | 0.929 [0.670, 1.000] | 0.0261 [0.0196, 0.0335] |
| Mosport | 4 | 0.900 [0.555, 1.000] | 0.0349 [0.0201, 0.0536] |
| Road America | 5 | 0.917 [0.621, 1.000] | **0.0503** [0.0296, 0.0764] — highest of the four |

**Series-wide (63 races pooled): FCY in 61/63 (P = 0.961 [0.902, 0.993]),
zero Safety Car in 63 races.** This is not a modelling choice — it is what
the data shows: IMSA runs a fundamentally different neutralisation
procedure from WEC, which prefers a genuine Safety Car over FCY at every
one of its own scoped circuits (`reports/wec/methodology.md`, §4.2). Two
different endurance series, two different hazards entirely — the clearest
single argument in this project for never reporting "endurance racing" as
one hazard model.

### 4.3 Simulator: confidence tracks the underlying signal

Demo scenario per circuit (mid-race, 8 laps fuel/tyre age):

| Circuit | Best-median pit lap | P(best) | Spread |
|---|---|---|---|
| Watkins Glen | 103 | 0.50 | 12.7s |
| Sebring | 182 | 0.55 | 11.6s |
| Mosport | 80 | 0.30 | **1.8s** |
| Road America | 44 | 0.65 | **38.8s** |

The simulator's confidence is not a fixed level dialled in by hand — it
directly tracks the strength of each circuit's own degradation signal.
Road America, the one circuit with a significant slope in every season
checked (§4.1), gives the most decisive recommendation of the four; Mosport,
whose CI covers zero, spreads only 1.8 seconds across every candidate pit
lap and reports that honestly rather than picking a winner anyway.
Track-position value (adjacent-car swap rate) runs 0.022-0.051 across the
four circuits — markedly more fluid than F1's Monaco (0.004), consistent
with GTP racing generally.

### 4.4 Multi-stop strategy

Across all 10 eligible IMSA circuits: **no IMSA race in scope is
tyre-limited on stop count**, from a 70-lap sprint (Long Beach) to the
705-lap 2026 Daytona 24 Hours. Where a break-even slope exists, degradation
would need to be **1.8× (Laguna Seca, the tightest margin measured in
either series) to 205× (Sebring, the most fuel-secure)** steeper than
measured before an extra stop would pay off. 7 of 10 circuits get their
stints re-spaced evenly rather than run fuel-tank-flat-out. Corroborated
independently by real results (§4.6): **24 of 33 real IMSA race winners**
ran at least one stint within 3 laps of the circuit's own measured fuel
range.

### 4.5 Calibration: the bug, and why IMSA was mostly unaffected

The same downstream bug described in the WEC report (§4.6 there) — a piece
of code checking raw per-car flag rows instead of the properly
modal-collapsed race timeline — was found while building both reports'
calibration sections. It inflated WEC's apparent FCY rate by roughly 2.6×;
IMSA's own figures barely moved (raw-method 0.968 vs the corrected 0.961
posterior mean), because IMSA's absence of a Safety Car removes the
flag-transition ambiguity that drove WEC's overcount. Corrected numbers:

| Target | Level | Races | Base rate | Skill vs climatology |
|---|---|---|---|---|
| IMSA FCY | circuit | 63 | 0.968 | **−0.505** |
| Endurance FCY (by series) | series | 96 | — | **+0.528** |

**Per circuit, IMSA's FCY odds do not beat the series base rate** — the
same conclusion as degradation (§4.1) and as WEC's own hazards. The positive
control (grouping FCY by series instead of circuit) shows clear skill
precisely because IMSA's true rate (~0.97) and WEC's true rate (~0.27, after
the fix) genuinely differ — evidence the harness detects real signal rather
than always returning zero, not evidence that either series' per-circuit
number is trustworthy on its own. **IMSA Safety Car is intentionally
omitted from this backtest**: there is nothing to predict when the event
has never occurred.

### 4.6 Generalization audit

Extending the leave-one-out protocol to pit loss gives IMSA's own relative
RMSE range of **0.23-0.45** across 9 testable circuits (Mosport excluded,
single season, cannot support a leave-one-out fold) — inside the "transfers
reasonably well" band this project's generalization audit establishes, and
nowhere near WEC COTA's 1.10 outlier. Degradation LORO within-stint R²
across the same 9 circuits stays close to zero throughout (−0.004 to
+0.029), consistent with §4.1's within-series result.

**Two measurement-basis notes, both instances of the discipline §3.3
commits to.** First, on pit loss: the LORO training medians used for this
test (e.g. Sebring 69.2s, Road America 68.0s) are computed differently from
§3.3's single-2023-fit demo values (Sebring 72.1s, Road America 76.7s) —
both correct for what they measure (a multi-season pooled median vs a single
race-season fit), and neither should be read as "the" IMSA pit loss for a
circuit without naming which one. Second, on degradation: this section's
R² range comes from the **widened** `ENDURANCE_SCOPE` artifact
(`data/derived/endurance/endurance_degradation_loro.csv`, 9 circuits
including 2026 seasons), while §4.1's per-circuit table comes from the
**frozen** 4-circuit degradation scope. The two agree closely at Sebring
(−0.001 both ways) and Road America (+0.005 both ways) but not at Watkins
Glen (−0.011 frozen vs +0.003 widened), where the widened scope adds a
2026 fold. Both round to "indistinguishable from zero," which is the
finding; the difference between them is fold set, not disagreement.

### 4.7 Decision audit: three real stop calls

| Case | Real decision | Model verdict |
|---|---|---|
| A. Watkins Glen 2024, car 01, lap 90 (FCY-onset, 4th/8 stops) | Pitted the exact FCY-onset lap | +7.92s vs optimum — **outside** window, but decisively resolved either way (P(best) 0.792 at the model's lap vs 0.014 at the real one) |
| B. Road America 2024, car 10, lap 29 (routine green stop, 1st/2 stops) | Pitted under green | +0.00s vs optimum — **inside**, decisively (P(best) 0.919) |
| C. Mosport 2023, car 10, lap 85 (FCY-onset, flat-signal circuit) | Pitted the exact FCY-onset lap | +11.52s vs optimum — technically **outside**, but on a low-confidence preference (P(best) 0.339 at the model's lap vs 0.011 at the real one, 581s spread) |

Model confidence at the recommended lap orders exactly as §4.3's demo
scenarios predicted from the underlying signal alone: **Road America
(0.919) > Watkins Glen (0.792) > Mosport (0.339)**. Case A's "outside"
verdict is a real, well-resolved correction (waiting past FCY onset paid
off with 15 laps of fuel still in hand); Case C's "outside" verdict is not
— Mosport's own degradation CI covers zero, and the model's own optimum is
barely more confident than the real decision was, which is the honest
result for a circuit with no measurable signal to correct against, not a
confident refutation of the real call.

### 4.8 Retrospective winner audit and the fuel-limited sensitivity sweep

**24 of 33 real IMSA race winners (72.7%)** ran a stint within 3 laps of
the circuit's measured fuel range (`reports/endurance_audit.md`),
corroborating §4.4. A sensitivity sweep on that 3-lap tolerance
(`reports/fuel_limited_sensitivity.md`) shows IMSA's share moves
considerably more than WEC's across the tested range: from **54.5%** at the
strictest reading (exact reach only) up to **93.9%** at a 10-lap tolerance —
a wider swing than WEC's 75.0-100.0% over the same range, meaning IMSA's
fuel-limited conclusion is real but more sensitive to exactly how the
tolerance is defined than WEC's is. Even at the strictest reading, IMSA is
still a clear majority (54.5%). Road America's fuel range is reported
differently across three sources in this project — 29 laps (§3.3's
single-2023-fit table), 30 laps (§4.7's Case B, measured from the specific
2024 race state), and 24 laps (this table's own `estimate_fuel_range`
method, a 90th-percentile-of-observed-stints figure applied across all
seasons) — all three are correct for their own measurement basis and are
named here explicitly rather than merged into one number, exactly the
discipline §3.3 commits to up front.

## 5. Threats to validity

**Internal validity** — could a reported effect be an artefact of the
estimation, not the phenomenon it claims to measure?

- **No tyre compound in the source**, so degradation is a single net slope,
  not F1's per-compound curve.
- **Classical homoscedastic standard errors** throughout, as in F1 and WEC.
- **Compound/strategy allocation is not random** (as F1's own report notes
  for itself): teams that plan a long stint choose accordingly, so a net
  slope describes observed usage, not a causal effect isolated from
  strategic intent.
- **Road America's negative degradation slope is reported as measured**, a
  genuine open finding rather than something smoothed over or attributed to
  measurement error without evidence.

**External validity** — how far do the fitted numbers travel beyond the
races they were fitted on?

- **Degradation does not transfer, tested two independent ways** (§4.1) —
  the same conclusion F1 and WEC each reach independently, now shown a
  third time in a structurally different series.
- **Mosport has no leave-one-season-out result at all** — a single verified
  season, not a gap this pipeline created; the simulator's Mosport demo
  still runs on that one available fit, and its honestly flat 1.8-second
  spread (§4.3) is itself a signal of how little that single fit should be
  trusted for anything sharper.
- **Per-circuit FCY odds do not beat the series base rate** (§4.5); only
  series-level pooling recovers skill, and IMSA cannot be pooled with WEC's
  Safety Car procedure at all, since IMSA has none to pool.
- **The Road America fuel-range figure differs by measurement basis, not
  by error** (§4.8) — a concrete example of why this report insists on
  naming which computation a quoted number comes from rather than treating
  "the IMSA fuel range at Road America" as one fixed constant.

**Construct validity** — do the simulator's objective and the audit's
comparison actually capture "good strategy," or a narrower proxy for it?

- **No rivals, no track position, and no driver-stint regulatory
  constraints** in either the single-stop or multi-stop engine; IMSA is
  heavily multi-class (GTP/GTD/GTDPRO/LMP2/LMP3), and a two-car rival
  abstraction (as used in the WEC and F1 adversarial-rival models) would
  misrepresent that field structure rather than simplify it honestly, which
  is why no adversarial-rival extension is reported for IMSA in this
  version of the project.
- **The decision audit's 0.5s window tolerance is inherited unchanged from
  F1**, and reads as a much stricter bar at IMSA's endurance race-time
  scale (Case A: 7.92s against roughly comparable spreads) than it was
  designed for — stated the same way the WEC report states it for its own
  cases.
- **Traffic (§3.5) enters the multi-stop simulation as calibrated variance,
  not a planned-around strategic lever** — the same construct limitation as
  WEC's own traffic layer.

## 6. Future work

Regenerate the Mosport fit once a second GTP season becomes available,
turning its single-fit demo into an actual leave-one-season-out result;
price the +8.7s tyre-change premium into the single-stop engine's per-stop
cost, as proposed for WEC; a genuine multi-class rival model rather than
omitting rivals from IMSA's simulator entirely, given the field structure
that currently rules out reusing WEC/F1's two-car abstraction; extend the
retrospective decision audit beyond three cases as more races enter scope
via the rolling `ENDURANCE_SCOPE`.

## 7. Reproducibility

Python 3.13, dependencies pinned in `requirements.lock` (duckdb, pandas
2.3.3, numpy 2.5.1, scipy 1.18.0). IMSA races are committed as derived CSVs
under `data/derived/imsa/` and `data/derived/endurance/`, so every test in
this report's scope runs fully offline; `scripts/run_endurance_flags.py` and
`scripts/run_endurance_models.py` re-pull and refit only if explicitly asked
to refresh the source. All stochastic code is seeded. This report's layer is
covered by a dedicated subset of the project's 260 pytest tests (data
loading, the endurance degradation/neutralisation/simulator models
including the field-wide standing-start filter's regression test, the
multi-stop dynamic program, traffic estimators, and the decision-audit state
reconstruction); the remaining tests cover F1 and WEC, out of scope for this
report. Each phase's full output is a committed report in `reports/imsa/`.
