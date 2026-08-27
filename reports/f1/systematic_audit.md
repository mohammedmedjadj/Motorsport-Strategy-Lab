# F1 decision audit — every first stop on the calendar

The model is asked **5 laps before** each real first stop, given the state as it actually was, for the top 5 classified finishers of every race with a fitted model. Its recommended lap is compared to the team's.

A **replay, not a forecast**: the decision point is defined relative to a stop that already happened. The question is where the model disagrees with real strategy and by how much, not whether it could have called the race.

**357 decisions across 25 circuits and 74 races.**

| | decisions | share | median |Δ| | median cost of the real lap |
|---|---|---|---|---|
| model agrees within 1 lap | 24 | 7% | 1 | 0.03 s |
| model would have stopped **later** | 286 | 80% | 12 | 6.71 s |
| model would have stopped **earlier** | 47 | 13% | 4 | 1.85 s |

`median cost` is the model's own median race time at the lap the team chose, minus at the lap it would have chosen. It is the size of the disagreement in seconds, and it is the number that says whether a disagreement in laps matters at all.

## Where the model disagrees most

| season | circuit | driver | real | model | Δ | cost |
|---|---|---|---|---|---|---|
| 2023 | singapore | LEC | 20 | 59 | +39 | +49.49 s |
| 2025 | singapore | VER | 19 | 59 | +40 | +47.59 s |
| 2022 | barcelona | SAI | 10 | 32 | +22 | +42.96 s |
| 2022 | montreal | HAM | 9 | 67 | +58 | +38.99 s |
| 2022 | montreal | VER | 9 | 67 | +58 | +38.99 s |
| 2022 | bahrain | MAG | 14 | 29 | +15 | +36.02 s |
| 2022 | red_bull_ring | RUS | 11 | 39 | +28 | +35.58 s |
| 2025 | montreal | RUS | 13 | 67 | +54 | +35.43 s |
| 2025 | imola | PIA | 13 | 49 | +36 | +35.40 s |
| 2025 | montreal | PIA | 16 | 67 | +51 | +33.79 s |
| 2023 | montreal | ALO | 12 | 67 | +55 | +33.25 s |
| 2023 | montreal | VER | 12 | 67 | +55 | +33.25 s |

## The disagreement is a systematic bias, and it is not the safety cars

The obvious explanation is that teams box opportunistically into a neutralisation the model cannot foresee — it is asked five laps earlier, before the Safety Car exists. **Measured, that is not what is happening.** Splitting the same decisions on whether the real stop was neutralised:

| real stop taken | decisions | median Δ laps | median cost |
|---|---|---|---|
| under green | 293 | +9 | +5.19 s |
| under a neutralisation | 64 | +12 | +7.79 s |

The bias is present in **both** groups and barely larger in the neutralised one. Whatever makes this model want to run the tyre out, it applies to ordinary green-flag stops as much as to opportunistic ones, so missing foresight does not account for it.

**What the audit establishes is that the bias exists and is large.** Two candidate causes are consistent with it and neither is tested here:

1. **No track position.** The engine optimises one car's expected race time. It cannot lose a place by staying out or gain one by stopping early, so it has no reason to pay for an undercut — and an undercut is exactly why a real team stops before it has to. The track-position layer measures how sticky each circuit is, and the single-car engine does not consume it.
2. **Slopes biased toward durability.** The endurance side of this project has a diagnosed, unfixed omitted variable that pushes fitted degradation slopes *down* ([track evolution](../cross_series/track_evolution_omitted_variable.md)). A tyre that looks flatter than it is makes staying out look cheaper than it is. Whether the F1 fits carry the same bias is not established.

Distinguishing the two is the obvious next piece of work: the adversarial-rival module already models the undercut, so re-running these decisions through it would say how much of the gap track position closes.


## By circuit

| circuit | decisions | median |Δ| laps | median cost |
|---|---|---|---|
| montreal | 15 | 51 | +33.22 s |
| barcelona | 19 | 14 | +19.37 s |
| bahrain | 20 | 12 | +19.16 s |
| hungaroring | 20 | 16 | +16.27 s |
| imola | 10 | 22 | +13.88 s |
| losail | 11 | 30 | +11.00 s |
| red_bull_ring | 15 | 12 | +10.20 s |
| singapore | 15 | 14 | +9.36 s |
| interlagos | 8 | 14 | +8.30 s |
| baku | 20 | 19 | +6.22 s |
| austin | 20 | 8 | +5.11 s |
| suzuka | 10 | 9 | +5.11 s |
| spa | 14 | 6 | +4.88 s |
| yas_marina | 20 | 7 | +4.29 s |
| monaco | 8 | 12 | +4.17 s |
| monza | 20 | 6 | +3.03 s |
| shanghai | 10 | 6 | +2.94 s |
| zandvoort | 15 | 11 | +2.73 s |
| las_vegas | 13 | 6 | +2.15 s |
| melbourne | 14 | 4 | +1.52 s |
| silverstone | 5 | 3 | +1.46 s |
| mexico_city | 20 | 5 | +1.39 s |
| jeddah | 15 | 4 | +0.61 s |
| miami | 15 | 4 | +0.31 s |
| ricard | 5 | 4 | +nan s |
