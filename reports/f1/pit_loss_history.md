# F1 pit loss — full-calendar breadth (Kaggle), validated vs FastF1

Green-flag pit loss (`t_in + t_out - 2 x driver green median`, stops beyond 2x the median trimmed) across the whole calendar — the breadth complement to the FastF1 estimator, which is exact but four circuits.

Coverage: **35 circuits**. Kaggle has no per-lap Safety-Car flag, so green-flanking is enforced by the same field-wide slow-lap inference the degradation layer uses.

## Validation against the FastF1 ground truth (the honest headline)

On the four circuits FastF1 also covers, how the Kaggle estimate compares:

| Circuit | Kaggle (s) | FastF1 (s) | Delta (s) |
|---|---|---|---|
| suzuka | 23.3 | 23.5 | -0.2 |
| catalunya | 23.3 | 23.5 | -0.3 |
| marina_bay | 31.2 | 27.3 | +3.9 |
| monaco | 39.3 | 19.1 | +20.2 |

The agreement is **within a few tenths on permanent circuits** (Barcelona, Suzuka) and degrades on **high-Safety-Car street circuits** (Singapore moderately, **Monaco by ~20 s**): without an SC flag, stops made under neutralisation inflate the measured loss, and street circuits see the most of them. **Where FastF1 covers a circuit, prefer it**; this breadth layer is trustworthy for the permanent circuits it uniquely adds.

## Pit loss by circuit, current era (`ground-effect`), street flagged

| Circuit | Pit loss (s) | IQR (s) | Stops | Street? |
|---|---|---|---|---|
| monaco | 39.3 | 15.3 | 50 | yes (uncertain) |
| marina_bay | 31.2 | 6.4 | 41 | yes (uncertain) |
| silverstone | 30.2 | 16.5 | 75 | no |
| losail | 29.5 | 3.8 | 57 | no |
| ricard | 29.1 | 3.6 | 9 | no |
| imola | 28.2 | 2.4 | 35 | no |
| monza | 25.7 | 3.0 | 75 | no |
| bahrain | 25.0 | 3.2 | 137 | no |
| shanghai | 24.6 | 1.9 | 22 | no |
| zandvoort | 24.2 | 9.9 | 108 | no |
| vegas | 24.0 | 3.7 | 55 | yes (uncertain) |
| baku | 23.4 | 3.3 | 41 | yes (uncertain) |
| rodriguez | 23.4 | 2.1 | 61 | no |
| yas_marina | 23.4 | 2.8 | 92 | no |
| suzuka | 23.3 | 5.4 | 88 | no |
| catalunya | 23.3 | 2.6 | 135 | no |
| interlagos | 22.3 | 2.0 | 74 | no |
| jeddah | 21.9 | 10.1 | 23 | yes (uncertain) |
| hungaroring | 21.9 | 3.1 | 116 | no |
| red_bull_ring | 21.5 | 2.1 | 110 | no |
| americas | 21.5 | 2.9 | 84 | no |
| miami | 21.4 | 3.1 | 53 | yes (uncertain) |
| albert_park | 21.4 | 3.7 | 51 | no |
| villeneuve | 20.1 | 4.8 | 55 | no |
| spa | 19.1 | 2.9 | 107 | no |
