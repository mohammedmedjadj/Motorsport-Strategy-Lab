# What four series say that one cannot

Every result here needed more than one championship to exist. They are placed
in one document because they are *comparisons*; every fitted number behind them
is estimated per series and per class and is never pooled.

## The six populations

Every strategy figure below is computed on **all 205 planned race-seasons**,
not one representative season per circuit. That distinction is not
housekeeping: the plan depends on each race's fitted degradation slope, and
slopes do not transfer between seasons (§4), so a per-circuit sample was
refuted by this document's own fourth finding.

| series | class | races | planned | median slope (s/lap) | median pit loss | tyre-limited | share | tyre premium |
|---|---|---|---|---|---|---|---|---|
| WEC | HYPERCAR | 28 | 27 | +0.0139 | 74.0 s | 0 | 0.0% | 21.6 s |
| ELMS | LMP2 Pro/Am | 17 | 17 | +0.0205 | 63.8 s | 0 | 0.0% | 35.4 s |
| ELMS | LMP2 | 25 | 25 | +0.0161 | 61.7 s | 1 | 4.0% | 25.1 s |
| IMSA | GTP | 33 | 32 | +0.0166 | 57.0 s | 2 | 6.2% | 8.7 s |
| IMSA | GTD PRO | 47 | 46 | +0.0190 | 39.6 s | 7 | 15.2% | 16.9 s |
| IMSA | GTD | 60 | 58 | +0.0200 | 24.4 s | 15 | 25.9% | 17.6 s |

*"Races" is what the degradation model fits; "planned" is what the multi-stop
program could plan. They differ by five race-seasons across the whole project —
a race with neither a Full Course Yellow nor a Safety Car has no neutralised
laps to measure a pace ratio from, so no race model exists for it. Every one is
listed with its reason in `data/derived/endurance/multistop_skipped.csv`.*

Sorted by pit loss, and the tyre-limited share sorts with it **without a single
inversion**. That is the synthesis.

## 1. The pit stop decides the strategy regime, not the car

The correlation between a class's median pit loss and the share of its races
where the optimum beats the fuel minimum is **−0.982**.

Read down the table: WEC Hypercar, at a 74-second stop, is fuel-limited in all
27 of its races; IMSA GTD, at 24 seconds, is tyre-limited in 15 of 58. Every
class in between falls exactly where its stop cost puts it.

This overturned the project's own published conclusion twice. "Every measured
race is fuel-limited on stop count" was true when only prototypes were
modelled — it was a fact about **expensive stops**, stated as a fact about
endurance racing. Adding GT3 broke it; adding ELMS and GTD PRO showed the
break was not about GT3 either.

The mechanism is in
[`when_tyres_beat_fuel.md`](when_tyres_beat_fuel.md): a cheap stop is
**necessary but not sufficient**. No race above a 22.5 s pit loss is
tyre-limited anywhere in 205 race-seasons (Mann-Whitney **p = 1.1 × 10⁻¹⁴**),
and below that threshold real degradation decides (**p = 1.5 × 10⁻⁸**). That is
**150 race-seasons above the edge, across all six classes, with no exception.**

The *rule* is what that supports; the *number* is weaker than it looks. The edge
sits at 22.5 s because one race puts it there (IMSA GTD Indianapolis 2025) and
the next tyre-limited race is at 13.2 s. This document used to argue that the
threshold was trustworthy because it "sat in exactly the same place when this
was computed on 66 entries" — but a maximum over a growing sample can only move
up, so a stable maximum shows that no counterexample appeared above it, not that
the threshold is well located. Quote 22.5 s as an order of magnitude, and see
[`when_tyres_beat_fuel.md`](when_tyres_beat_fuel.md) before treating it as a
constant.

The cleanest single illustration is Mugello 2024, where LMP2 is tyre-limited on
a 9.2 s stop and Pro/Am at the same circuit in the same year is not, on a
comparable 10.8 s stop but a shallower slope.

## 2. The tyre-change premium is the car, not the crew

| comparison | what changes | premium |
|---|---|---|
| IMSA GTP → GTD | the car (prototype → GT3) | 8.7 s → 17.6 s |
| IMSA GTD → GTD PRO | the crew (Pro/Am → all-pro) | 17.6 s → 16.9 s |

Holding the car fixed and changing only the driver rating moves the pit-stop
premium by 0.7 s. Changing the car moves it by nine. This required GTD PRO to
exist: with GTD alone, the GT3-versus-prototype gap was equally consistent with
a crew effect.

It also exposed a pooling error that would have destroyed a published result.
The premium had been measured per *series*; pooling IMSA's three classes gives
roughly 14 s and erases the finding that IMSA services tyres in parallel with
the fuel fill while WEC does it in sequence.

**ELMS disagrees, and that is reported rather than smoothed.** Its two classes
differ by 10.3 s in premium — but also by 9.2 s in the fuel-only stop, which a
driver rating should not change. That looks like a procedural or sampling
difference and is recorded as unexplained.

## 3. No consistent crew effect on tyre wear

Two natural experiments, same design — the same car under the same regulations,
entered with and without a mandatory amateur-rated driver:

| experiment | Pro/Am − Pro | pairs | paired Wilcoxon | holds up under robustness? |
|---|---|---|---|---|
| IMSA GTD vs GTD PRO | +0.0040 s/lap | 44 | **p = 0.032** | **no** — 0.096 / 0.094 / 0.054 |
| ELMS Pro/Am vs LMP2 | −0.0053 s/lap | 17 | p = 0.148 | not significant to begin with |

**They point in opposite directions.** IMSA's amateur-rated crews degrade
faster, as the intuitive hypothesis predicts; ELMS's degrade *slower*, which
it does not. Only IMSA's clears 5%, and it clears it once: a sign test, the
removal of the in-progress 2026 season, and the removal of races hit by the
known track-evolution defect each put it back above the line.

The honest summary is that **no consistent crew effect survives across
championships**, and that the one significant-looking result is a statement
about statistical power rather than about tyres.

One test alone would have been read as "a trend towards" and written up as a
finding. Two independent ones make that impossible, which is the argument for
the second series.

These numbers previously read p = 0.085 and p = 0.0093, with the two
championships' significance the other way round. They were computed by hand,
the slopes beneath them were corrected twice, and no code recomputed them.
Both tests now come from `src/degradation/crew_rating.py` and are pinned by
`tests/test_crew_rating.py`, which fails if any document here — the README
included — quotes a crew p-value the code does not produce. The post-mortem is
[`reports/elms/crew_rating_findings.md`](../elms/crew_rating_findings.md) §6.

## 4. Slope instability is not the machinery

Degradation slopes fitted on one season routinely fail to predict another —
the within-stint R² is at or below zero almost everywhere. The obvious
candidate cause was heterogeneous, Balance-of-Performance-adjusted cars.

ELMS LMP2 is the control: one chassis, one engine, near-spec. Its slopes fail
to transfer exactly as the others do (leave-one-race-out mean R² of +0.035,
−0.001, −0.011, −0.067, −0.004 across its circuits). **The instability is not
the hardware.**

Bahrain is the strongest transfer **in WEC**, at a leave-one-race-out mean
within-stint R² of +0.217 over four folds (+0.049, +0.310, +0.266, +0.243).
It is **not** the strongest in this project: widening to IMSA's GT3 classes
found four circuit-classes above it — Lime Rock GTD **+0.573**, Lime Rock
GTD PRO +0.497, Laguna Seca GTD +0.273, Laguna Seca GTD PRO +0.256. Short
circuits with cheap stops transfer better than long ones with expensive
stops, which is the same axis the cross-series pit-loss rule turns on.

So transfer is not impossible everywhere — it is rare, and where it happens it
tracks circuit length and stop cost rather than machinery. That is a weaker
claim than "Bahrain is the one exception", which this document asserted until
the GT3 classes were scoped and measured.

## 5. Three neutralisation regimes, no average that describes any

| series | races with ≥1 FCY | with ≥1 Safety Car | SC rate/lap |
|---|---|---|---|
| IMSA | 61 of 63 | **0 of 63** | 0.00004 (prior floor) |
| WEC | 9 of 33 | 19 of 33 | 0.00605 |
| ELMS | 15 of 29 | 23 of 29 | 0.01592 |

A pooled endurance model would sit between 0.00004 and 0.01592 per lap and
describe none of them. Since a stop under caution is discounted by the pace
ratio, every strategy conclusion depending on that value would be wrong in a
different direction per championship.

## What the separation rule actually bought

The project's rule — never pool two series, never pool two classes — began as
a discipline. Four of the five results above **only exist because of it**, and
two of them are corrections to conclusions that pooling had already produced:
the fuel-limited claim and the tyre-change premium were both published, both
wrong, and both wrong specifically because a population had been averaged.

The cost is real: six populations mean six sets of coefficients, thinner
samples, and cluster-robust intervals on 7-car fields. The alternative is
plausible numbers describing nothing.

## Caveat that applies to every slope above

None of these fits carries a race-time term, so track evolution lands on the
tyre-age coefficient with its sign inverted; 41 of 210 races fit a negative
slope. Read every slope as a **lower bound**. The diagnosis, and an attempted
fix that was built, validated on synthetic data and withdrawn because it made
the real-data refit worse, are in
[`track_evolution_omitted_variable.md`](track_evolution_omitted_variable.md).

Its effect on the results above is asymmetric and stated there: the
tyre-limited group carries clearly positive slopes, so a bias pushing slopes
down can only understate finding 1, never manufacture it; finding 4 is
supported rather than undermined; and findings 2 and 3 rest on paired
comparisons within the same weekend, where a shared trend cancels.
