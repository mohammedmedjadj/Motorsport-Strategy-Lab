# Adversarial check: does a safety car contaminate a stint's own green laps?

The degradation frame already excludes neutralised laps themselves. This checks a second-order effect a safety car could plausibly cause even so -- tyre-temperature disruption showing up in the green laps *around* a neutralisation, the same category of contamination the Monaco wet-race bug turned out to be, just for a different cause.

| Circuit | Clean stints | SC-touched stints | Clean RMSE (s) | SC-touched RMSE (s) | Ratio |
|---|---|---|---|---|---|
| austin | 64 | 120 | 0.565 | 0.623 | 1.10x |
| bahrain | 111 | 148 | 0.451 | 0.438 | 0.97x |
| baku | 32 | 124 | 0.539 | 0.742 | 1.38x |
| barcelona | 212 | 49 | 0.595 | 0.664 | 1.12x |
| hungaroring | 102 | 113 | 0.582 | 0.833 | 1.43x |
| imola | 57 | 65 | 0.552 | 1.088 | 1.97x |
| interlagos | 103 | 55 | 0.499 | 0.516 | 1.03x |
| jeddah | 36 | 101 | 0.501 | 0.804 | 1.61x |
| las_vegas | 69 | 62 | 0.644 | 0.889 | 1.38x |
| losail | 46 | 108 | 0.552 | 0.563 | 1.02x |
| madrid | -- | -- | -- | -- | no laps in (2022, 2023, 2024, 2025) |
| melbourne | 14 | 94 | 0.385 | 1.090 | 2.83x |
| mexico_city | 50 | 119 | 0.470 | 0.592 | 1.26x |
| miami | 54 | 100 | 0.469 | 0.509 | 1.09x |
| monaco | 24 | 90 | 1.324 | 1.475 | 1.11x |
| montreal | 35 | 133 | 0.387 | 0.834 | 2.16x |
| monza | 109 | 55 | 0.510 | 0.515 | 1.01x |
| red_bull_ring | 103 | 103 | 0.452 | 0.455 | 1.01x |
| ricard | 0 | 43 | -- | -- | too few to compare |
| shanghai | 46 | 52 | 0.532 | 0.501 | 0.94x |
| silverstone | 55 | 81 | 1.129 | 0.873 | 0.77x |
| singapore | 50 | 92 | 0.892 | 1.152 | 1.29x |
| spa | 94 | 76 | 0.836 | 0.730 | 0.87x |
| suzuka | 94 | 42 | 0.561 | 0.583 | 1.04x |
| yas_marina | 135 | 56 | 0.481 | 0.468 | 0.97x |
| zandvoort | 82 | 130 | 0.500 | 0.778 | 1.55x |

**Reading `Ratio`**: fit the model on clean stints only, then score its within-stint residual on both clean stints (in-sample, the floor) and SC-touched stints it never saw (out-of-sample). A ratio near 1x means SC-touched green laps behave like any other held-out stint -- no detectable contamination beyond ordinary season-to-season noise. A ratio well above 1x would mean SC-touched stints are harder to predict specifically *because* they were touched, which would be a real, previously uncaught bias.

**Possible contamination at melbourne** (2.83x) -- worth a closer look before this is treated as settled; SC-touched stints there predict meaningfully worse than clean stints do, which is at least consistent with a real effect.
