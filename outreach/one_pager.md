# Does a tyre-degradation model transfer?

**What public timing cannot identify, and what teams' pit stops reveal.**

Motorsport Strategy Lab — Formula 1, WEC, IMSA and ELMS, seven car classes,
one protocol applied identically to all of them.

Repository: <https://github.com/mohammedmedjadj/Motorsport-Strategy-Lab>  
Archived and citable: [10.5281/zenodo.22726130](https://doi.org/10.5281/zenodo.22726130) (Zenodo, Software Heritage, OpenAIRE)

---

## The problem

Race-strategy models are published per championship and validated on the
championship they were fitted to. Two questions that follow are rarely asked:
does a fitted model transfer to a season it has never seen, and does its
recommendation resemble what a professional team actually did?

This project answers both on the same data, with the same code, across four
championships, and reports what came back, including what it could not measure.

---

## R1 — Transfer is mostly not measurable from public timing, and slopes move

Leave one season out: fit the degradation slope on every other season of a
circuit, predict the held-out one, score the within-stint R². Of **51 endurance
circuit-classes, 5 clear 0.2**; in Formula 1, 3 of 22 circuits do.

The reason is physical. Inside a stint the car burns fuel as the tyre wears, and
in Formula 1 the two nearly cancel (−0.053 s/lap of fuel against +0.040 of wear),
so the shape a stint shows is tiny against 0.67 s of lap noise. Rebuilt with a
slope stable by construction, **16 of 22 F1 circuits and 43 of 50 endurance
circuit-classes still could not reach 0.2.** Measured directly as a variance
component, the slope does move between races, by about a third of its mean,
whether compounds are coded by label or by the real Pirelli rubber.

The raw GT3-over-prototype difference (+0.164) falls to +0.035 [−0.005, +0.085]
paired within the events that run both: a difference between circuits, not car
types.

*Figures: `reports/figures/r1_transfer.png`, `reports/figures/r1_ceiling.png`*

## R2 — Held to the team's strategy, the planner agrees, and the agreement comes from the horizon

Every first stop is replayed: the model is asked 5 laps before the real stop,
given the state as it was. Run to the flag, it stops +10 laps later than F1
teams, because it plans a second stint the team never ran. **Given each team's
own next stop, the gap is +2 laps [+1, +4] over 352 F1 decisions, +3 [+2, +4]
out of sample**, and every endurance interval contains zero.

But a rule with no fitted quantity, balancing tyre age before the team's next
stop, ties the full Monte Carlo engine in 7 of 7 classes. The agreement is a
property of the question, not of the model.

*Figure: `reports/figures/r3_audit_bias.png`*

## R3 — The stops carry the compound difference the fit misses

Inverting the time-optimal stop at the lap each team chose gives the wear ratio
that would have made it optimal, which is a ratio of stint lengths and uses no
fitted slope. **To a harder compound it is 0.73 [0.68, 0.77]; to a softer one,
1.74 [1.43, 2.53]**, on the side hardness predicts for 79% of decisions, against
48% for the fitted slopes. Teams act as if they know which compound lasts, and
public timing does not resolve it.

## A note on the endurance planner

Across 205 race-seasons the class-level correlation between median pit loss and
the tyre-limited share is **r = −0.982** on six class points, and no race-season
above a 22.5 s pit loss is tyre-limited. The regime is decided inside the
planner, so this is a description of where these championships sit, not a
mechanism.

*Figure: `reports/figures/r2_pit_loss_rule.png`*

---

## What underwrites it

No fabricated data anywhere: every quantity is measured from published timing,
or absent. Cluster-robust standard errors throughout. Two estimators built,
validated on synthetic races, and **withdrawn** when they failed on real fields.
Every published headline number is recomputed from its committed artifact by
`tests/test_paper_claims.py`, and a CI job regenerates the deterministic
artifacts and fails on any diff.
