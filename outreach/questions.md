# Three questions a reviewer can actually settle

Not "what do you think" — three specific methodological decisions where I am
genuinely unsure, each with a stated position and what would change it. A person
with fifteen minutes can answer any one of them.

---

## 1. Is a paired bootstrap the right test for "GT3 transfers and prototypes do not"?

**The claim.** Leave-one-race-out within-stint R² reaches +0.573 at IMSA Lime
Rock in GTD and +0.497 in GTD PRO, against a ceiling of +0.058 for IMSA GTP and
+0.035 for ELMS LMP2. I want to say the GT3 classes transfer and the prototype
classes do not.

**What I have.** 51 circuit-classes, each scored by the same protocol. The
folds are seasons, so each circuit-class has 2–6 of them, and circuits within a
class are not independent — they share a fitted pooled slope.

**My position.** Bootstrap the *difference in mean R²* between the two groups by
resampling **circuit-classes**, not folds, because the fold is nested inside the
circuit-class and resampling folds would treat 51 clusters as ~194 observations.
Report a percentile interval on the difference.

**What I am unsure about.** Whether the small number of clusters (12 GT3,
22 prototype) makes any bootstrap interval unreliable enough that a permutation
test on the group labels would be the honest choice instead — and whether R²,
being a ratio, should be transformed before averaging across folds at all.

**What would change my mind.** A reason the cluster structure is weaker than I
think, or a standard test for this design I have not found.

---

## 2. Does the decision audit compare comparable things?

**This is the question I most want answered, because a "yes" and a "no" lead to
completely different papers.**

**The claim.** Replaying 1,280 first stops, an exact optimiser recommends
stopping a median of 12 laps later than the team did, on 80–86% of decisions in
F1 and IMSA. Two candidate explanations were tested and both failed: modelling
the undercut through a cover-aware Stackelberg engine moves the recommendation
*away* from the real stop, and the fitted slopes show no durability bias against
an independent source (median paired difference +0.0002 s/lap).

**The asymmetry I cannot rule out.** The model is asked five laps before the
real stop and offered **every remaining lap** as a candidate, optimising one
car's expected race time. A real team is choosing between a handful of laps
inside a strategy committed to earlier, under a tyre allocation and a
two-compound rule the engine does not represent, with a pit wall that will not
gamble a points finish on an expected-value argument.

**My position.** The bias is real and measured, and I do not know its cause. I
would rather publish that than a mechanism two measurements contradict.

**What I am unsure about.** Whether this comparison is meaningful at all — that
is, whether "the optimiser disagrees with the team" is a finding about
optimisers, or an artefact of asking a question no team is answering. If the
latter, the fix is to constrain the model's candidate set to what was actually
available and re-run, which changes the audit rather than the model.

**What would change my mind.** Anyone who has sat on a pit wall telling me which
constraints bind in practice and are missing here.

---

## 3. Is the 22.5 s cheap-stop threshold a sampling artefact?

**The claim.** Across 205 endurance race-seasons, no race with a pit loss above
22.5 s is ever tyre-limited — 150 races above the edge, all six classes, no
exception. The class-level correlation between median pit loss and tyre-limited
share is −0.982.

**The weakness, stated up front.** The 22.5 s edge is a **maximum set by a
single race** (IMSA GTD Indianapolis 2025). The next tyre-limited race sits at
13.2 s — a 9.3 s gap with 16 fuel-limited races inside it. An earlier version of
this work argued the threshold was trustworthy because it did not move when the
sample tripled from 66 to 205; that reasoning is wrong, because a maximum over a
growing sample can only move up.

**My position.** The *rule* (a cheap stop is necessary) is well supported. The
*constant* is not, and should be quoted as "somewhere in the low tens of
seconds" rather than as a calibrated value.

**What I am unsure about.** Whether there is a principled way to put an interval
on a threshold defined as a maximum — a bootstrap over races gives a
distribution, but of a statistic whose sampling behaviour is not
well-approximated by resampling. Extreme-value methods look like the right
family and like overkill for 25 positive cases.

**What would change my mind.** A better estimator for the boundary, or an
argument that reporting the rule without a constant is sufficient.
