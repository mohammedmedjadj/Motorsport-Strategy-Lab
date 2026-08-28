# Sensitivity: does the fuel-limited verdict depend on the 3-lap tolerance?

The retrospective audit (`reports/endurance_audit.md`) calls a winner "fuel-limited" if its longest stint comes within **3 laps** of the measured fuel range -- a threshold picked once and never stress-tested before this pass. This is the adversarial check Section 7 of the Activity #3 roadmap named as priority #2: look for the next Monaco- or Road-America-style contamination before writing anything up, rather than assume the first choice was right.

## Headline count at each tolerance

| Tolerance (laps) | Fuel-limited | Total | Share |
|---|---|---|---|
| 0 | 148 | 209 | 70.8% |
| 1 | 168 | 209 | 80.4% |
| 2 | 177 | 209 | 84.7% |
| 3 | 178 | 209 | 85.2% |
| 5 | 189 | 209 | 90.4% |
| 7 | 196 | 209 | 93.8% |
| 10 | 201 | 209 | 96.2% |

## Per-series share at each tolerance

| Tolerance (laps) | ELMS | IMSA | WEC |
|---|---|---|---|
| 0 | 81.0% | 65.5% | 82.1% |
| 1 | 95.2% | 74.1% | 89.3% |
| 2 | 100.0% | 77.7% | 96.4% |
| 3 | 100.0% | 77.7% | 100.0% |
| 5 | 100.0% | 85.6% | 100.0% |
| 7 | 100.0% | 90.6% | 100.0% |
| 10 | 100.0% | 94.2% | 100.0% |

## Verdict

At the chosen tolerance (3 laps): **178/209 (85.2%)**. At the strictest tolerance tested (0 laps, exact reach only): **148/209 (70.8%)**. At the most lenient (10 laps): **201/209 (96.2%)**.

**The exact percentage is sensitive to the tolerance choice (25.4% swing) -- but the qualitative claim is not.** Even at the strictest possible reading (0 laps, exact reach only), 70.8% of winners still ran fuel-limited -- a clear majority at every tolerance tested. What should change is how the 3-lap number is reported: as "178/209 (85.2%) at a 3-lap tolerance, 148/209 (70.8%) at the strictest reading -- a majority either way" rather than a single unqualified point estimate. Every figure in that sentence is computed here rather than typed, because the previous version was typed and still read "49/61" long after the audit had grown past 200 races.
