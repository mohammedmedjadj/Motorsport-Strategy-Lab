# ELMS decision audit — every first stop, every class

The model is asked **3 laps before** each real first stop, for the top 5 finishers of every class in every scoped race. Position comes from laps completed: the source carries no running order.

A **replay, not a forecast** — the decision point is defined relative to a stop that already happened. It measures where the model disagrees with real strategy, and by how much.

**171 decisions across 39 race-classes.**

| | decisions | median Δ laps | median cost |
|---|---|---|---|
| all | 171 | +2 | +5.07 s |
| real stop under green | 136 | +2 | +4.56 s |
| real stop under a neutralisation | 35 | +1 | +9.01 s |

**The model runs to the fuel deadline in 109 of 171 decisions** (64%). It optimises expected race time from the state it is given, with no track position and no way to foresee a caution, so with a tyre that still has life the tank is the only thing that ever stops it.

**20% of the real first stops here were taken under a neutralisation**, and that is what decides how far the model is from them. Under green it sits +2 laps away (+2); the gap opens on the stops taken under caution, which is the one thing a model asked three laps earlier cannot know is coming.

Across the three endurance championships that ordering is clean, and it is a property of the championship rather than of the car:

| series | first stops under caution | median Δ, green | median Δ, all |
|---|---|---|---|
| WEC | 8% | +1 | +1 |
| ELMS | 20% | +2 | +2 |
| IMSA | 53% | +7 | +12 |

**WEC and ELMS agree with real strategy to within one or two laps.** That is the strongest corroboration this simulator has: on two championships where cautions are rare, its stop timing is what teams actually did. IMSA's disagreement is not a different model — it is the same model in a championship that throws a Full Course Yellow in 61 of 63 races, so more than half its stops are opportunistic.

The F1 audit is the useful contrast. There the neutralisation split is small (+9 laps under green against +12 under caution) and the disagreement is large anyway, because F1 has **no fuel cap** — nothing bounds how long "stay out" can run. Here the tank bounds it, so what is left to explain is the cautions.

## By class

| class | decisions | median Δ | median cost | at the fuel deadline |
|---|---|---|---|---|
| ELMS LMP2 | 101 | +2 | +4.56 s | 59% |
| ELMS LMP2 Pro/Am | 70 | +3 | +6.61 s | 70% |

## Where the model disagrees most

| year | event | class | car | real | model | Δ | cost | neutralised |
|---|---|---|---|---|---|---|---|---|
| 2023 | Barcelona | LMP2 | 22 | 7 | 27 | +20 | +119.93 s | no |
| 2024 | Barcelona | LMP2 Pro/Am | 20 | 16 | 28 | +12 | +90.25 s | no |
| 2025 | Paul Ricard | LMP2 | 18 | 7 | 25 | +18 | +89.22 s | no |
| 2024 | Barcelona | LMP2 Pro/Am | 24 | 16 | 28 | +12 | +89.09 s | no |
| 2024 | Barcelona | LMP2 | 22 | 17 | 29 | +12 | +84.00 s | no |
| 2024 | Barcelona | LMP2 | 37 | 17 | 29 | +12 | +84.00 s | no |
| 2024 | Barcelona | LMP2 | 65 | 17 | 29 | +12 | +83.06 s | no |
| 2024 | Barcelona | LMP2 Pro/Am | 29 | 17 | 28 | +11 | +81.28 s | no |
| 2024 | Barcelona | LMP2 Pro/Am | 83 | 17 | 28 | +11 | +81.28 s | no |
| 2025 | Paul Ricard | LMP2 | 30 | 8 | 25 | +17 | +81.19 s | no |
