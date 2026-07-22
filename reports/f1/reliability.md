# F1 reliability / attrition (Kaggle results, 2011-2024)

The cross-series counterpart to the [WEC reliability layer](../wec/reliability.md), same Jeffreys smoother (`reliability.core`). Probability a car is classified at the finish (saw the flag or was lapped); every mechanical/accident status is a DNF.

Coverage: **5980 car-entries**, 2011-2024, overall finish rate **0.826**.

## Most fragile circuits (>= 40 entries, most fragile first)

| Circuit | Entries | Classified | Finish rate | 95% CI |
|---|---|---|---|---|
| albert_park | 251 | 178 | 0.708 | 0.651-0.763 |
| monaco | 274 | 211 | 0.769 | 0.718-0.817 |
| baku | 162 | 125 | 0.770 | 0.703-0.831 |
| sepang | 154 | 119 | 0.771 | 0.702-0.833 |
| marina_bay | 254 | 200 | 0.786 | 0.734-0.834 |
| jeddah | 80 | 64 | 0.796 | 0.703-0.876 |
| villeneuve | 254 | 203 | 0.798 | 0.747-0.845 |
| silverstone | 314 | 255 | 0.811 | 0.766-0.852 |
| nurburgring | 66 | 54 | 0.813 | 0.713-0.897 |
| americas | 246 | 202 | 0.820 | 0.770-0.865 |

## Finish rate by regulation era

| Era | Entries | Finish rate | 95% CI |
|---|---|---|---|
| ground-effect | 1359 | 0.857 | 0.838-0.875 |
| hybrid-v6 | 1247 | 0.798 | 0.776-0.820 |
| v8-blown | 1354 | 0.825 | 0.804-0.844 |
| wide-aero | 2020 | 0.824 | 0.807-0.840 |

**Positive control: permanent circuits finish better than street circuits — holds** (0.832 permanent vs 0.796 street). Street tracks punish any error with a wall, so higher attrition there is the expected sign — reported either way.

The early **hybrid-v6** era is the least reliable, matching the well-known 2014 power-unit teething; **ground-effect** (2022+) is the most reliable. Eras are never pooled (see the degradation report for the 2026 wall).
