# Three contact variants

Short on purpose. A cold email that runs past twelve lines gets skimmed and
archived; the one-pager and the questions do the work once someone replies.

**Every `[…]` is a placeholder you must fill with something you have actually
verified.** A cold email that gets a detail wrong about the recipient's own work
is worse than no email. Do not send a variant with a placeholder still in it,
and do not let me or anyone else write the specific detail for you — the whole
value of that sentence is that it proves you read the thing.

---

## Variant A — a researcher whose paper you have read

> **Subject:** Question on cross-championship transfer of tyre-degradation models
>
> Dear Dr [surname],
>
> I'm a secondary-school student in [place] and I've spent the past [n] months
> building an open cross-championship study of race strategy — F1, WEC, IMSA and
> ELMS, seven car classes, one protocol applied identically to all of them.
>
> I read [exact title], and [one specific sentence about what that paper does
> that bears on your work — a method you reused, an assumption you tested, a
> result yours disagrees with]. That is what made me want to ask you something
> rather than just cite you.
>
> My difficulty is question 2 in the attached page: I replay 1,280 real
> first-stop decisions against an exact optimiser, it recommends stopping a
> median of 12 laps later than the teams did, and the two explanations I
> proposed both failed when I tested them. I can't tell whether that's a finding
> about optimisers or an artefact of asking a question no team is answering.
>
> One page of results and three questions are attached; the code and data are at
> [repo link]. If any of the three is quick for you to answer I'd be very
> grateful, and if none is, that's a useful answer too.
>
> With thanks,
> [name]

## Variant B — a race engineer or strategist

> **Subject:** A model that stops 12 laps too late — what am I missing?
>
> Dear [name],
>
> I'm a secondary-school student who built a race-strategy model across F1, WEC,
> IMSA and ELMS from public timing data, then did something I haven't seen done:
> replayed **1,280 real first-stop decisions** and compared what the model would
> have called to what teams actually did.
>
> The model stops later than the pit wall on 80–86% of them, by a median of 12
> laps. I tested the two explanations I could think of — no track position, and
> slopes that make tyres look too durable — and both failed.
>
> My suspicion is that the comparison itself is unfair: the model sees every
> remaining lap and optimises one car's expected race time, while you're
> choosing between a handful of laps inside a plan you already committed to,
> with a tyre allocation and a rulebook it doesn't represent.
>
> **Which constraints actually bind on your pit wall that a model like this
> would miss?** That single answer would be worth more to me than another month
> of work. One page attached; nothing confidential is being asked for and
> nothing you say would be published without your agreement.
>
> With thanks,
> [name]

## Variant C — an academic in sports analytics or operations research

> **Subject:** Student project — cross-series validation, seeking a methods opinion
>
> Dear Professor [surname],
>
> I'm a secondary-school student in [place]. Over the past [n] months I've built
> an open study of race-strategy models across four championships and seven car
> classes, applying one protocol to all of them. Two of its three results are
> negative, which is why I'd value an outside opinion before writing it up.
>
> The methodological question I'm least sure of is the first in the attached
> page: I want to claim that GT3 degradation slopes transfer across seasons and
> prototype slopes do not, from leave-one-race-out R² across 51 circuit-classes
> with 2–6 folds each and clustering at the circuit-class level. I think a
> paired bootstrap resampling clusters is right and a permutation test may be
> more honest at this cluster count.
>
> I'm not asking for supervision — one paragraph on whether that design is
> defensible would already help. One page of results, three questions, and the
> full code and data at [repo link].
>
> With thanks,
> [name]

---

## Before you send anything

- [ ] Every `[…]` replaced with something verified.
- [ ] `outreach/one_pager.md` exported to PDF and attached — do not paste it
      into the body.
- [ ] The repository link works from a signed-out browser.
- [ ] The paper you cite in Variant A: title, authors and venue checked against
      the actual publication, not from memory or from a summary.
- [ ] Send one variant per person. Sending the same mail to a list is visible
      and it ends the conversation before it starts.
