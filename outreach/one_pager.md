# Does a tyre-degradation model transfer?

**Cross-championship evidence and a retrospective audit of 1,280 real pit-stop
decisions.**

Motorsport Strategy Lab — Formula 1, WEC, IMSA and ELMS, seven car classes,
one protocol applied identically to all of them.
Repository: <https://github.com/mohammedmedjadj/motorsport-strategy-lab>

---

## The problem

Race-strategy models are published per championship and validated on the
championship they were fitted to. Two questions that follow are rarely asked:
does a fitted model transfer to a season it has never seen, and does its
recommendation resemble what a professional team actually did?

This project answers both on the same data, with the same code, across four
championships — including two negative results.

---

## R1 — Transfer is a property of the circuit-class, not the championship

Leave-one-race-out: fit the degradation slope on every season of a circuit but
one, predict the held-out season, score within-stint R².

| | best transfer | class ceiling |
|---|---|---|
| IMSA GTD (GT3) | Lime Rock **+0.573** | — |
| IMSA GTD PRO (GT3) | Lime Rock **+0.497** | — |
| WEC Hypercar | Bahrain +0.217 | +0.217 |
| IMSA GTP | Laguna Seca +0.058 | **+0.058** |
| ELMS LMP2 | Barcelona +0.035 | **+0.035** |

Of **51 circuit-classes measured, 5 clear R² = 0.2.** Everywhere else a slope
fitted on past seasons predicts the next one no better than its own mean.

The obvious explanation — heterogeneous, Balance-of-Performance-adjusted GT3
fields — is refuted by the control: **ELMS LMP2 is near-spec** (one chassis, one
engine, no BoP) and transfers no better than anything else. The instability is
not the machinery. Where transfer does happen it tracks short circuits with
cheap stops, which is the same axis R2 turns on.

*Figure: `reports/figures/r1_transfer.png`*

## R2 — The cost of the stop, not the car, sets the strategy regime

An exact dynamic program plans every endurance race under a hard fuel
constraint, and reports whether the tyre-optimal plan needs more stops than the
fuel minimum.

Across **205 race-seasons**, the share of tyre-limited races against the class's
median pit loss: **r = −0.982**, monotonic across all six classes with no
inversion (IMSA GTD 24 s → 26% ... WEC Hypercar 74 s → 0%).

At race level: **150 of 205 race-seasons have a pit loss above 22.5 s and not
one of them is tyre-limited**, across all six classes (Mann-Whitney
p = 1.1 × 10⁻¹⁴).

*Stated with its weakness:* the 22.5 s edge is a maximum set by a single race;
the next tyre-limited race sits at 13.2 s. The rule is robust, the constant is
not — see question 3.

*Figure: `reports/figures/r2_pit_loss_rule.png`*

## R3 — An exact optimiser stops later than teams do, and both explanations fail

Every first stop is replayed: the model is asked 5 laps before the real stop,
given the state as it actually was, and its recommended lap compared to the
team's.

| series | decisions | median Δ | stops later |
|---|---|---|---|
| IMSA | 632 | **+12** | 86% |
| F1 | 357 | +10 | 80% |
| ELMS | 171 | +2 | 68% |
| WEC | 120 | +1 | 54% |

**1,280 decisions.** In endurance the gap tracks the caution rate; in F1 it does
not — the bias is present on green-flag stops too.

Two candidate explanations were named in the report, then tested:

1. **No track position**, so the engine can never pay for an undercut.
   *Rejected.* Re-running all 357 F1 decisions through a cover-aware
   Stackelberg engine moves the recommendation **away** from the real stop.
2. **Slopes biased toward durability.** *Not detected.* Against an independent
   source separating tyre wear from fuel burn by a different method, the median
   paired difference is +0.0002 s/lap — an error that size moves a stop by
   several race distances, not twelve laps.

**The result stands as measured and unexplained.** That is the honest position,
and it is the finding this project would most like a second opinion on.

*Figure: `reports/figures/r3_audit_bias.png`*

---

## What underwrites it

No fabricated data anywhere: every quantity is measured from published timing,
or absent. Cluster-robust standard errors throughout. Two estimators built,
validated on synthetic races, and **withdrawn** when they failed on real fields.
Every published headline number is recomputed from its committed artifact by
`tests/test_paper_claims.py`, and a CI job regenerates the deterministic
artifacts and fails on any diff.
