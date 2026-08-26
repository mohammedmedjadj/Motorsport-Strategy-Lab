# ELMS — the crew-rating question, and why two championships disagree

*ELMS only. It shares its source and this project's code with WEC and IMSA and
shares no fitted number with either.*

Scope and the two data traps are in
[`data_availability_phase0.md`](data_availability_phase0.md). This document is
the result the scoping decision was made to obtain.

## 1. Why this test exists

Both ELMS and IMSA run the same car in two classes that differ **only** in
whether an amateur-rated driver is mandatory:

| championship | professional class | Pro/Am class | car |
|---|---|---|---|
| IMSA | GTD PRO | GTD | GT3, same BoP |
| ELMS | LMP2 (2023+) | LMP2 Pro/Am | Oreca 07, near-spec |

The class boundary *is* the crew rating, so the amateur effect is measurable
without any external driver-rating data. IMSA's answer, on 44 matched pairs,
was **+0.0040 s/lap** steeper for Pro/Am. ELMS was scoped to provide a second,
independent test on a different car in a different championship.

Both tests are computed by `src/degradation/crew_rating.py` and pinned by
`tests/test_crew_rating.py`. That is not incidental to the result: an earlier
version of this document quoted numbers produced by hand, the slopes beneath
them were corrected twice, and nothing recomputed them. §6 records what that
cost.

**Restricted to 2023-2025 on purpose.** Before 2023 the `LMP2` label covers
every LMP2 entry, not the professional subset; pairing the full range against
Pro/Am would compare a mixed field against a pro one and call the difference a
crew effect.

## 2. The two tests disagree in sign, and neither is robust

| test | Pro/Am − Pro slope | pairs | Pro/Am steeper in | paired Wilcoxon |
|---|---|---|---|---|
| IMSA GTD vs GTD PRO | **+0.0040** s/lap | 44 | 28 of 44 | p = 0.032 |
| ELMS LMP2 Pro/Am vs LMP2 | **−0.0053** s/lap | 17 | 5 of 17 | p = 0.148 |

They point in opposite directions. In IMSA the amateur-rated crews degrade
faster, as the naive hypothesis predicts; in ELMS the **professionals** do
(paired medians 0.0249 against 0.0205), which it does not.

IMSA's is the only one of the two below the conventional 5% line, and §3
shows it does not stay there under any of three defensible variations of the
analysis. So the honest reading is not "amateurs degrade tyres faster, shown
in IMSA and not yet in ELMS". It is that **two natural experiments of the same
design disagree in sign, and neither carries an effect that survives its own
robustness checks.**

A physically plausible story exists for either direction — an amateur
overworking the tyre, or a professional extracting more from it early in a
stint and paying for it later. Nothing here tests a mechanism, so neither
story is offered as more than that.

## 3. Neither p-value survives its own robustness checks

Both results rest on per-race fits that are **individually very noisy**.
Across the 34 ELMS race-fits in this window the net slope ranges from
**−0.298 to +0.083 s/lap** against a median of +0.024, and the most negative
values are physically implausible — a tyre gaining a third of a second per lap
as it ages is a fit artefact of the unmodelled track-evolution term, not a
measurement. Fields are 7-14 cars, so each race carries few clusters.

The paired Wilcoxon is the right test regardless: it operates on within-weekend
*differences*, which cancel the conditions common to both classes at that
event. But a p-value of 0.032 on data this noisy needs to be asked whether it
is load-bearing, so `robustness()` re-runs each test under three variations,
none of them a strawman:

| variation | IMSA | ELMS |
|---|---|---|
| **headline** (paired Wilcoxon) | n = 44, **p = 0.032** | n = 17, p = 0.148 |
| sign test — direction only, so no single large pair carries it | n = 44, p = 0.096 | n = 17, p = 0.144 |
| latest season dropped | n = 39, p = 0.094 | n = 11, p = 0.160 |
| races with both slopes positive — excludes the known model defect | n = 37, p = 0.054 | n = 11, p = 0.375 |

**Every variation puts IMSA back above 0.05,** and the closest one — 0.054 —
still fails at the line the headline cleared. A result that appears and
disappears depending on which defensible analysis you ran first is a statement
about statistical power, not about tyres.

This does not support quoting either +0.0040 or −0.0053 s/lap as the size of a
crew effect, and this report does not.

## 4. Pit stops disagree between championships too

| series / class | fuel-only stop | tyre-change premium |
|---|---|---|
| IMSA GTD (Pro/Am) | 60.2 s | 17.6 s |
| IMSA GTD PRO (all-pro) | 60.2 s | 16.9 s |
| ELMS LMP2 (pro) | 44.4 s | 25.1 s |
| ELMS LMP2 Pro/Am | 35.2 s | 35.4 s |

IMSA shows essentially no crew effect at the stop (0.7 s). ELMS shows a large
apparent one (10.3 s) — but its fuel-only stops also differ by 9.2 s between
the two classes, which is not something a driver rating should change, and the
Pro/Am cell rests on 79 fuel-only stops. That pattern looks more like a
difference in stop *procedure or sample* than a crew effect, and it is
reported as unexplained rather than as a finding.

## 5. The conclusion this actually supports

Across two championships, **no consistent crew effect survives**. The two
tests disagree in sign, the one that clears 5% does not stay there under any
robustness check, and the pit-stop comparison disagrees between series as
well. The honest summary is that the simple "amateurs degrade tyres faster"
hypothesis is **not supported by this data**, and that a real answer needs
mechanism — stint-level pace traces, driver-stint identification, and more
seasons — rather than more class-level pairs.

What the work does establish is the design. Two independent natural
experiments now exist inside this project, both like-for-like on car, BoP,
weekend and circuit, and a disagreement between them is a more useful starting
point than the single inconclusive result IMSA gave on its own.

## 6. What this document got wrong, and why it could

The table in §2 previously read **IMSA p = 0.085, ELMS p = 0.0093**, with the
ELMS difference at −0.0143 s/lap. Every one of those numbers is wrong, and the
conclusion drawn from them — "the significant test contradicts the hypothesis"
— pointed at the wrong championship. The two series have since **swapped**
which one clears 5%.

Nothing about the data changed underneath in a suspicious way. The slopes were
corrected twice, for good reasons documented elsewhere: the traffic trim was
found to be [selecting on the dependent
variable](degradation_phase2.md) and cutting up to 25% of the measured slope,
and a field-wide neutralisation ramp was leaking into the fits until a
hysteresis filter caught it. Both corrections were right. Both moved every
slope in this table.

**The defect was that this comparison had no code.** It was computed once, by
hand, and written into prose. Prose does not get recomputed when its inputs
change, and no test could pin a number that nothing produced — so the reports
drifted away from the artifacts silently, and stayed there across several
regenerations that would otherwise have caught it.

The fix is `src/degradation/crew_rating.py`, which computes both tests and
their robustness variants from `endurance_degradation_fits.csv`, and
`tests/test_crew_rating.py`, which fails if any document in this repository —
including the README — quotes a crew p-value the code does not produce.

The lesson generalises past this file, and it is the one worth keeping: in
this project, **a published finding with no committed code behind it cannot
become stale, only quietly wrong.** Staleness is visible on regeneration;
being quietly wrong is not.

## 7. Neutralisations: a third distinct regime

Ingesting ELMS's race-control flags added a third neutralisation profile,
distinct from both series already modelled:

| series | races with ≥1 FCY | races with ≥1 SC | SC rate/lap |
|---|---|---|---|
| IMSA | 61 of 63 | **0 of 63** | 0.00004 (prior floor) |
| WEC | 9 of 33 | 19 of 33 | 0.00605 |
| **ELMS** | 15 of 29 | **23 of 29** | **0.01592** |

ELMS is more Safety-Car-dominated than WEC, which is itself more so than IMSA
— which sees none at all. Three series, three regimes, and the same conclusion
each time: a pooled "endurance" neutralisation model would describe none of
them.
