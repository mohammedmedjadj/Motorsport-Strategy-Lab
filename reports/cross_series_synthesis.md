# What four series say that one cannot

Every result here needed more than one championship to exist. They are placed
in one document because they are *comparisons*; every fitted number behind them
is estimated per series and per class and is never pooled.

## The six populations

| series | class | races | median slope (s/lap) | median pit loss | circuits | tyre-limited | tyre premium | winners running the tank |
|---|---|---|---|---|---|---|---|---|
| WEC | HYPERCAR | 28 | +0.0139 | 76.3 s | 11 | 0 | 21.6 s | 89% |
| ELMS | LMP2 | 25 | +0.0161 | 64.8 s | 9 | 1 | 25.1 s | 100% |
| ELMS | LMP2 Pro/Am | 17 | +0.0205 | 62.2 s | 8 | 0 | 35.4 s | 94% |
| IMSA | GTP | 33 | +0.0166 | 47.6 s | 10 | 1 | 8.7 s | 64% |
| IMSA | GTD PRO | 47 | +0.0190 | 38.6 s | 13 | 2 | 16.9 s | 77% |
| IMSA | GTD | 60 | +0.0200 | 19.7 s | 15 | 5 | 17.6 s | 63% |

Sorted by pit loss, and the last three columns sort with it. That is the
synthesis.

## 1. The pit stop decides the strategy regime, not the car

The correlation between a class's median pit loss and the share of its
circuits where the optimum beats the fuel minimum is **−0.913**.

Read down the table: WEC Hypercar, at a 76-second stop, is fuel-limited
everywhere; IMSA GTD, at 20 seconds, is tyre-limited at a third of its
circuits. Every class in between falls where its stop cost puts it.

This overturned the project's own published conclusion twice. "Every measured
race is fuel-limited on stop count" was true when only prototypes were
modelled — it was a fact about **expensive stops**, stated as a fact about
endurance racing. Adding GT3 broke it; adding ELMS and GTD PRO showed the
break was not about GT3 either.

The mechanism is in
[`when_tyres_beat_fuel.md`](when_tyres_beat_fuel.md): a cheap stop is
**necessary but not sufficient**. No race above a 22.5 s pit loss is
tyre-limited anywhere in 66 circuit-classes (Mann-Whitney p = 0.00001), and
below that threshold real degradation decides (p = 0.0013). The cleanest single
illustration is Mugello 2024, where LMP2 is tyre-limited on a 9.2 s stop and
Pro/Am at the same circuit in the same year is not, on a comparable 10.8 s stop
but a shallower slope.

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
[`reports/elms/crew_rating_findings.md`](elms/crew_rating_findings.md) §6.

## 4. Slope instability is not the machinery

Degradation slopes fitted on one season routinely fail to predict another —
the within-stint R² is at or below zero almost everywhere. The obvious
candidate cause was heterogeneous, Balance-of-Performance-adjusted cars.

ELMS LMP2 is the control: one chassis, one engine, near-spec. Its slopes fail
to transfer exactly as the others do (leave-one-race-out mean R² of +0.035,
−0.001, −0.011, −0.067, −0.004 across its circuits). **The instability is not
the hardware.** Bahrain remains the only circuit anywhere in this project whose
slope genuinely transfers, and it now reads as an isolated exception rather
than the best case of a general rule.

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
