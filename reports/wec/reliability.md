# WEC reliability / attrition (results-level, 2011-2023)

From the Kaggle results history (one row per car per race, every class and round). Not lap-level, so this is the one primitive results data supports better than telemetry: **the probability a car reaches the classified finish**, over a 13-season baseline.

Coverage: **3035 car-entries**, seasons 2011-2023. Finish = official *Classified* status; *Not classified / Retired / Excluded / Not started* all count as non-finishes. Rates use the same Jeffreys `Beta(0.5,0.5)` smoother as the calibration backtest — small classes get a wide interval, never a false 0/100%.

## Finish rate by class (most fragile first)

| Class | Entries | Classified | Finish rate | 95% CI |
|---|---|---|---|---|
| CDNT | 3 | 1 | 0.375 | 0.039-0.823 |
| LMP1 | 491 | 404 | 0.822 | 0.787-0.855 |
| INNOVATIVE CAR | 2 | 2 | 0.833 | 0.333-1.000 |
| LMP2 | 977 | 833 | 0.852 | 0.829-0.874 |
| LMGTE Am | 843 | 731 | 0.867 | 0.843-0.889 |
| HYPERCAR | 140 | 123 | 0.876 | 0.817-0.925 |
| LMGTE Pro | 579 | 517 | 0.892 | 0.866-0.916 |

## Finish rate by race duration (the positive control)

The falsifiable prediction: attrition rises with race length, so a 24 h finish rate should sit **below** a 6 h one. If it did not, the model would be wrong — reported either way.

| Duration | Entries | Classified | Finish rate | 95% CI |
|---|---|---|---|---|
| 4h | 62 | 59 | 0.944 | 0.876-0.986 |
| 6h | 1929 | 1747 | 0.905 | 0.892-0.918 |
| 8h | 253 | 237 | 0.935 | 0.902-0.962 |
| 12h | 29 | 25 | 0.850 | 0.705-0.952 |
| 24h | 762 | 543 | 0.712 | 0.680-0.744 |

**Positive control: attrition-rises-with-duration holds** (longest-race finish rate < shortest-race).

## What this does and does not add

- Adds a measured attrition prior absent from every lap-level model here.
- Does **not** feed degradation or neutralisation models (no per-lap data); it is a separate, complementary layer.
- Results-level only: it cannot say *when* in a race a car failed, only whether it was classified.
