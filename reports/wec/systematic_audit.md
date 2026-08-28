# WEC decision audit — every first stop, every class

The model is asked **3 laps before** each real first stop, for the top 5 finishers of every class in every scoped race. Position comes from laps completed: the source carries no running order.

A **replay, not a forecast** — the decision point is defined relative to a stop that already happened. It measures where the model disagrees with real strategy, and by how much.

**120 decisions across 26 race-classes.**

| | decisions | median Δ laps | median cost |
|---|---|---|---|
| all | 120 | +1 | +3.75 s |
| real stop under green | 111 | +1 | +3.65 s |
| real stop under a neutralisation | 9 | -2 | +31.95 s |

**The model runs to the fuel deadline in 85 of 120 decisions** (71%). It optimises expected race time from the state it is given, with no track position and no way to foresee a caution, so with a tyre that still has life the tank is the only thing that ever stops it.

**8% of the real first stops here were taken under a neutralisation**, and that is what decides how far the model is from them. Under green it sits within a lap or two (+1); the gap opens on the stops taken under caution, which is the one thing a model asked three laps earlier cannot know is coming.

Across the three endurance championships that ordering is clean, and it is a property of the championship rather than of the car:

| series | first stops under caution | median Δ, green | median Δ, all |
|---|---|---|---|
| WEC | 8% | +1 | +1 |
| ELMS | 20% | +3 | +2 |
| IMSA | 53% | +7 | +12 |

**WEC and ELMS agree with real strategy to within one or two laps.** That is the strongest corroboration this simulator has: on two championships where cautions are rare, its stop timing is what teams actually did. IMSA's disagreement is not a different model — it is the same model in a championship that throws a Full Course Yellow in 61 of 63 races, so more than half its stops are opportunistic.

The F1 audit is the useful contrast. There the neutralisation split is small (+9 laps under green against +12 under caution) and the disagreement is large anyway, because F1 has **no fuel cap** — nothing bounds how long "stay out" can run. Here the tank bounds it, so what is left to explain is the cautions.

## By class

| class | decisions | median Δ | median cost | at the fuel deadline |
|---|---|---|---|---|
| WEC Hypercar | 120 | +1 | +3.75 s | 71% |

## Where the model disagrees most

| year | event | class | car | real | model | Δ | cost | neutralised |
|---|---|---|---|---|---|---|---|---|
| 2024 | Spa | HYPERCAR | 8 | 9 | 29 | +20 | +119.80 s | yes |
| 2024 | Interlagos | HYPERCAR | 6 | 28 | 44 | +16 | +71.59 s | no |
| 2025 | Fuji | HYPERCAR | 9 | 24 | 47 | +23 | +64.20 s | no |
| 2022 | Le Mans | HYPERCAR | 36 | 12 | 13 | +1 | +63.93 s | no |
| 2022 | Le Mans | HYPERCAR | 7 | 12 | 13 | +1 | +63.07 s | no |
| 2022 | Le Mans | HYPERCAR | 709 | 12 | 13 | +1 | +62.76 s | no |
| 2025 | Fuji | HYPERCAR | 20 | 28 | 47 | +19 | +51.34 s | no |
| 2025 | Fuji | HYPERCAR | 12 | 28 | 47 | +19 | +51.34 s | no |
| 2025 | Fuji | HYPERCAR | 94 | 28 | 47 | +19 | +51.34 s | no |
| 2025 | Fuji | HYPERCAR | 35 | 28 | 47 | +19 | +51.34 s | yes |
