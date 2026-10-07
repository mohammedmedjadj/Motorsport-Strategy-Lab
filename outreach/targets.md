# Who to contact

**No names are listed until they are verified.** A cold email addressed to
someone who does not hold the job I think they hold is worse than sending
nothing, and it is the one error in this whole plan that cannot be undone. A
name goes into the table only once I have seen it on a source I can point to.

| # | Category | Who exactly | Variant | Verified name | Sent | Reply |
|---|---|---|---|---|---|---|
| 1 | Paper author | TU Eindhoven, electric endurance strategy | A | Jorn van Kampen | | **replied 25 Sep 2026** |
| 2 | Paper author | TU Eindhoven, competitor-aware endurance (arXiv:2603.28286) | A | Wytze de Vries | | **replied 25 Sep 2026** — asked for a page on the pit-loss correlation with the data behind it |
| 3 | Paper author | Universidad de Chile, Stackelberg pit-stop DP (EJOR 319(3):908-919) | A | Charles Thraves | | **replied three times** — rival-selection defect, then a selection criterion, then its own endogeneity |
| 4 | Academic, sports analytics | | C | | | |
| 5 | Academic, operations research | | C | | | |
| 6 | Race engineer / strategist | | B | | | |
| 7 | Race engineer / strategist | | B | | | |
| 8 | Race engineer / strategist | | B | | | |

---

## Category 1 — authors of the papers I cite

The highest-response category by a wide margin. The email asks someone a
precise question about their own work, which is the one email academics
reliably answer.

**The literature review is done.** Sixteen papers, each verified against a real
publication record, are in
[`../reports/cross_series/related_work.md`](../reports/cross_series/related_work.md),
and thirteen entries are in the paper's bibliography. Nothing blocks these
emails any more.

The four worth writing to first, and why:

**Cole Cappello and Andrew Hoegh** (*Journal of Sports Analytics* 12, 2026;
preprint arXiv:2512.00640) are the closest to this work on both data and method
— Bayesian state-space tyre degradation from FastF1. Cite the journal version,
not the preprint: the preprint evaluates one race, the published paper holds out
19 sessions of the 2025 season by rolling-origin cross-validation, and getting
that wrong in the first paragraph would end the exchange. They are the only
authors in the review who validate a tyre model out of sample, which makes them
the right people to ask question 1 — whether a cluster bootstrap resampling
circuit-classes is the right test.

**Felipe Aguad and Charles Thraves** (EJOR 319(3):908–919) wrote the Stackelberg
dynamic-programming treatment your adversarial component reuses. Thraves also
co-wrote the CEJOR dynamic programme with Oscar Carrasco Heine. Ask them question
2 — whether replaying real decisions against an optimiser compares comparable
things — since their game formulation has no occasion to check it and they will
have an opinion.

**Alexander Heilmeier's group at TUM** built the race simulation most of this
field rests on, and released the code. Three papers between 2018 and 2020. They
are the people most likely to have hit the same transfer problem and decided not
to write about it.

**Juan S. Santillana** (arXiv:2607.06495) deployed a calibrated Monte Carlo
engine live at two Grands Prix. Different question from yours, but the only
person in this list who has had to defend a strategy model to people watching a
race in real time.

Everyone above is reachable by the address on their paper.

## Category 2 — academics in sports analytics and operations research

French universities are worth trying first: I can write in French, the
geographic connection is real, and a student email from the same country gets
read. Look for research groups in operations research, decision science or
sports analytics, and for anyone publishing on scheduling or stochastic
optimisation who might find the audit interesting on methodological grounds even
without caring about racing.

Also worth trying: authors of any motorsport-adjacent paper in
*Journal of Quantitative Analysis in Sports* or *Journal of Sports Analytics*.

## Category 3 — race engineers and strategists

**Different value from the other two.** They will not review your statistics,
but they can answer question 2 — the one about whether the audit compares
comparable things — and nobody else can. One paragraph from someone who has run
a pit wall is worth more than any amount of further modelling.

Where to look: LinkedIn, filtered on strategy and race-engineering roles at the
manufacturer and customer teams in the four series this project covers. Sports
engineering and motorsport-engineering degree programmes also have alumni in
these roles who answer student mail more readily than serving engineers at a
works team.

**The DOI exists** — [10.5281/zenodo.22726130](https://doi.org/10.5281/zenodo.22726130) — so this category
is open. A link to a citable, archived deposit changes how the message reads
to someone who gets a lot of student mail.

---

## Sequencing

1. **Categories 1 and 2 now.** The literature review is done and the paper's
   related-work section is written, so these are unblocked. A methods answer is
   only useful before the methods are finalised, which is where the project is
   today.
2. **Category 3, also now.** The Zenodo deposit this was waiting on is live at
   [10.5281/zenodo.22726130](https://doi.org/10.5281/zenodo.22726130), archived onward into Software
   Heritage and OpenAIRE. A link to a citable deposit changes how the message
   reads to someone on a pit wall.

## Open thread — de Vries, 25 September

He asked for one page on Result 2 with the correlation data, not the project
one-pager. [`pit_loss_rule_brief.pdf`](pit_loss_rule_brief.pdf) is that page:
the question, how pit loss and tyre-limited status are measured in enough
detail to be judged, the class table with the interval, the figure, and the two
places the evidence is thin. It ends on the question I want answered — whether
a correlation over six class summaries is the right statistic, or whether this
should be a per-race model with pit loss as a covariate.

Regenerate it with `python scripts/make_outreach_brief.py` before sending if
any artifact has moved. Every number on the page is read from the artifacts at
build time, so a stale copy cannot survive a rebuild.

His own paper is the closest published work to the adversarial component here,
and it is endurance rather than Formula 1. Row 15 of
[`../reports/cross_series/related_work.md`](../reports/cross_series/related_work.md)
says what it does and what it does not.

## Open thread — Thraves, three replies

The most productive correspondence on this project so far, and the only one
that has reached the paper's method rather than its presentation.

**First reply: a defect.** `_nearest_rival` in
`scripts/run_undercut_hypothesis.py` picks the rival by minimising absolute
classified-position distance, so it chooses the car ahead on some decisions and
the car behind on others while the audited car always commits first. Those are
different games. With equidistant neighbours the choice falls to row order, and
271 of 357 decisions turned out to be exactly that. The replay was stratified
rather than rewritten, and the published result was left alone; see the added
section in [`../reports/f1/undercut_hypothesis.md`](../reports/f1/undercut_hypothesis.md).

**Second reply: the second-order effect.** He confirmed that lap-time
differences from compound and tyre age are enough to move the relative timing,
so a selection rule cannot work on raw pace alone.

**Third reply: a criterion, and its limit.** Estimate for each car the total
race time it would set under its own optimal strategy with no competition, and
take as rival the car whose estimated time is closest. Implemented in
`scripts/run_rival_selection.py` and compared against three other rules in
[`../reports/f1/rival_selection.md`](../reports/f1/rival_selection.md).

He named the limit himself: at the extreme the choice of rival is endogenous,
since each car's strategy depends on the others. That is written into the
paper as a declared limitation rather than left out, because it is the kind of
reservation that disappears quietly when it is inconvenient.

## Rules

- One variant per person, personalised. A visible mass mailing ends it.
- One follow-up after two weeks, then stop.
- Log every send and every reply in the table above. A record of ten serious
  attempts with two replies is itself a real piece of work.
- Never overstate what this is. "A secondary-school student who built this on
  public data and would like a methods opinion" is accurate, and it is a far
  better hook than any inflated title.
