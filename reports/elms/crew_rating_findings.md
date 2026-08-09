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
without any external driver-rating data. IMSA's answer was inconclusive
(+0.0040 s/lap steeper for Pro/Am, 44 matched pairs, paired Wilcoxon
p = 0.085). ELMS was scoped to provide a second, independent test on a
different car in a different championship.

**Restricted to 2023-2025 on purpose.** Before 2023 the `LMP2` label covers
every LMP2 entry, not the professional subset; pairing the full range against
Pro/Am would compare a mixed field against a pro one and call the difference a
crew effect.

## 2. The two tests disagree, and the significant one inverts the hypothesis

| test | Pro/Am − Pro slope | pairs | Pro/Am steeper in | paired Wilcoxon |
|---|---|---|---|---|
| IMSA GTD vs GTD PRO | **+0.0040** s/lap | 44 | 27 of 44 | p = 0.085 |
| ELMS LMP2 Pro/Am vs LMP2 | **−0.0143** s/lap | 17 | 5 of 17 | **p = 0.0093** |

In ELMS the **professionals** show the steeper degradation slope (median
0.0400 against 0.0201), the opposite of IMSA's direction — and it is the ELMS
test, not the IMSA one, that reaches significance.

The naive hypothesis this project set out to test was that an amateur-rated
driver wears tyres faster. It is **not merely unconfirmed: it is contradicted
where the signal is clearest.** A physically plausible reading is that a
professional extracts more from the tyre early in a stint and degrades it
faster, while an amateur runs below the limit — but that is offered as a
hypothesis, not a conclusion, because nothing here tests the mechanism.

## 3. What the p-value does not license

The ELMS result rests on per-race fits that are **individually very noisy**.
Across the 34 ELMS race-fits in this window the net slope ranges from
**−0.249 to +0.109 s/lap** against a median of 0.040, and the most negative
values are physically implausible — a tyre gaining a third of a second per lap
as it ages is a fit artefact, not a measurement. Fields are 7-14 cars, so each
race carries few clusters.

The paired Wilcoxon is still the right test: it operates on within-weekend
*differences*, which cancel the conditions common to both classes at that
event. What it supports is the **direction**, on 17 pairs. It does not support
quoting −0.0143 s/lap as the size of a crew effect, and this report does not.

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

Across two championships, **no consistent crew effect survives**. One test is
inconclusive, the other is significant in the opposite direction, and the
pit-stop comparison disagrees between series as well. The honest summary is
that the simple "amateurs degrade tyres faster" hypothesis is **not supported
by this data**, and that a real answer needs mechanism — stint-level pace
traces, driver-stint identification, and more seasons — rather than more
class-level pairs.

What the work does establish is the design. Two independent natural
experiments now exist inside this project, both like-for-like on car, BoP,
weekend and circuit, and a disagreement between them is a more useful starting
point than the single inconclusive result IMSA gave on its own.

## 6. Neutralisations: a third distinct regime

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
