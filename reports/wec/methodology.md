# Uncertainty-First Race Strategy Modelling for the FIA World Endurance Championship

**Author:** Mohammed Reda Medjadj
**Date:** August 2026.
**Repository:** `motorsport-strategy-lab` (all numbers in this report are generated
by the scripts in `scripts/` and traceable to the phase reports in
`reports/wec/`; simulation numbers use seed 20260712, 5000 draws unless
stated otherwise). This report covers **WEC only**. IMSA gets its own,
separate report ([`reports/imsa/methodology.md`](../imsa/methodology.md)):
the two series share loader and estimator code
(`src/data/endurance_loader.py`, `src/degradation/endurance.py`,
`src/safety_car/endurance.py`, `src/simulator/endurance.py`) because the
underlying problem — pit visit vs tyre change vs driver stint as three
distinct signals — is genuinely the same, but every fitted number below is
WEC's own, never pooled with IMSA's. See [`reports/methodology.md`](../methodology.md)
for the sibling F1 report this one mirrors in structure.

## Abstract

I build the same three-layer decision-support system described for Formula 1
— a fixed-effects tyre degradation model, a Bayesian neutralisation-risk
model, and a Monte Carlo strategy simulator — for the FIA World Endurance
Championship's HYPERCAR class, on a source FastF1 does not cover (a
community-maintained lap-and-flag dataset spanning IMSA, WEC, ELMS and ALMS).
WEC needed three real extensions beyond the F1 design: a **hard fuel-range
constraint** on candidate pit laps rather than a preference, **two
neutralisation kinds** (Full Course Yellow and a genuine Safety Car
procedure, sampled independently), and an **exact multi-stop dynamic
program**, since a 6-24 hour race needs 2-29 stops, not one. The headline
results: degradation slopes are unstable across seasons everywhere except
**Bahrain**, whose pooled slope explains a fifth of a held-out season's
within-stint variance (mean R² +0.209) — the strongest transfer found
anywhere in this project, F1 included; WEC runs a genuine **Safety Car**
procedure and prefers it over FCY at every one of its four scoped circuits
(Spa alone: SC in 5 of 6 editions vs FCY in 3 of 6); and **no scoped WEC race
is tyre-limited on stop count** — every one is fuel-limited, corroborated by
25 of 28 real race winners running a stint within 3 laps of the circuit's
measured fuel range. A leave-one-out calibration backtest shows per-circuit
neutralisation odds do not beat the series base rate, but a positive control
(FCY grouped by series rather than circuit) does — WEC's own series-wide FCY
rate (~0.27) is genuinely different from IMSA's (~0.97), proof the harness
detects real signal rather than always returning zero.

## 1. Motivation and related work

Public strategy-modelling work on endurance racing is far sparser than on
Formula 1, and what exists skews toward electric or hybrid powertrains
rather than the fuel-range and tyre-service trade-offs a HYPERCAR faces.
Two papers are the closest comparisons:

Braghin, Paparusso, Riani & Ruggeri (2022, *IEEE Transactions on Vehicular
Technology*, DOI 10.1109/TVT.2022.3215171) build a competitor-aware energy
strategy for WEC hybrid vehicles, combining statistical competitor modelling,
Monte Carlo simulation of realistic on-track positions, and stochastic
dynamic programming, validated on a real WEC stint. It is the one paper found
that fits real WEC race data at all. The traffic layer here
(`src/simulator/traffic.py`, §3.5) targets a version of the same problem —
what a slower car ahead costs a HYPERCAR — but from measured crossing-time
data across every scoped season rather than a competitor-behaviour model,
and feeds the cost into the Monte Carlo simulator as calibrated variance
rather than optimising around it directly.

van Kampen, Herrmann, Hofman & Salazar (2023, *IEEE Transactions on Control
Systems Technology*, arXiv:2301.08060) solve a bi-level optimisation for a
fully electric endurance car: an inner loop finds the minimum lap time for a
given stint length and charge duration, an outer loop chooses the number of
stops. The stop-count-under-a-range-constraint structure is the same problem
this project's multi-stop layer solves (§3.4) for a fuel tank instead of a
battery, though this project's `optimal_stop_plan` is an exact dynamic
program over a small discrete grid of stint lengths rather than a
mixed-integer conic program — a WEC race's fuel range (13-46 laps depending
on circuit) makes the discrete search tractable without the continuous
relaxation their electric-vehicle problem needs.

Neither paper tests whether a fitted quantity transfers across seasons, and
neither confronts its output against real strategist decisions. Both gaps
are addressed here (§3.4's decision audit; the leave-one-season-out and
leave-one-circuit-out protocols throughout §4), and a third, broader
question — does *any* fitted quantity in this project generalise, not just
degradation, and does the answer differ by series — is reported separately
in [`reports/generalization_audit.md`](../generalization_audit.md), which
runs the identical leave-one-out protocol on pit loss and neutralisation
occurrence across all three series in this project. The F1 report
([`reports/methodology.md`](../methodology.md), §1) covers F1-specific
related work (Aguad & Thraves' Stackelberg pit-stop game; three
learned-model pit-strategy systems; Pitwall) that is not re-litigated here
since none of those five is endurance-specific.

## 2. Data

Source: a community-maintained DuckDB (`hf://datasets/tobil/imsa/imsa.duckdb`,
maintained by "tobil" on Hugging Face), covering IMSA, WEC, ELMS and ALMS
together — verified directly by query before a separately-planned WEC API
was judged unnecessary (`reports/wec/data_availability_phase0.md`).

- **Degradation/simulator scope: 4 HYPERCAR circuits, 2-3 seasons each
  (2023-2025)** — Spa, Fuji, Bahrain (6h, 6h, 8h formats), plus Imola
  (6h, 2024-2025 only: HYPERCAR started racing there in 2024, checked
  directly rather than assumed). **Le Mans 2024 was deliberately excluded**:
  the source holds only 43 HYPERCAR laps for what should be a 300+ lap race,
  an incomplete upstream extraction that would have poisoned every model
  built on it.
- **Neutralisation scope: all 33 available HYPERCAR-class WEC races
  (2021-2026)**, which wants as large a sample as it can get. 2021 is
  excluded from every other layer (100% NaN flags that season, an upstream
  collection gap, not a modelling choice).
- **Two verification traps caught before any model was built**
  (`data_availability_phase0.md`): the raw source mixes practice/qualifying/
  warm-up laps in with race laps (guarded by an assertion, not a silent
  filter); and `stint_number` in the source means the *driver* stint, not
  the tyre stint — tyre age (`est_tire_age`) resets independently and is
  tracked as a separate signal.
- **Data quality** (`data_quality_phase1.md`): **27,383 / 34,782 laps kept
  (78.7%)** across the 11 race-seasons in the frozen scope, after a
  five-stage filter (non-green/pit → missing tyre age → field-wide trim →
  per-car trim → insufficient-laps drop). WEC's retention is consistently
  higher than IMSA's (70-86% vs 47-79%), because WEC sees far fewer
  neutralised laps: FCY+SC together affect a smaller share of green running
  than IMSA's FCY-heavy calendar (§4.2).
- **A widened scope for the cross-cutting extensions** (multi-stop, traffic,
  generalization audit): 11 circuits, every eligible HYPERCAR race
  (≥4 cars, ≥40 laps) discovered by `scripts/discover_endurance_events.py`
  rather than hand-picked, spanning three continents and 2022-2026.

## 3. Method

### 3.1 Tyre degradation (per circuit)

Fixed-effects OLS, mirroring F1's specification but with **car-and-driver**
fixed effects (not car-only): `lap_time = a_{car,driver} + n · tyre_age + ε`,
where `n` is the net within-stint pace slope. WEC rotates drivers within a
car far more than F1 does, so a car-only intercept would confound
driver-pace differences with tyre wear. Unlike F1, the fuel/tyre split is
**not attempted as a separate result**: 84-99% of pit visits also change
tyres at every WEC circuit, so post-fixed-effects correlation between the
fuel and tyre-age regressors runs +0.95 to +1.00 in every one of 11
race-seasons — collinear enough that only the combined net slope is
reported, gated behind a `separable` flag (`SEPARABILITY_LIMIT = 0.90`) that
would flip on its own if a race with enough fuel-only stops ever turned up.
Validation is leave-one-race-out, scored on within-stint demeaned lap times,
exactly as F1 §3.1 — car-driver intercepts cannot transfer to an unseen
race, so raw lap times would leak information. The same validation function
is reused with two different grouping keys: by season (does a slope
transfer to a *different edition of the same circuit*) and by circuit (does
it transfer to a *different track entirely*) — described in the code as "a
different and strictly harder question" than season-holdout, and this
report keeps the two separate rather than treating them as interchangeable.

A field-wide standing-start filter (lap numbers where the whole field's
median pace exceeds 1.3× the race's own green median, applied before the
existing per-car trim) was added after it caught a nonsense slope in an
**IMSA** race (Road America 2024, §4.1 of the IMSA report) — the fix changed
WEC's numbers too, most visibly at Imola 2024 (RMSE 2.66s → 2.36s), since
the same filter runs on both series' data through the shared
`src/degradation/endurance.py`.

### 3.2 Neutralisation risk: two kinds, one shared estimator

WEC's per-lap flag encodes race control state directly rather than F1's
`TrackStatus` intervals, so the extraction layer is new but the underlying
estimators are reused unchanged from the F1 model
(`src/safety_car/model.py`): **Beta-Binomial** for P(≥1 event per race) and
**Gamma-Poisson** for the per-lap deployment rate, both under Jeffreys
priors. What is genuinely different about WEC is that it runs **two**
neutralisation kinds — Full Course Yellow (`FCY`) and a real **Safety Car**
procedure (`SF`) — whereas IMSA has never shown a Safety Car in 63 races.

**Lap indexing is a real methodological choice, not a detail.** Cars are
spread around a multi-kilometre circuit, so "lap N" is not a single instant
— different cars can report different flags for the same lap number while a
neutralisation is starting or ending. The race-level timeline
(`src/safety_car/endurance.py::race_timeline`) takes the **modal flag**: for
every (race, lap), the flag the largest number of cars reported. This
matters beyond Phase 3 itself — building this report's calibration section
(§4.6) surfaced a real bug where a *different* piece of code
(`src/prediction/backtest.py`) checked whether a neutralisation flag
appeared in **any** row of the raw, uncollapsed per-car table instead of
reusing this modal collapse, which let a single car's transient off-flag
reading near a transition mark an entire race as neutralised. That
inflated WEC's apparent FCY rate from a true 9/33 races to 24/33 — caught
and fixed while writing this report (see §4.6). A consequence of the modal
method itself, not the bug: short neutralisations that never become the
modal state on any full lap are invisible to it, so event counts are lower
bounds and durations are reported in laps, not minutes.

### 3.3 Monte Carlo simulator: three real differences from F1

The single-stop engine (`src/simulator/endurance.py`) reuses F1's
common-random-numbers Monte Carlo design (5000 draws, every candidate pit
lap sharing the same per-draw realisation of hazards, coefficients and
noise, so `P(best)` is a clean per-draw argmin) but three structural changes
are forced by how endurance racing actually works:

1. **Fuel range is a hard constraint, not a preference.** Candidate pit laps
   are capped at `current_lap + (fuel_range_laps − laps_since_refuel)`; a
   regression test confirms the engine rejects an already-exhausted-fuel
   scenario outright rather than merely deprioritising it.
2. **Two hazards, sampled independently.** Both FCY and SC pace ratios and
   durations are drawn from their own Phase 2 posteriors each draw, mirroring
   F1's SC/VSC pair.
3. **Stops are expensive and procedurally distinct between series.** WEC's
   pit-stop rule forbids touching the tyres until the fuel hose is out
   (sequential service), so a tyre change adds the *full* tyre-service time
   on top of a fuel-only stop: pooled across 125 WEC fuel-only stops and
   3,364 tyre changes, the premium is **+21.6s**, against IMSA's **+8.7s**
   (IMSA services tyres *while* refuelling, in parallel) — a ~2.5× gap from
   the rulebook alone, not measurement noise. The single-stop engine still
   prices one flat pit loss per stop, so this premium is not yet priced
   into individual recommendations (§5).

**Measured circuit constants (2024 fit):**

| Circuit | Green pace (s) | Pit loss (s) | FCY ratio | SC ratio | Fuel range (laps) | Net slope |
|---|---|---|---|---|---|---|
| Spa | 130.7 | 63.0 | 1.77 | 2.17 | 28 | +0.0404 |
| Fuji | 93.0 | 79.0 | 1.37 | 1.53 | 42 | +0.0135 |
| Bahrain | 114.6 | 80.6 | 1.89 | 1.91 | 32 | +0.0493 |
| Imola | 94.9 | 26.8 | 1.61 | 1.71 | 36 | −0.0198 |

Imola's pit loss (26.8s) is a third of the other three circuits' 63-81s —
echoing F1's own Monaco-vs-Singapore contrast (19.1s vs 27.3s). Pit loss is
measured the same way as F1 (in-lap + out-lap cost against the car's own
green median, restricted to green-flanked stops, trimmed at 2× the pool's
own median), so the two contrasts are genuinely comparable.

### 3.4 Multi-stop strategy: an exact dynamic program

A 6-24 hour race needs 2-29 stops, not the single next stop §3.3 plans, so
`src/simulator/multistop.py::optimal_stop_plan` runs an exact dynamic
program, `O(race_laps × fuel_range)`, minimising total green-running time +
degradation + `n_stops × pit_loss` over every way to partition the race into
stints no longer than the fuel range. `evaluate_plan` then runs the chosen
plan through the same per-draw neutralisation timeline as the single-stop
engine, for a full race-time distribution rather than a point prediction.

### 3.5 Traffic: solving the lapping problem without positions

HYPERCAR shares the track with three slower GT/prototype classes, and a
prototype is forever catching and passing them. The trap is that cumulative
race position does not equal on-track order while lapping is happening,
which is exactly when the cost is paid. `src/simulator/traffic.py` sidesteps
it by comparing **start/finish line crossing times**: a slower car crossing
within 12 seconds ahead of a HYPERCAR counts as traffic just ahead of it,
regardless of how many laps down it is. The measured cost then folds into
the Monte Carlo simulator as calibrated, zero-mean per-race variance (its
mean is already inside the measured green pace) rather than a bias, so it
widens the uncertainty band without shifting which plan wins.

### 3.6 Adversarial rival: the pit stop as a two-player game

`src/simulator/adversarial_endurance.py` reuses the same game-solving core
as F1's reactive-rival model (`solve_pit_game`, rival best-response,
Stackelberg optimum), adapted to endurance's single net degradation slope,
two-hazard timeline, and hard fuel constraint on candidate laps rather than
compound choice. Both cars share the same per-draw hazard and degradation
realisation (common random numbers); only lap noise is drawn independently.

### 3.7 Out-of-sample calibration

`src/prediction/backtest.py` asks whether the per-circuit FCY/SC posteriors
from §3.2 actually forecast, not just fit: each race edition is left out,
its probability formed from the *other* editions of the same circuit only
(Jeffreys `(k+0.5)/(n+1)`), and graded with proper scoring rules (Brier
score, Brier skill vs the series climatology, log-loss). The harness is
series-agnostic — the same code scores F1, WEC and IMSA — and, as of this
report, correctly reuses §3.2's modal-flag collapse rather than the raw
per-car rows (§3.2, the bug found while writing this section).

## 4. Results

### 4.1 Degradation

| Circuit | Seasons | Slope range (s/lap) | RMSE range (s) | LORO mean within-stint R² |
|---|---|---|---|---|
| Spa | 3 | +0.0021 to +0.0404 | 1.05-1.46 | **−0.006** |
| Fuji | 3 | +0.0081 to +0.0186 | 0.54-0.66 | **+0.044** |
| **Bahrain** | 3 | +0.0422 to +0.0493 | 0.70-0.78 | **+0.209** |
| Imola | 2 | −0.0198 to +0.0019 | 0.67-2.36 | **−0.042** |

**Bahrain is the exception that actually transfers**: its net slope sits in
a tight +0.042 to +0.049 s/lap band across three real seasons, and every
individual held-out fold scores positive (+0.227, +0.213, +0.192) — the
strongest transfer found anywhere in this project, F1's own circuits
included. **A measurement-basis note, since the same nominal quantity
appears twice in this project with different values**: the +0.209 above is
the mean over the frozen 2023-2025 degradation scope (3 folds), matching
`degradation_phase2.md`. The widened `ENDURANCE_SCOPE` artifact
(`data/derived/endurance/endurance_degradation_loro.csv`, feeding
[`reports/generalization_audit.md`](../generalization_audit.md)) adds a
2022 fold (+0.133) and therefore reports **+0.191** over 4 folds. Neither
is wrong; they are different fold sets, and the qualitative finding —
every Bahrain fold positive, unique in either series — holds under both. Everywhere else, the pattern from F1 repeats: slopes move too
much between editions of the same race for a fitted trend to predict a
held-out season better than a flat line. A separate leave-one-circuit-out
test (one season each, holding out an entire track) gives a negative mean
R² (−0.012) with two outright sign disagreements (Bahrain and Imola) — a
harder, different question, with the same broad answer: Bahrain's strong
same-season transfer does not extend to predicting a *different* circuit.
Imola's RMSE (up to 2.36s) is markedly higher than the other three
circuits — reported as measured, not explained away; it also has only two
seasons of data, so its leave-one-season-out result rests on a single fold
in each direction.

### 4.2 Neutralisation: two hazards, and WEC prefers the harder one

| Circuit | Editions | SC: P(≥1) [95% CI] | FCY: P(≥1) [95% CI] |
|---|---|---|---|
| Spa | 6 | 0.786 [0.442, 0.981] | 0.500 [0.167, 0.833] |
| Fuji | 4 | 0.700 [0.284, 0.972] | 0.300 [0.028, 0.716] |
| Bahrain | 4 | 0.700 [0.284, 0.972] | 0.300 [0.028, 0.716] |
| Imola | 3 | 0.625 [0.177, 0.961] | 0.375 [0.039, 0.823] |

**Series-wide (33 races pooled): SC in 19/33 (P = 0.574 [0.407, 0.732]),
FCY in 9/33 (P = 0.279 [0.144, 0.439])** — the Safety Car is used more often
than FCY at every single one of the four scoped circuits, not just pooled;
at Spa specifically, SC (5/6 editions) is used more than twice as often as
FCY (3/6). This is the opposite of IMSA, which has never shown a Safety Car
in 63 races (`reports/imsa/safety_car_phase3.md`) — "endurance racing" is
not one hazard model, it is two genuinely different procedures depending on
the series.

### 4.3 Simulator and pit loss

Demo scenario per circuit (mid-race state, 8 laps fuel/tyre age):

| Circuit | Best-median pit lap | P(best) | Spread |
|---|---|---|---|
| Spa | 90 | 0.88 | 35.5s |
| Fuji | 140 | 0.79 | 28.0s |
| Bahrain | 141 | 0.92 | 93.4s |
| Imola | 103 | 0.95 | 34.1s |

At Spa, the recommended lap (90) is **not** the tyre-optimal lap (tyres
alone would want ~106): the fuel tank runs dry first, and lap 90 is where
the simulator actually lands — pinned by a regression test
(`test_spa_optimum_is_pinned_by_the_fuel_constraint`) so the behaviour
cannot silently regress. Track-position value (adjacent-car swap rate on
green laps) runs 0.031-0.043 across the four circuits, versus F1 Monaco's
0.004 — HYPERCAR racing is far more fluid than F1's tightest street circuit,
consistent with WEC's multi-class, prototype-heavy field.

### 4.4 Multi-stop strategy

Across all 11 eligible WEC circuits (`data/derived/endurance/multistop_plans.csv`):
**no WEC race in scope is tyre-limited on stop count** — the dynamic
program's optimum never exceeds the fuel-minimum number of stops, from a
3-stop sprint (COTA) to a 29-stop 24-hour format (Le Mans). Where a
break-even slope exists (positive-slope circuits only), degradation would
need to be **4.9× (Bahrain, the tightest margin) to 67.7× (Sebring, the
most fuel-secure) steeper** than measured before an extra stop would pay
off. 6 of 11 circuits get their stints re-spaced evenly rather than run
fuel-tank-flat-out — a real, circuit-dependent effect that correlates with
positive slope magnitude. This headline is corroborated independently by
real results (§4.7): **25 of 28 real WEC race winners** ran at least one
stint within 3 laps of the circuit's own measured fuel range.

### 4.5 Traffic and adversarial rival

| Circuit | Clear-air vs in-traffic (mean, SD) | Cost per GT car ahead (mean, SD) | Seasons |
|---|---|---|---|
| Spa | **+0.58s** (±0.29) | +0.21s (±0.09) | 3 |
| Imola | +0.15s (±0.05) | −0.01s (±0.01, no signal) | 2 |
| Fuji | +0.14s (±0.05) | +0.04s (±0.02) | 3 |
| Bahrain | +0.13s (±0.14) | +0.10s (±0.04) | 3 |

Spa is the most traffic-costly circuit measured. The single-season read of
+0.95 s/lap reported early in this project's development was Spa's 2024
alone, its steepest edition; the three-season mean is +0.58 s/lap (2023:
0.25, 2024: 0.95, 2025: 0.55) — a self-correction worth stating plainly
rather than quietly overwriting, since it is exactly the kind of claim this
project's own engineering rules ask to be checked, not assumed.

The adversarial-rival result scales with degradation, as the theory
predicts: at Bahrain's steep +0.049 s/lap slope, assuming the rival won't
cover an undercut overstates ego win probability by **~0.44** (0.90 uncovered
vs 0.47 once the rival reacts); at IMSA's flat Watkins Glen, the same
comparison moves the number by only ~0.08 (cited here only as the contrast
this WEC finding is measured against, not as a WEC number). The value of
covering an undercut is a function of how much a stint's tyre age actually
costs — not a fixed strategic constant.

### 4.6 Calibration: a bug found while writing this section

Building this report's calibration numbers surfaced a real discrepancy: two
files (`reports/prediction/calibration.md`, `reports/generalization_audit.md`)
reported WEC's series-wide FCY base rate as ~0.73 and Safety Car as ~0.70,
disagreeing by roughly 2.6× with §4.2's own 0.279/0.574 on the *same* 33-race
sample. Traced to `src/prediction/backtest.py::endurance_race_table`
checking neutralisation flags against the raw, uncollapsed per-car rows
instead of reusing §3.2's modal-flag race timeline — fixed (§3.2, §3.7), and
both dependent reports regenerated. The corrected numbers:

| Target | Level | Races | Base rate | Skill vs climatology |
|---|---|---|---|---|
| WEC FCY | circuit | 33 | 0.273 | −0.538 |
| WEC Safety Car | circuit | 33 | 0.576 | −0.139 |
| Endurance FCY (by series) | series | 96 | — | **+0.528** |

**Per circuit, neither WEC hazard beats the series base rate out of
sample** — 3-6 editions per circuit is too few for the leave-one-out
per-circuit frequency to escape sampling noise, the same qualitative
conclusion as degradation. The positive control (grouping FCY by *series*
instead of circuit) does show clear skill, and the fix makes this control
**stronger**, not weaker: IMSA's true FCY rate (~0.97) and WEC's true rate
(~0.27) are shown to differ far more than the old, wrong 0.97-vs-0.73
comparison suggested — proof the harness distinguishes a real effect
(series) from noise (circuit) rather than always returning zero.

### 4.7 Decision audit: three real stop calls

`src/audit/endurance_cases.py` selects cases by a measurable, uniform
criterion — no public strategy narrative exists for WEC HYPERCAR the way
F1's does — either an opportunistic neutralisation-onset stop or a routine
green-flag stop, on the car that completed the most laps in class.

| Case | Real decision | Model verdict |
|---|---|---|
| A. Bahrain 2025, car 009, lap 216 (SC-onset, 9th/final stop) | Pitted the exact SF-onset lap | +0.04s vs optimum — **inside** window (P(best) 0.838 vs 0.068) |
| B. Bahrain 2024, car 15, lap 125 (routine green stop) | Pitted under green, 4th/8 stops | +4.33s vs optimum — technically **outside**, but against an 819s p10-p90 spread — noise at endurance race-time scale |
| C. Imola 2024, car 5, lap 130 (SC-onset, anomalous-slope circuit) | Pitted the exact SF-onset lap | +0.00s vs optimum — **inside**, decisively (P(best) 0.911) |

Both opportunistic Safety-Car-onset stops (A, C) are strongly endorsed, even
at Imola's anomalous negative slope — the fuel clock binds the recommended
window as hard as the degradation slope does at both circuits. Case B's
"outside" label is a caution against reading the audit's 0.5s window
tolerance (inherited unchanged from F1) literally at endurance race-time
scale: 4.33 seconds against an 819-second spread is not a meaningful
correction.

### 4.8 Generalization audit and the COTA anomaly

Extending the leave-one-out protocol to pit loss (never tested before this
project's generalization audit) gives a strikingly different answer from
degradation: relative RMSE sits at **0.18-0.54 for 7 of WEC's 8 testable
circuits** (Bahrain 0.18, Interlagos 0.23, Le Mans 0.28, Fuji 0.28, Sebring
0.29, Spa 0.41, Imola 0.54), closer to a fixed procedural quantity than a
fitted trend. The
one outlier, **WEC COTA (relative RMSE 1.10)** — worse than anywhere else in
either series — traces to a checked, not assumed, cause: the 2025 race was
**120 laps versus 183 in 2024, same 18 cars**. COTA is also the single
worst-transferring circuit for degradation (mean LORO within-stint R²
**−6.330**, an order of magnitude more negative than anywhere else) — two
independent estimators flagging the same circuit-season pair is stronger
evidence of a genuine race-format change than either alone.

### 4.9 Retrospective winner audit and the fuel-limited sensitivity sweep

Real winning stints, reconstructed from committed lap data and compared to
each circuit's measured fuel range (`reports/endurance_audit.md`): **25 of
28 WEC race winners** ran a stint within 3 laps of the fuel range,
corroborating §4.4's multi-stop headline against what teams actually did.
The three exceptions (COTA 2024, Fuji 2022, Fuji 2023) are not automatic
refutations — a race disrupted by heavy neutralisation bunches stops and
shortens stints for reasons unrelated to tyres. A sensitivity sweep on the
3-lap tolerance itself (`reports/fuel_limited_sensitivity.md`) shows the
WEC share stays a clear majority at every tolerance tested, from 75.0% at
the strictest reading (exact reach only) to 100.0% at a 7-lap tolerance —
flatter and more robust to the tolerance choice than IMSA's own sweep
(54.5% to 93.9% over the same range).

### 4.10 Reliability and attrition: a complementary results-level layer

Every layer above is lap-level. One strategy-relevant quantity is not
available at lap level at all and is better served by results history:
**the probability a car reaches the classified finish**.
[`reports/wec/reliability.md`](reliability.md) measures it over **3,035
car-entries, 2011-2023**, all classes, using the same Jeffreys
`Beta(0.5, 0.5)` smoother as the calibration backtest so a thinly-sampled
class gets a wide interval rather than a false 0% or 100%.

| Class | Entries | Finish rate | 95% CI |
|---|---|---|---|
| LMP1 | 491 | 0.822 | [0.787, 0.855] |
| LMP2 | 977 | 0.852 | [0.829, 0.874] |
| LMGTE Am | 843 | 0.867 | [0.843, 0.889] |
| **HYPERCAR** | 140 | **0.876** | [0.817, 0.925] |
| LMGTE Pro | 579 | 0.892 | [0.866, 0.916] |

The falsifiable check this layer was built around: **attrition should rise
with race length**, so a 24h finish rate must sit below a 4h one, or the
measurement is wrong. It holds — **0.712** [0.680, 0.744] at 24h against
**0.944** [0.876, 0.986] at 4h. Worth stating plainly that the middle of
that range is not monotonic (6h 0.905, 8h 0.935): the 8h finish rate sits
slightly *above* the 6h one, on overlapping intervals and a much smaller
sample (253 vs 1,929 entries), so the honest reading is that the control
fires on the endpoints and the intermediate ordering is not resolved by
this data.

This layer deliberately does **not** feed the degradation or neutralisation
models — it has no per-lap resolution, so it cannot say *when* in a race a
car failed, only whether it was classified. It is a complementary prior,
reported separately rather than folded into the simulator, and IMSA has no
equivalent in this project (the Kaggle results history covers WEC only).

## 5. Threats to validity

**Internal validity** — could a reported effect be an artefact of the
estimation, not the phenomenon it claims to measure?

- **Compound is not in the source at all**, so degradation is a single net
  slope rather than F1's per-compound polynomial — a coarser, not a wrong,
  measurement.
- **Classical homoscedastic standard errors** are used throughout, as in F1;
  real lap-time noise (traffic, fuel-load variance, track evolution) is
  heteroscedastic, so reported CIs are approximate.
- **FCY and SC are modelled as independent hazards**, though a real FCY can
  escalate into a Safety Car — the same caveat F1's own SC/VSC pair states
  about itself.
- **The single-stop engine still prices one flat pit loss per stop**, not
  yet distinguishing the +21.6s tyre-change premium (§3.3) from a fuel-only
  splash — a real cost this report measures but the recommendation engine
  does not yet price in.

**External validity** — how far do the fitted numbers travel beyond the
races they were fitted on?

- **Degradation transfers almost nowhere except Bahrain** (§4.1); a slope
  fitted on two editions of Spa, Fuji or Imola routinely fails to predict a
  third. Pit loss, by contrast, transfers well at 8 of 9 testable circuits
  (§4.8) — the companion generalization audit's central point is that
  "nothing generalises" was itself an overclaim, and the answer depends on
  whether the fitted quantity is closer to a fixed procedural constant or a
  season-specific trend.
- **Per-circuit neutralisation odds do not beat the series base rate**
  (§4.6); only pooling at the series level recovers skill, at the cost of
  losing per-circuit resolution.
- **Imola has only two seasons** of HYPERCAR data (it did not race there
  before 2024), so its leave-one-season-out result rests on a single fold
  in each direction — the thinnest evidence base of the four scoped
  circuits.
- **WEC COTA's 2025 relative RMSE (1.10) and R² (−6.33) are both explained
  by a real race-format change**, not a data artefact (§4.8) — a reminder
  that "does this generalise" and "is the source data comparable across
  editions" are different questions, and this project answers both rather
  than assuming the first once the second looks fine.
- **The reliability layer's class comparison spans a regulation era it does
  not model** (§4.10): 2011-2023 covers LMP1's peak and its replacement by
  HYPERCAR, so a cross-class finish-rate ranking mixes eras as well as
  classes. HYPERCAR's own 140 entries are the thinnest sample in that
  table, and its interval says so.

**Construct validity** — do the simulator's objective and the audit's
comparison actually capture "good strategy," or a narrower proxy for it?

- **No rivals, no track position, and no driver-stint regulatory
  constraints** (WEC requires a minimum of three drivers) in the single-stop
  or multi-stop engines — the adversarial-rival model (§3.6, §4.5) targets
  the rival-reaction gap specifically, but even it is limited to a
  pit-lap-and-fuel-window response, not a full re-plan, and does not yet
  feed the multi-stop layer.
- **The decision audit's 0.5 s window tolerance is inherited unchanged from
  F1**, where race times run to ~5,000s; at WEC's endurance race-time scale
  (Case B: 13,286s), that tolerance is a much stricter bar than it was
  designed for, and this report states that explicitly rather than letting
  a "technically outside the window" verdict imply more precision than the
  underlying spread supports.
- **Traffic enters the simulator as variance, not as a strategic lever**:
  the measured cost widens the uncertainty band but does not let the
  simulator plan *around* an anticipated traffic pattern the way a real
  strategist might.

## 6. Future work

Price the tyre-change premium (§3.3) into the single-stop engine's per-stop
cost rather than treating pit loss as flat; extend the adversarial-rival
model into the multi-stop layer, so a reacting rival is priced across a full
race rather than a single next stop; a two-state (FCY-may-escalate-to-SC)
hazard model, replacing the current independence assumption; extend the
retrospective decision audit beyond three cases as more races enter scope
via the rolling `ENDURANCE_SCOPE`.

## 7. Reproducibility

Python 3.13, dependencies pinned in `requirements.lock` (duckdb, pandas
2.3.3, numpy 2.5.1, scipy 1.18.0). WEC races are committed as derived CSVs
under `data/derived/wec/` and `data/derived/endurance/`, so every test in
this report's scope runs fully offline; `scripts/run_endurance_flags.py` and
`scripts/run_endurance_models.py` re-pull and refit only if explicitly asked
to refresh the source. All stochastic code is seeded. This report's layer is
covered by a dedicated subset of the project's 249 pytest tests (data
loading, the endurance degradation/neutralisation/simulator models, the
multi-stop dynamic program, traffic and adversarial-rival estimators, and
the decision-audit state reconstruction); the remaining tests cover F1 and
IMSA, out of scope for this report. Each phase's full output is a committed
report in `reports/wec/`.
