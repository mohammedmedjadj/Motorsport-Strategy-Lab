# IMSA GTD (GT3) — measured results

*GTD only. It shares IMSA's data source and this project's code with GTP, and
shares none of its numbers: every coefficient, posterior and constant below is
fitted on GTD alone. The two classes are never pooled, for the same reason WEC
and IMSA are never pooled — they are different cars answering a different
strategy question.*

Phase 0 for this class is in
[`reports/new_series_survey_phase0.md`](../../cross_series/new_series_survey_phase0.md): the
source verification, the eligibility scan, the circuit-alias trap and the
scope-key work that had to land before a second class could be added at all.
This document is what the models say now that it has been.

## 1. Scope

| | |
|---|---|
| Class | GTD (GT3, Pro/Am) |
| Seasons | 2021–2026 |
| Race-seasons | **60**, all of which cleared the eligibility floor |
| Circuits | **13** (16 source event strings; Canadian Tire Motorsport Park resolves to Mosport, and Watkins Glen 240 / 6 Hours to Watkins Glen — three aliases, so 16 - 3) |
| Race laps | 201,249 — more than the whole of WEC across all its classes |
| Median field | 14 cars |
| Laps kept for modelling | 73.2% (median per race) |

Every GTD race-season passed. That is unusual and worth stating plainly rather
than glossing: no race was dropped for missing flags, short distance or a thin
field. The two data traps that cost this project real work elsewhere — WEC 2021
and ELMS 2021's empty `flags` column — have no counterpart here.

## 2. Degradation

Median net within-stint slope **+0.0200 s/lap**, against GTP's +0.0166 and
GTD PRO's +0.0190 on the same circuits and the same code. 8 of 60 GTD races
fit a negative slope (GTP: 5 of 33) — tyres apparently getting faster with
age. Part of that is a race where fuel burn outweighs tyre wear seen through a
single net coefficient; part is the unmodelled track-evolution term diagnosed
in [`reports/track_evolution_omitted_variable.md`](../../cross_series/track_evolution_omitted_variable.md).
Reported rather than clipped, and every slope here read as a lower bound.

Standard errors are cluster-robust by car with a `t(G−1)` reference; with a
median 14-car field that is a `t(13)`, so the tail weight is doing real work
here rather than being a formality.

**The fuel/degradation split is not identified**, in 58 of 60 races. That
matches GTP and WEC exactly, and for the same measured reason: teams change
tyres at nearly every fuel stop, so the two regressors move together and
fitting both produces a collinear ridge rather than a measurement. Only the
net slope is reported.

## 3. The finding that changes a published conclusion

Phase 4 reported that at every scoped circuit the optimal stop count equals the
fuel minimum — tyre degradation never steep enough to buy an extra pit visit.
Adding GT3 shows that was never a fact about endurance racing. It was a fact
about **prototypes**.

| class | tyre-limited circuits |
|---|---|
| WEC HYPERCAR | none |
| ELMS LMP2 Pro/Am | none |
| IMSA GTP | 1 (Laguna Seca) |
| ELMS LMP2 | 1 (Mugello) |
| IMSA GTD PRO | 2 (Laguna Seca, VIR) |
| **IMSA GTD** | **5** — Indianapolis, Laguna Seca, Lime Rock, Mosport, VIR |

**This table is not the finding, and reading it as one is a mistake this
report made first.** Once ELMS and GTD PRO were added, the pattern resolved
into a mechanism that has nothing to do with the class: tyre-limited racing
needs a *cheap stop* (no entry above 22.5 s pit loss is tyre-limited anywhere
in 66 entries) and *real degradation*, and conditioned on stop cost the split
happens inside every class. GT3 dominates the list because GT3 racing is where
cheap stops are common. See
[`reports/when_tyres_beat_fuel.md`](../../cross_series/when_tyres_beat_fuel.md).

At Laguna Seca the GTD optimum takes **six stops against a fuel minimum of
two**. The five are the short sprint rounds, where the stop is cheap and a
heavier car on harder-worked rubber has more to gain from fresh tyres. GTD's
median measured pit loss is 19.7 s against a 39-lap fuel range — a
combination that makes stopping for tyres alone worth considering, which it
never is on a prototype's 60–80 s stop.

Read with the same caution the GTP exception carries: these are optima under a
time-only objective, on a class whose real races are also decided by
multi-class traffic and by Balance of Performance.

## 4. Pit procedure: the pooling error GT3 exposed

The tyre-change premium was measured per *series* until this class was added.
It cannot be:

| series / class | fuel-only stop | with tyre change | premium |
|---|---|---|---|
| IMSA GTP | 67.7 s | 76.5 s | **8.7 s** |
| IMSA GTD | 60.2 s | 77.8 s | **17.6 s** |
| WEC HYPERCAR | 55.7 s | 77.4 s | **21.6 s** |

GTD's premium is twice GTP's and much closer to WEC's. Pooling the two IMSA
classes would have reported roughly 14 s for the series and destroyed the
published finding that IMSA services tyres in parallel with the fuel fill
while WEC does it in sequence.

The mechanism is visible in the same table and is not a statistical artefact:
GT3's fuel-only stop is **7.5 s shorter** than the prototype's, so the tyre
service protrudes further past the end of the fill. Same rulebook, different
car, different number — which is exactly why the rulebook comparison has to be
made like class against like.

## 5. Track position

Median adjacent-swap rate **0.0388** across 16 measured circuit entries,
against the endurance range this project reports elsewhere. Position is
reconstructed from cumulative time within the class, as for every other
endurance series.

## 6. GTD PRO: the crew-rating comparison, measured

IMSA runs **GTD PRO** alongside GTD — the same GT3 cars under the same
Balance of Performance, entered with all-professional line-ups instead of
GTD's mandatory bronze- or silver-rated driver. The class boundary *is* the
crew rating, so no external rating data is needed. GTD PRO is scoped as its
own class (47 of 47 race-seasons, 2022–2026, 13 circuits, all of which GTD
also races) and is never pooled with GTD.

**Pit stops: the difference is the car, not the crew.**

| class | fuel-only stop | tyre-change premium |
|---|---|---|
| IMSA GTP (prototype) | 67.7 s | **8.7 s** |
| IMSA GTD (GT3, Pro/Am) | 60.2 s | **17.6 s** |
| IMSA GTD PRO (GT3, all-pro) | 60.2 s | **16.9 s** |

Holding the car fixed and changing only the crew moves the premium by 0.7 s;
changing the car moves it by roughly nine. The GT3-versus-prototype gap
reported in §4 is therefore a property of the machine and its service, not of
who is driving it. Same fuel-only stop to two significant figures (60.2 s in
both GT3 classes) makes the comparison as clean as this data allows.

**Degradation: significant on its face, and not robust.** Paired on the
*race* — 44 pairs where GTD and GTD PRO ran the same event in the same season
— the Pro/Am slope is steeper by a median **+0.0040 s/lap** (paired medians:
GTD 0.0226, GTD PRO 0.0193), in 28 of the 44 pairs. A paired Wilcoxon test
gives **p = 0.032**.

Pairing on the race rather than the circuit matters here: IMSA ran two
distinct races at Watkins Glen in 2021, and a circuit-keyed pairing averages
them into a single pair without saying so.

Read alone, p = 0.032 licenses "amateur-rated crews degrade tyres faster in
IMSA". It does not survive being asked twice. `robustness()` in
`src/degradation/crew_rating.py` re-runs the test under three defensible
variations and **all three put it back above 0.05**: a sign test, which drops
magnitudes so no single large pair can carry the result, gives p = 0.096;
dropping the still-in-progress 2026 season gives p = 0.094; restricting to the
37 pairs where both classes fit a positive slope — excluding races hit by the
[unmodelled track-evolution
term](../../cross_series/track_evolution_omitted_variable.md) — gives p = 0.054.

And the second natural experiment points the other way: **ELMS's LMP2 Pro/Am
crews degrade −0.0053 s/lap *less* than its professionals** (17 pairs,
p = 0.148). See [`reports/elms/crew_rating_findings.md`](../../elms/crew_rating_findings.md).

So the honest statement is unchanged from what this section said before the
numbers were recomputed, even though every number in it moved: **this analysis
does not establish an amateur effect on tyre wear.** What it does establish is
the design — same car, same BoP, same weekends, same tracks — so the question
is answerable with more seasons rather than merely askable.

Both tests and their robustness variants are computed by
`src/degradation/crew_rating.py` and pinned by `tests/test_crew_rating.py`.
Until that module existed the comparison was run by hand and its published
p-values had drifted a long way from the artifacts; the post-mortem is in
[`reports/elms/crew_rating_findings.md`](../../elms/crew_rating_findings.md) §6.

## 7. What is not here

- **Per-decision audit: now present** for both GT3 classes
  ([`gt3_audit_cases.md`](audit_cases.md)), on the two circuits the
  cross-series rule marks tyre-limited.
- **No established amateur effect on degradation** — see §6. The design is in
  place and the measurement is inconclusive at 44 pairs, which is a different
  thing from an effect that is not there.
- **No Balance-of-Performance term.** BoP shifts a car's pace level and the
  per-race intercepts absorb that completely (see
  [`reports/new_series_survey_phase0.md`](../../cross_series/new_series_survey_phase0.md) §GT3);
  what it can also do is move the tyre-wear slope, which would show up as
  between-race slope variation and is not separately identified here.
