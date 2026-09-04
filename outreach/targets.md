# Targets, and how to find the right person

**No names are listed here on purpose.** I can describe categories and how to
identify the right person in each, but I will not invent an individual's name,
role or email — a cold email addressed to someone who does not hold the job you
think they hold is worse than sending nothing, and it is the one error in this
whole plan that cannot be undone. Fill this in yourself from sources you can
see, and write the verified name straight into the table.

| # | Category | Who exactly | Variant | Verified name | Sent | Reply |
|---|---|---|---|---|---|---|
| 1 | Paper author | | A | | | |
| 2 | Paper author | | A | | | |
| 3 | Paper author | | A | | | |
| 4 | Academic, sports analytics | | C | | | |
| 5 | Academic, operations research | | C | | | |
| 6 | Race engineer / strategist | | B | | | |
| 7 | Race engineer / strategist | | B | | | |
| 8 | Race engineer / strategist | | B | | | |

---

## Category 1 — authors of the papers you cite

**The highest-response category by a wide margin**, because you are asking
someone a precise question about their own work, which is the one email
academics reliably answer.

**Before you can use this category you have to do the literature review**, and
it is a blocking dependency for the paper as well as for these emails. The
project's README currently compares itself to *public notebooks*. Formal
research exists and a reviewer who sees it missing stops reading — this is the
single most likely reason a submission gets rejected without review.

Search, and record what you actually find:

| where | query |
|---|---|
| Google Scholar | `"pit stop" strategy optimization dynamic programming motorsport` |
| Google Scholar | `Formula 1 tyre degradation model machine learning` |
| Google Scholar | `endurance racing strategy simulation Monte Carlo` |
| arXiv | `cat:cs.LG AND (abs:"formula 1" OR abs:"motorsport")` |
| arXiv | `abs:"race strategy" AND abs:"reinforcement learning"` |
| Semantic Scholar | follow the citation graph out from anything you find |

For each paper record: exact title, authors, venue, year, DOI, **what it does
that this project does not, and what this project does that it does not.**
That last column is the literature review, and it is also section 1 of the
paper.

> There is a list of five candidate papers in my planning notes — an EJOR 2024
> Stackelberg/DP paper, a Frontiers in AI 2025 deep-learning paper, a
> driver-versus-car paper, an arXiv real-time Monte Carlo system, and an arXiv
> RL-with-energy-management paper. **Treat every one of those as unverified.**
> I have not checked a single title, author or venue against a real publication
> record in this session, and a citation that turns out not to exist would do
> more damage to your application than the missing literature review does. Look
> each one up before it goes anywhere near an email or a bibliography.

## Category 2 — academics in sports analytics and operations research

French universities are worth trying first: you can write in French, the
geographic connection is real, and a student email from your own country gets
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

**Approach them after the DOI exists**, not before — a link to a citable
deposited paper changes how the message reads.

---

## Sequencing

1. **Literature review first.** It gates the Variant A emails, the paper's
   section 1, and your credibility with categories 1 and 2.
2. **Categories 1 and 2 next**, while the paper is being written — a methods
   answer is only useful before you have finalised the methods.
3. **Category 3 after the Zenodo DOI.**

## Rules

- One variant per person, personalised. A visible mass mailing ends it.
- One follow-up after two weeks, then stop.
- Log every send and every reply in the table above. A record of ten serious
  attempts with two replies is itself a real thing you did.
- Never overstate what this is. "A secondary-school student who built this on
  public data and would like a methods opinion" is accurate, and it is a far
  better hook than any inflated title.
