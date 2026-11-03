# IMSA decision audit — every first stop, every class

The model is asked **3 laps before** each real first stop, for the top 5 finishers of every class in every scoped race. Position comes from laps completed: the source carries no running order.

A **replay, not a forecast** — the decision point is defined relative to a stop that already happened. It measures where the model disagrees with real strategy, and by how much.

**632 decisions across 136 race-classes.**

| | decisions | median Δ laps | median cost |
|---|---|---|---|
| all | 632 | +12 | +15.36 s |
| real stop under green | 300 | +7 | +5.89 s |
| real stop under a neutralisation | 332 | +15 | +26.90 s |

**The model runs to the fuel deadline in 438 of 632 decisions** (69%). It optimises expected race time from the state it is given, with no track position and no way to foresee a caution, so with a tyre that still has life the tank is the only thing that ever stops it.

**53% of the real first stops here were taken under a neutralisation**, and that is what decides how far the model is from them. Under green it sits +7 laps away (+7); the gap opens on the stops taken under caution, which is the one thing a model asked three laps earlier cannot know is coming.

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
| IMSA GTD | 268 | +12 | +15.57 s | 75% |
| IMSA GTD PRO | 215 | +13 | +20.37 s | 69% |
| IMSA GTP | 149 | +9 | +10.34 s | 58% |

## Where the model disagrees most

| year | event | class | car | real | model | Δ | cost | neutralised |
|---|---|---|---|---|---|---|---|---|
| 2025 | Road Atlanta | GTP | 6 | 10 | 52 | +42 | +291.65 s | yes |
| 2026 | Daytona | GTP | 31 | 13 | 34 | +21 | +291.17 s | no |
| 2024 | Daytona | GTDPRO | 62 | 20 | 35 | +15 | +279.33 s | yes |
| 2024 | Daytona | GTDPRO | 1 | 20 | 35 | +15 | +275.76 s | yes |
| 2024 | Daytona | GTDPRO | 23 | 20 | 35 | +15 | +275.71 s | yes |
| 2023 | Road Atlanta | GTP | 24 | 8 | 46 | +38 | +272.02 s | no |
| 2024 | Daytona | GTP | 40 | 20 | 33 | +13 | +269.36 s | yes |
| 2024 | Daytona | GTP | 31 | 20 | 33 | +13 | +269.36 s | yes |
| 2024 | Daytona | GTP | 5 | 20 | 33 | +13 | +269.36 s | yes |
| 2024 | Daytona | GTP | 7 | 20 | 33 | +13 | +269.36 s | yes |
