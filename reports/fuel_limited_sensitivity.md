# Sensitivity: does the fuel-limited verdict depend on the 3-lap tolerance?

The retrospective audit (`reports/endurance_audit.md`) calls a winner "fuel-limited" if its longest stint comes within **3 laps** of the measured fuel range -- a threshold picked once and never stress-tested before this pass. This is the adversarial check Section 7 of the Activity #3 roadmap named as priority #2: look for the next Monaco- or Road-America-style contamination before writing anything up, rather than assume the first choice was right.

## Headline count at each tolerance

| Tolerance (laps) | Fuel-limited | Total | Share |
|---|---|---|---|
| 0 | 39 | 61 | 63.9% |
| 1 | 43 | 61 | 70.5% |
| 2 | 45 | 61 | 73.8% |
| 3 | 49 | 61 | 80.3% |
| 5 | 53 | 61 | 86.9% |
| 7 | 57 | 61 | 93.4% |
| 10 | 59 | 61 | 96.7% |

## Per-series share at each tolerance

| Tolerance (laps) | IMSA | WEC |
|---|---|---|
| 0 | 54.5% | 75.0% |
| 1 | 60.6% | 82.1% |
| 2 | 63.6% | 85.7% |
| 3 | 72.7% | 89.3% |
| 5 | 81.8% | 92.9% |
| 7 | 87.9% | 100.0% |
| 10 | 93.9% | 100.0% |

## Verdict

At the chosen tolerance (3 laps): **49/61 (80.3%)**. At the strictest tolerance tested (0 laps, exact reach only): **39/61 (63.9%)**. At the most lenient (10 laps): **59/61 (96.7%)**.

**The exact percentage is sensitive to the tolerance choice (32.8% swing) -- but the qualitative claim is not.** Even at the strictest possible reading (0 laps, exact reach only), 63.9% of winners still ran fuel-limited -- a clear majority at every tolerance tested, IMSA included (54.5% at the strictest reading, above in the per-series table). What should change is how the 3-lap number is reported: as "49/61 (80.3%) at a 3-lap tolerance, 39/61 (63.9%) at the strictest reading -- a majority either way" rather than a single unqualified point estimate. The IMSA figure in particular moves more than WEC's and deserves the same caveat inline, not just here.
