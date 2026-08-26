# A Near-Spec Control for Tyre Degradation Instability: the European Le Mans Series

**Author:** Mohammed Reda Medjadj
**Date:** August 2026.
**Repository:** `motorsport-strategy-lab`. Every number here is produced by the
scripts in `scripts/` and traceable to a committed artifact under
`data/derived/`; the figures are checked against those artifacts by
`tests/test_reports_are_not_stale.py`, so this document cannot quietly drift
from the data it describes.

This report covers **ELMS only**. WEC and IMSA have their own
([`reports/wec/methodology.md`](../wec/methodology.md) ·
[`reports/imsa/methodology.md`](../imsa/methodology.md)). The three share
loader and estimator code — `src/data/endurance_loader.py`,
`src/degradation/endurance.py`, `src/safety_car/endurance.py`,
`src/simulator/endurance.py` — because the underlying problem is genuinely the
same: a pit visit, a tyre change and a driver stint are three distinct signals
that FastF1's data model never forces apart on the F1 side. **No fitted number
below is pooled with either other series**, and §4.4 is the reason that rule
exists rather than a stylistic preference.

Within ELMS, the same rule applies one level down: `LMP2` and `LMP2 Pro/Am`
are fitted separately throughout and share no number. §4.5 is what that buys.

## Abstract

ELMS was not added to this project for breadth. It was added because it is the
only championship available that could **falsify a hypothesis the project had
carried since its Formula 1 phase**, and the falsification is the headline
result.

Degradation slopes fitted on one season routinely fail to predict another,
everywhere this project has looked. The obvious candidate cause was the
machinery: Formula 1 cars differ from each other, and Hypercar and GTP are
manufacturer prototypes equalised by a Balance of Performance that is adjusted
between events. ELMS's LMP2 is as close to a one-make formula as top-flight
sportscar racing offers — an Oreca 07 chassis and a Gibson GK428 engine for
essentially the whole field. **If slopes still fail to transfer there, the
instability is not the car.**

They still fail. Leave-one-race-out mean within-stint R² is at or below zero at
every ELMS circuit in both classes, reaching **−0.455** at Portimao for LMP2
Pro/Am. A slope fitted on a circuit's other seasons explains none of the
held-out season's within-stint variance, and at Portimao it is materially worse
than predicting the mean. The hypothesis is closed, negatively, on a control
field designed to test it.

Three further results follow from the same scope. ELMS supplies a **second
natural experiment on crew rating**, and it disagrees in sign with IMSA's:
Pro/Am crews here degrade −0.0053 s/lap *less* than professionals (17 matched
pairs, p = 0.148), where IMSA's Pro/Am crews degrade +0.0040 s/lap *more*
(44 pairs, p = 0.032) — and IMSA's does not survive any of three robustness
checks, so neither championship establishes an amateur effect. ELMS is a
**third distinct neutralisation regime**, with a Safety Car in 23 of 29 races
against WEC's 19 of 33 and IMSA's 0 of 63. And it is **almost entirely
fuel-limited** on stop count, with exactly one exception that turned out to
belong to a cross-series pattern rather than to ELMS.

The report also states plainly what it does not establish. 12 of 42 ELMS
race-seasons fit a *negative* net degradation slope, which is physically
impossible for a wearing tyre, and the cause is a diagnosed and **unfixed**
model defect (§5.1). Every slope here should be read as a lower bound.

## 1. Motivation

By the time ELMS was scoped, this project had measured degradation-slope
instability in three championships and reported it three times as a finding.
Repeating a measurement is not the same as testing it. The finding had an
obvious alternative explanation that none of the three could rule out:

> Formula 1, WEC Hypercar and IMSA GTP all field **heterogeneous machinery**.
> F1 cars are built to different designs; Hypercar and GTP are equalised by a
> Balance of Performance whose adjustments between events change what a car
> does to its tyres. A slope fitted in one season might legitimately not apply
> to the next, because it is not the same car.

That explanation is comfortable and it is testable. What it needs is a field
where the cars are the same, and where the same estimator can be run without
modification. ELMS LMP2 provides exactly that:

| | this project's other prototype classes | ELMS LMP2 |
|---|---|---|
| chassis | multiple manufacturers | Oreca 07, near-universal |
| engine | multiple manufacturers | Gibson GK428 |
| performance equalisation | Balance of Performance, adjusted in-season | none needed |

The prediction was explicit and recorded in
[`data_availability_phase0.md`](data_availability_phase0.md) **before the fit
was run**: if slopes transfer in LMP2 but not elsewhere, the instability is
the machinery and the project's central finding is much weaker than claimed.
If they fail in LMP2 too, the machinery explanation is dead.

This is the only place in the project where a series was chosen to make a
result falsifiable rather than to add data. It is worth saying that the
prediction pointed the *inconvenient* way: a transfer result in LMP2 would
have undermined three phases of prior work.

## 2. Data

### 2.1 Source and scope

The same community-maintained lap-and-flag dataset used for WEC and IMSA, which
also carries ELMS. Scope is frozen in `src/data/endurance_scope.py` and every
race in it cleared the same eligibility floor as the other series.

| | LMP2 | LMP2 Pro/Am | total |
|---|---|---|---|
| race-seasons | 25 | 17 | **42** |
| circuits | 9 | 8 | 9 |
| seasons | 2021–2025 | 2023–2025 | 2021–2025 |
| field size (cars fitted) | 7–17 | 7–11 | 7–17 |

**52,472 raw race laps, 69.6% kept for modelling** (median per race), on the
same stage-by-stage accounting as WEC and IMSA
([`data_quality_phase1.md`](data_quality_phase1.md)).

### 2.2 The class-label trap, and why it changes the crew analysis

**Before 2023, the `LMP2` label covers every LMP2 entry.** From 2023 it means
the professional subset only, with Pro/Am entries carrying their own label.
Pairing the full 2021–2025 `LMP2` range against `LMP2 Pro/Am` would therefore
compare a *mixed* field against a Pro/Am one and report the difference as a
crew effect.

Every cross-class comparison in this report is restricted to 2023 onward for
that reason. The restriction lives in code
(`src/degradation/crew_rating.py::CREW_PAIRS`, with the reason stored on the
dataclass) rather than in a reader's memory, because a scope restriction that
is only written down is a scope restriction that gets dropped.

### 2.3 What the source does not carry

- **No tyre compound.** As in WEC and IMSA, so degradation is a single net
  slope, never a per-compound curve.
- **No positions.** Track position is reconstructed from cumulative time within
  the class, which is what makes the adjacent-swap rate in §4.6 measurable at
  all.
- **2021 flags are empty** for part of the calendar, which is why the
  neutralisation model in §4.3 runs on 29 races rather than all 42.

## 3. Method

Identical to WEC and IMSA — that is the point. A series is added to this
project by scoping data, not by writing a new model, and a result that
required a new estimator would not be comparable with the ones it is meant to
be compared against.

### 3.1 Degradation

    lap_time = a_{car,driver} + n · tyre_age + eps

`n` is the **net within-stint slope**: tyre loss and fuel gain combined.
Fixed effects are per car-driver unit, so each stint's pace level is absorbed
and only the within-stint trend is estimated.

Standard errors are **cluster-robust by car** with a `t(G−1)` reference
distribution (`src/degradation/robust.py`). ELMS fields run 7–17 cars, so that
reference is doing real work rather than being a formality: at 7 cars it is a
`t(6)`, whose 95% interval is 22% wider than the normal's. Lap times inside one
car's race are not independent observations, and the classical OLS standard
error counts the same information repeatedly.

### 3.2 Neutralisations

Beta-Binomial for the per-race probability of at least one event, Gamma-Poisson
for the per-lap rate, both with Jeffreys priors. Full Course Yellow and Safety
Car are fitted **separately and empirically**, never assumed to be one hazard.
The `+0.5` pseudo-count is applied identically to both, which is what lets
IMSA's never-observed Safety Car take a small positive rate instead of an
impossible exact zero — and the same code path therefore cannot special-case
ELMS either.

### 3.3 Simulator

`src/simulator/endurance.py` for the *next* stop under a hard fuel-range
constraint, plus `src/simulator/multistop.py` for the whole race: an exact
dynamic program over every fuel-feasible stint partition, evaluated at expected
pace and again under stochastic neutralisations with common random numbers.

Degradation coefficients are resampled per draw from their measured
uncertainty, using a Student's *t* with the fit's own cluster count as degrees
of freedom — so a race fitted on 7 cars produces a visibly wider race-time
distribution than one fitted on 17, rather than silently the same.

### 3.4 The crew comparison

Paired, one pair per race where both classes ran, keyed on `(event, season)`.
**Not on the circuit**: `pivot_table` averages duplicate keys without warning,
and IMSA — the comparison this one is set against — ran two distinct races at
Watkins Glen in 2021.

Wilcoxon signed-rank rather than a paired *t*-test, because the slope
distribution has heavy negative outliers from the unmodelled defect in §5.1
and a mean-based test would let those outliers drive the answer.

## 4. Results

### 4.1 Degradation

| | LMP2 | LMP2 Pro/Am |
|---|---|---|
| median net slope | **+0.0161 s/lap** | **+0.0205 s/lap** |
| steepest | +0.0751 | +0.0832 |
| flattest | −0.2134 (Portimao 2023) | −0.2979 (Portimao 2023) |
| races fitting a negative slope | 7 of 25 | 5 of 17 |

For comparison on identical code: WEC HYPERCAR +0.0139, IMSA GTP +0.0166,
IMSA GTD +0.0200, IMSA GTD PRO +0.0190. ELMS sits inside that range, which is
itself mildly informative — the near-spec field does not degrade its tyres at a
noticeably different rate from the BoP-adjusted ones.

### 4.2 The control experiment, and it comes back negative

Leave-one-race-out mean within-stint R², per circuit:

| circuit | LMP2 | LMP2 Pro/Am |
|---|---|---|
| Barcelona | +0.035 | +0.027 |
| Imola | −0.001 | −0.003 |
| Paul Ricard | −0.011 | −0.011 |
| Portimao | **−0.067** | **−0.455** |
| Spa | −0.004 | −0.012 |

Every value is at or below zero except two that are indistinguishable from it.
A slope fitted on a circuit's other seasons explains **none** of the held-out
season's within-stint variance, and at Portimao it is actively worse than
predicting the mean.

**This closes the hypothesis of §1.** The season-to-season instability of
degradation slopes is not an artefact of heterogeneous, BoP-adjusted machinery:
it survives intact on a field where the chassis and engine are the same for
everyone. Whatever drives it — track evolution, weather, traffic, tyre
allocation, or the genuine year-to-year variation of a compound — it is not the
car.

It is a negative result, and it is the most useful thing this series
contributed.

Note that the unmodelled defect of §5.1 makes this conclusion *more* secure
rather than less. A trend that differs by race is one more reason fits fail to
transfer, so correcting it could only reduce the failure, never manufacture it.

### 4.3 A third neutralisation regime

| series | races with ≥1 FCY | races with ≥1 SC | SC rate/lap (posterior) |
|---|---|---|---|
| IMSA | 61 of 63 | **0 of 63** | 0.00004 (prior floor) |
| WEC | 9 of 33 | 19 of 33 | 0.00605 |
| **ELMS** | 15 of 29 | **23 of 29** | **0.01592** |

ELMS is the most Safety-Car-dominated of the three, ahead of WEC, where IMSA
records none at all. Three series, three regimes. **A pooled "endurance"
neutralisation model would describe none of them**, which is the third
independent confirmation of the rule this project applies everywhere.

Getting these numbers required fixing `scripts/run_endurance_flags.py`, whose
query hard-coded `IN ('imsa', 'wec')`. It was caught by the `KeyError` guard in
`load_race_model` rather than by a suspicious result — without that guard, ELMS
models would have been built on a default Jeffreys prior and would have
produced entirely plausible stop plans from an invented neutralisation risk.
That is the argument for failing loudly on a missing posterior rather than
falling back to a default.

### 4.4 Stops, fuel, and the one exception

| | LMP2 | LMP2 Pro/Am |
|---|---|---|
| median pit loss | **64.8 s** | 62.2 s |
| fuel-only stop | 44.4 s | 35.2 s |
| tyre-change premium | **25.1 s** | **35.4 s** |
| median fuel range | 24 laps | 24.5 laps |

An expensive stop on a short tank, which is why ELMS is almost entirely
fuel-limited on stop count: 41 of 42 audited winners ran a fuel-limited longest
stint, and the multi-stop program finds **1 of 17 circuit-seasons
tyre-limited**.

That one is LMP2 at Mugello 2024, whose **9.2 s pit loss is the cheapest in the
series** and which takes six stops against a fuel minimum of four. It is not an
ELMS curiosity. It is one of nine entries across the project behind the
cross-series rule that the *pit stop* decides the strategy regime — the
correlation between a class's median pit loss and its share of tyre-limited
circuits is −0.913 across six populations
([`when_tyres_beat_fuel.md`](../when_tyres_beat_fuel.md)).

The 10.3 s gap in tyre-change premium between the two classes is **not**
reported as a crew effect. Their *fuel-only* stops also differ by 9.2 s, which
no driver rating should change, and the Pro/Am cell rests on 79 fuel-only
stops. That pattern looks like a difference in stop procedure or in sample, and
it is recorded as unexplained.

### 4.5 The second crew experiment, and it disagrees with IMSA's

| test | Pro/Am − Pro | pairs | Pro/Am steeper in | paired Wilcoxon |
|---|---|---|---|---|
| IMSA GTD vs GTD PRO | **+0.0040** s/lap | 44 | 28 of 44 | p = 0.032 |
| ELMS LMP2 Pro/Am vs LMP2 | **−0.0053** s/lap | 17 | 5 of 17 | p = 0.148 |

They point in opposite directions. IMSA's amateur-rated crews degrade faster,
as the naive hypothesis predicts; ELMS's degrade *slower*, which it does not.

Only IMSA's clears 5%, and it clears it exactly once. Re-running it under three
defensible variations, none of them a strawman:

| variation | IMSA | ELMS |
|---|---|---|
| headline | p = 0.032 | p = 0.148 |
| sign test — direction only | p = 0.096 | p = 0.144 |
| latest season dropped | p = 0.094 | p = 0.160 |
| both slopes positive | p = 0.054 | p = 0.375 |

**Every variation puts IMSA back above 0.05.** A result that appears and
disappears depending on which defensible analysis you ran first is a statement
about statistical power, not about tyres. Neither championship establishes an
amateur effect on tyre wear.

What the pair of experiments does establish is the design. Two independent
natural experiments now exist inside this project, both like-for-like on car,
regulations, weekend and circuit. **One test alone would have been written up
as "a trend towards".** That is precisely what the earlier version of this
analysis did, in the opposite direction, and §5.3 is the account of it.

### 4.6 Traffic and track position

Median adjacent-swap rate **0.0463** over 17 circuit-class entries, with a
median probability of holding position over 15 laps of 0.49 — positions
reconstructed from cumulative time within the class.

Inter-class traffic cost is measured over 25 ELMS race-seasons, and it is
**noisy enough that single-season figures should not be quoted**. Spa averages
0.48 s/lap lost in traffic against clear air over five seasons with a standard
deviation of 0.45; Portimao averages −0.56 with a standard deviation of 1.29,
which is to say it is not measured at all; Silverstone reads 10.07 s/lap on a
single season and is reported rather than trusted. The simulator therefore
folds traffic in as calibrated, zero-mean race-time *variance*, which widens
the uncertainty band without biasing which plan wins.

## 5. Threats to validity

### 5.1 The negative slopes are a model defect, and it is not fixed

**12 of 42 ELMS race-seasons fit a negative net slope**, and Portimao 2023
returns −0.213 s/lap (LMP2) and −0.298 (Pro/Am) for a tyre that is wearing.

The cause is diagnosed. At Portimao 2023 the race gets **17.8 seconds a lap
faster** from start to finish — a drying or rapidly rubbering-in track. Within
any stint the correlation between lap number and tyre age is 1.000, so
later-in-stint laps are simultaneously on older tyres and on a much better
track. The car-driver fixed effects absorb each unit's pace *level*; they
absorb nothing of a trend running through the whole race. Track evolution is
therefore attributed to tyre age, with its sign inverted.

The F1 model carries a lap-number regressor as a fuel proxy, which incidentally
absorbs some of this. The endurance model deliberately replaced it with
`laps_since_refuel`, because endurance cars refuel and fuel load is not
monotone in lap number. That substitution was correct for fuel and left nothing
carrying race time.

**Two corrections were built and both were withdrawn.** A piecewise-linear
race-time basis, validated on synthetic races where it recovered a known
+0.0800 s/lap exactly, made the real-data refit worse: negative slopes across
the project went 41 → 64. A two-way fixed-effects estimator with a fixed effect
per lap, which is exact at every drift level in synthetic testing, produced the
identical failure. The one mechanism proposed to explain the gap — selection in
which cars carry fresh tyres at a given lap — measures at only −0.047 to −0.118
and is far too small.

**The cause of the failure is not established**, and this report does not claim
otherwise. Full account:
[`track_evolution_omitted_variable.md`](../track_evolution_omitted_variable.md).
Read every slope in §4.1 as a lower bound on degradation.

What this does *not* invalidate is §4.2: an omitted trend that differs by race
makes fits less transferable, not more, so it supports that conclusion.

### 5.2 Scope

Nine circuits, all European, and no round longer than four hours. ELMS
therefore says nothing about the 12- and 24-hour formats where WEC and IMSA
differ most, and its neutralisation regime is measured on 29 races — enough to
separate it from the other two series, not enough for per-circuit posteriors
that beat the series rate.

The Pro/Am class exists for three seasons only, which is what limits the crew
comparison to 17 pairs. More seasons is the single most valuable thing that
could happen to §4.5.

### 5.3 A published result that was wrong, and how

The table in §4.5 previously read **IMSA p = 0.085, ELMS p = 0.0093**, with the
ELMS difference at −0.0143 s/lap, and the conclusion drawn from it was that
"the significant test contradicts the hypothesis". Every one of those numbers
was wrong, and the two championships have since **swapped** which one clears
5%.

Nothing changed underneath in a suspicious way. The slopes were corrected
twice, for good reasons: the traffic trim was found to be selecting on the
dependent variable and removing up to 25% of the measured slope, and a
field-wide neutralisation ramp was leaking into the fits until a hysteresis
filter caught it. Both corrections were right. Both moved every number in the
comparison.

**The defect was that the comparison had no code.** It was computed once, by
hand, and written into prose. Prose does not get recomputed when its inputs
change, and no test can pin a number that nothing produces — so the published
figures drifted away from the artifacts silently and stayed there across
several regenerations that would otherwise have caught them.

The conclusion happened to survive. It survived by luck, and the fix is
structural rather than a correction: `src/degradation/crew_rating.py` computes
both tests and their robustness variants from the committed artifact, and
`tests/test_crew_rating.py` fails if any document in this repository — the
README and the interactive demo included — quotes a crew p-value the code does
not produce.

The lesson generalises past this analysis, and it is the one worth keeping:
**a published finding with no committed code behind it cannot become stale,
only quietly wrong.** Staleness is visible on regeneration; being quietly wrong
is not.

## 6. Future work

- **Reproduce the failure, not the fix.** The open problem in §5.1 is not "add
  a track-evolution term" — that has been tried twice. It is to build a
  synthetic generator faithful enough to *break* both estimators, which would
  identify what the real races contain that the synthetic ones do not.
- **More Pro/Am seasons**, which is the only thing that will move §4.5.
- **A per-circuit neutralisation posterior** once ELMS has enough races to beat
  its own series rate; the calibration harness in `src.prediction` already
  exists and ELMS is not yet a target in it.
- **Driver-stint identification**, which would turn the crew question from a
  class-level comparison into a within-race one and is the only route to a
  mechanism rather than an association.

## 7. Reproducibility

```bash
python scripts/run_endurance_flags.py    # network: race-control flags
python scripts/run_endurance_models.py   # offline: fits, quality, LORO, traffic
python scripts/run_multistop.py          # offline: full-race plans
python scripts/run_endurance_audit_cases.py
```

Every number above comes from the artifacts those scripts write, all committed
under `data/derived/`. The claims are pinned by
`tests/test_endurance_artifacts.py`, `tests/test_endurance_safety_car.py`,
`tests/test_crew_rating.py` and `tests/test_reports_are_not_stale.py`.

Simulation figures use the project's standard seed and draw count; the
endurance engine uses common random numbers across candidate stop laps, so
comparisons between candidates are paired rather than independently noisy.
