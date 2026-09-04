# F1 decision audit — every first stop on the calendar

The model is asked **5 laps before** each real first stop, given the state as it actually was, for the top 5 classified finishers of every race with a fitted model. Its recommended lap is compared to the team's.

A **replay, not a forecast**: the decision point is defined relative to a stop that already happened. The question is where the model disagrees with real strategy and by how much, not whether it could have called the race.

**357 decisions across 25 circuits and 74 races.**

| | decisions | share | median |Δ| | median cost of the real lap |
|---|---|---|---|---|
| model agrees within 1 lap | 27 | 8% | 1 | 0.03 s |
| model would have stopped **later** | 284 | 80% | 12 | 6.86 s |
| model would have stopped **earlier** | 46 | 13% | 4 | 1.83 s |

`median cost` is the model's own median race time at the lap the team chose, minus at the lap it would have chosen. It is the size of the disagreement in seconds, and it is the number that says whether a disagreement in laps matters at all.

## Where the model disagrees most

| season | circuit | driver | real | model | Δ | cost |
|---|---|---|---|---|---|---|
| 2023 | singapore | LEC | 20 | 59 | +39 | +49.49 s |
| 2025 | singapore | VER | 19 | 59 | +40 | +47.59 s |
| 2022 | barcelona | SAI | 10 | 31 | +21 | +43.28 s |
| 2022 | montreal | HAM | 9 | 67 | +58 | +38.99 s |
| 2022 | montreal | VER | 9 | 67 | +58 | +38.99 s |
| 2022 | bahrain | MAG | 14 | 29 | +15 | +36.02 s |
| 2022 | red_bull_ring | RUS | 11 | 39 | +28 | +35.58 s |
| 2025 | montreal | RUS | 13 | 67 | +54 | +35.43 s |
| 2025 | imola | PIA | 13 | 49 | +36 | +35.40 s |
| 2025 | montreal | PIA | 16 | 67 | +51 | +33.79 s |
| 2023 | montreal | HAM | 12 | 67 | +55 | +33.25 s |
| 2023 | montreal | ALO | 12 | 67 | +55 | +33.25 s |

## The disagreement is a systematic bias, and it is not the safety cars

The obvious explanation is that teams box opportunistically into a neutralisation the model cannot foresee — it is asked five laps earlier, before the Safety Car exists. **Measured, that is not what is happening.** Splitting the same decisions on whether the real stop was neutralised:

| real stop taken | decisions | median Δ laps | median cost |
|---|---|---|---|
| under green | 293 | +9 | +5.20 s |
| under a neutralisation | 64 | +12 | +7.79 s |

The bias is present in **both** groups and barely larger in the neutralised one. Whatever makes this model want to run the tyre out, it applies to ordinary green-flag stops as much as to opportunistic ones, so missing foresight does not account for it.

**What the audit establishes is that the bias exists and is large.** Two causes were consistent with it. One has since been tested and **rejected**; the other is still open:

1. ~~**No track position.**~~ **Tested and rejected.** The engine optimises one car's expected race time and cannot pay for an undercut, which sounded like the answer. Re-running all 357 decisions through the cover-aware adversarial engine — which does model the undercut and does consume each circuit's measured stickiness — moves the recommendation *away* from the real stop, not toward it: median error +11 laps against the single-car engine's +9, closer in 65 decisions and further in 188. See [`undercut_hypothesis.md`](undercut_hypothesis.md).
2. ~~**Slopes biased toward durability.**~~ **Tested and not detected.** The endurance side carries a diagnosed, unfixed omitted variable that pushes slopes down, and a tyre that looks flatter than it is makes staying out look cheaper. Measured against the Kaggle breadth layer — an independent source separating tyre wear from fuel burn by a different method — the two agree at r = +0.85 with a median paired difference of +0.0006 s/lap. An error that size moves the stop by several race distances' worth of laps, not twelve. See [`slope_bias_check.md`](slope_bias_check.md).

**Both explanations are measured and neither accounts for the finding.** The result stands as measured and unexplained, which is a worse position than having a plausible story and a better one than publishing a story two measurements contradict.

What is left to try is the question itself. The model is asked five laps before the real stop and offers every remaining lap as a candidate; a real team is choosing between a handful of laps inside a strategy already committed to, with a tyre allocation and a two-compound rule the engine does not see. The two may not be answering the same question, and testing that means changing the audit rather than the model.


## By circuit

| circuit | decisions | median |Δ| laps | median cost |
|---|---|---|---|
| montreal | 15 | 51 | +33.22 s |
| barcelona | 19 | 14 | +19.47 s |
| bahrain | 20 | 12 | +19.16 s |
| hungaroring | 20 | 16 | +16.77 s |
| imola | 10 | 22 | +13.88 s |
| losail | 11 | 30 | +11.95 s |
| red_bull_ring | 15 | 12 | +10.20 s |
| singapore | 15 | 14 | +9.36 s |
| interlagos | 8 | 12 | +6.93 s |
| baku | 20 | 19 | +6.22 s |
| austin | 20 | 8 | +5.11 s |
| suzuka | 10 | 9 | +5.11 s |
| monaco | 8 | 12 | +4.17 s |
| spa | 14 | 8 | +3.86 s |
| yas_marina | 20 | 7 | +3.86 s |
| monza | 20 | 6 | +3.03 s |
| shanghai | 10 | 5 | +2.83 s |
| zandvoort | 15 | 11 | +2.73 s |
| las_vegas | 13 | 6 | +2.15 s |
| melbourne | 14 | 4 | +1.52 s |
| silverstone | 5 | 3 | +1.46 s |
| mexico_city | 20 | 6 | +0.68 s |
| jeddah | 15 | 4 | +0.61 s |
| miami | 15 | 4 | +0.31 s |
| ricard | 5 | 4 | +nan s |
