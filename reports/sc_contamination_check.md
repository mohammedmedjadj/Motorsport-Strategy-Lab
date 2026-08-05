# Adversarial check: does a safety car contaminate a stint's own green laps?

The degradation frame already excludes neutralised laps themselves. This checks a second-order effect a safety car could plausibly cause even so -- tyre-temperature disruption showing up in the green laps *around* a neutralisation, the same category of contamination the Monaco wet-race bug turned out to be, just for a different cause.

| Circuit | Clean stints | SC-touched stints | Clean RMSE (s) | SC-touched RMSE (s) | Ratio |
|---|---|---|---|---|---|
| monaco | 22 | 73 | 1.281 | 1.510 | 1.18x |
| singapore | 46 | 80 | 0.707 | 0.905 | 1.28x |
| barcelona | 162 | 29 | 0.547 | 0.703 | 1.29x |
| suzuka | 94 | 42 | 0.561 | 0.583 | 1.04x |

**Reading `Ratio`**: fit the model on clean stints only, then score its within-stint residual on both clean stints (in-sample, the floor) and SC-touched stints it never saw (out-of-sample). A ratio near 1x means SC-touched green laps behave like any other held-out stint -- no detectable contamination beyond ordinary season-to-season noise. A ratio well above 1x would mean SC-touched stints are harder to predict specifically *because* they were touched, which would be a real, previously uncaught bias.

**No contamination detected.** Every circuit's ratio stays under 1.5x (worst: barcelona at 1.29x) -- well within the range ordinary out-of-sample noise already produces elsewhere in this project's LORO folds. The existing neutralised-lap exclusion appears sufficient; a safety car's effect on tyre temperature, if real, is not large enough to show up above the season-to-season noise this project already treats as expected.
