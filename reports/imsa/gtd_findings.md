# IMSA GTD (GT3) — measured results

*GTD only. It shares IMSA's data source and this project's code with GTP, and
shares none of its numbers: every coefficient, posterior and constant below is
fitted on GTD alone. The two classes are never pooled, for the same reason WEC
and IMSA are never pooled — they are different cars answering a different
strategy question.*

Phase 0 for this class is in
[`reports/new_series_survey_phase0.md`](../new_series_survey_phase0.md): the
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

Median net within-stint slope **+0.0202 s/lap**, against GTP's +0.0155 on the
same circuits and the same code. Nine of 60 GTD races fit a negative slope
(GTP: 5 of 33) — tyres apparently getting faster with age, which is what a
race where fuel burn outweighs tyre wear looks like through a single net
coefficient, and is reported rather than clipped.

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
| IMSA GTP | 1 (Laguna Seca) |
| **IMSA GTD** | **5** — Indianapolis, Laguna Seca, Lime Rock, Mosport, VIR |

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

**Degradation: suggestive, and not established.** Paired on circuit *and*
season — 44 pairs where GTD and GTD PRO raced the same event in the same
year — the Pro/Am slope is steeper by a median **+0.0040 s/lap** (GTD 0.0231,
GTD PRO 0.0200), in 27 of the 44 pairs. A paired Wilcoxon test gives
**p = 0.085**.

That is not significant at the conventional level and is reported as what it
is: a difference in the expected direction that 44 pairs cannot separate from
chance. The temptation with a result like this is to call it "a trend
towards" and move on; the honest statement is that **this analysis does not
establish an amateur effect on tyre wear.** It does establish the design —
same car, same BoP, same weekends, same tracks — so the question is now
answerable with more seasons rather than merely askable.

## 7. What is not here

- **No per-decision audit.** GTP and WEC each have one; GTD does not yet.
- **No established amateur effect on degradation** — see §6. The design is in
  place and the measurement is inconclusive at 44 pairs, which is a different
  thing from an effect that is not there.
- **No Balance-of-Performance term.** BoP shifts a car's pace level and the
  per-race intercepts absorb that completely (see
  [`reports/new_series_survey_phase0.md`](../new_series_survey_phase0.md) §GT3);
  what it can also do is move the tyre-wear slope, which would show up as
  between-race slope variation and is not separately identified here.
