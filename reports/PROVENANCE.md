# Who decided what

This project was built with an AI coding assistant. That is worth saying plainly
rather than leaving to be inferred from a commit rate, and it makes the question
of who decided what a real one. This file answers it as precisely as the record
allows.

The rule used here: a decision is attributed to the project owner only where a
specific instruction can be pointed to, and where the consequence is visible in
the repository. Everything else is attributed to the assistant, including work
the owner would probably have approved. A short true list is worth more than a
long generous one.

## Decisions the owner made

**Every scope expansion in the project came from the owner, and two of them
destroyed published conclusions.**

*Formula 1 from four circuits to the full calendar.* The project began with four
"core" circuits. The owner rejected that — every circuit that can be worked
should be worked to the same standard — which took F1 from 4 circuits to 26 and
the endurance multi-stop layer from 65 race-seasons to 205. That expansion is
what moved the pit-loss correlation from −0.913 to −0.982 and what made the
22.5 s edge testable at all. It also destroyed a headline: "no measured
endurance race is tyre-limited" had been published twice, was true of the
expensive-stop classes it was measured on, and turned out false the moment the
cheap-stop classes entered scope. 25 of 205 race-seasons are tyre-limited.

*Audit every series, not just F1.* The owner asked why the decision audit existed
only for Formula 1. It now covers 1,280 decisions across four championships, and
the endurance half is where the finding that the gap tracks the caution rate
came from.

*Classes are never pooled.* The owner's standing instruction is that WEC and
IMSA never share a report, extended to every class. That is why there are seven
sets of coefficients rather than four, and it is load-bearing rather than
fastidious: IMSA GTP and GTD run the same rounds and disagree on the project's
headline endurance conclusion. Pooling would have averaged the disagreement
away, and did, for a while.

**Standards of evidence the owner set:**

*A result about one Grand Prix is worthless.* The owner rejected a README whose
key results were single-race findings. Everything headline in the project is now
calendar-wide or cross-series.

*The README is a presentation, not a changelog of corrections.* The owner
rejected a version that had turned into a list of the assistant's own fixes.
Corrections now live in the reports where they belong, and only where they led
somewhere.

*Rigour is the price of entry, not the value.* The owner's correction —
"if this project is useless then it is useless" — is what redirected the work
from more modelling to publication, validation and external review. The paper,
the site, the outreach pack and the DOI route all follow from it.

*The figure comparison rule.* The owner's rule — do not compare classes on
performance, compare like with like, and distinguish classes even in a
four-series figure — was applied to all nine figures and **found two that broke
it**. Fixing `r3_audit_bias` split IMSA's pooled +12 into GTP +9, GTD +12 and
GTD PRO +13, and moved the baseline headline from "three championships out of
four" to "five of the seven classes". Nothing else had caught that.

**Working method the owner imposed:** phase gates with explicit stop points
through phases 0–7; write the handover before compacting context; report at
block boundaries; and a rule about prose rhythm that this file is written under.

## Errors the owner caught

Each of these was raised by the owner before the assistant found it, and each
led to a change in the repository.

- Reports and figures left stale after the code beneath them moved.
- The four-circuit scope being too narrow to support the claims made on it.
- The README drifting into a changelog.
- A checkbox table that read as machine output rather than as writing.
- Two specific figure defects: extreme values crushing the readable range in
  `s3_f1_degradation`, and an annotation sitting on top of the data in
  `s2_pit_loss_spectrum`. Both are fixed and the fix is described in
  [`figures/README.md`](figures/README.md).
- Circuit names appearing as raw slugs in published figures.
- Asking whether the Streamlit demo actually worked, and whether the post-race
  refresh actually ran. The honest answers — it does, and the refresh cannot
  reach the timing API from GitHub's runners — are both now written down.

## Errors the assistant found

For contrast, and because the distinction matters if anyone asks. These came
from the assistant reading artifacts, not from the owner:

The FastF1 event-substitution bug and its guard; a drift check blind to
untracked files, which had allowed three weeks of silent staleness; a report
attributing a model's own P(best) to a team's decision; a weather layer
requesting a 24-hour UTC slice instead of the local race day, which changed 28%
of the precipitation totals; a join matching slugs against display names, which
silently dropped a third of the endurance audit; a report naming the wrong
circuit as its least trustworthy; and a sweep of 72 numbers typed into report
prose, four of which had gone stale.

## What this means for how the project should be described

The defensible claim is not that the owner wrote the code. It is that the owner
set the scope, set the standards of evidence, held the phase gates, and caught
the presentational and methodological failures — and that in at least three
cases an instruction from the owner directly destroyed a conclusion the project
had already published.

That last part is the unusual one. Deciding to widen a scope that then refutes
your own headline result is a research judgement, and it is visible in this
repository three times over.
