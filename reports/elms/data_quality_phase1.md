# ELMS — Phase 1: data quality

*ELMS only. Both LMP2 classes are accounted for separately, because they are
separate populations — see [`data_availability_phase0.md`](data_availability_phase0.md) §3.*

Phase 1 answers: **of the laps the source provides, which reach the model, and
where does every excluded lap go?** The identity below must close exactly —
each stage's count plus what is kept must reconstruct the raw total — because
the numbers in this table are quoted directly by the later phases.

## Lap accounting

| stage | LMP2 | LMP2 Pro/Am |
|---|---|---|
| raw laps in the committed CSVs | **35,750** | **16,722** |
| neutralised (FCY/SC/FF/RF) or a pit visit | −5,272 | −2,562 |
| green, non-pit, but tyre age unknown | −0 | −0 |
| field-wide slow periods (see below) | −2,447 | −1,171 |
| per-car traffic trim, on the residual | −2,914 | −1,347 |
| cars with too few laps to carry an intercept | −139 | −60 |
| **kept for modelling** | **24,978** (69.9%) | **11,582** (69.3%) |

Two things worth reading off this rather than glossing.

**Not one lap is missing a tyre age.** Across 52,472 raw laps in both classes,
`est_tire_age` is populated everywhere. That is unusual — it is the column
whose absence would have ended the series at phase 0 — and it is why ELMS
could be scoped at all.

**The field-wide filter removes more here than the per-car traffic trim does
in proportion.** 2,447 LMP2 laps against 2,914, where in a prototype race the
per-car trim usually dominates. ELMS is the most Safety-Car-dominated series
in this project (23 of 29 races, see [phase 3](#)), so more of its green-flagged
laps are actually field-wide recovery running.

## The two filters, and why each exists

**Field-wide, with hysteresis.** A lap number is dropped when the median across
*all* cars on it exceeds 1.3× the race median, and the contiguous laps either
side go with it while the median stays above 1.05×. The second threshold is
not decoration: at Portimao 2023 the field median runs 1.407× on lap 6 and then
1.131, 1.077, 1.057 on laps 7-9 as the field winds back up to racing pace.
Those recovery laps are still compromised and still flagged green upstream, and
because they sit early in the race they sit at low tyre age — keeping them
drags the fitted slope negative. Removing them took physically impossible
slopes across all four series from 7 races to 3.

**Per car, on the residual.** Traffic is the dominant noise source in
multi-class racing, so each car's slowest tenth is trimmed — but on the
residual after a first-pass fit, never on raw lap time. Trimming raw lap time
selects on the quantity being estimated: within a stint the slowest laps are
the oldest-tyre laps, so a raw-time quantile shaves the top off the very curve
being measured. Measured on synthetic races, that version attenuated a true
+0.080 s/lap slope to +0.060 at realistic noise.

## Known limitation carried into later phases

Both classes still fit a substantial number of negative net slopes (9 of 25
LMP2, 5 of 17 Pro/Am). The cause is diagnosed and is **not** a filtering
problem: the model carries no race-time term, so track evolution lands on the
tyre-age coefficient with its sign inverted. Portimao 2023 gets 17.8 s a lap
faster over the race. See
[`reports/track_evolution_omitted_variable.md`](../track_evolution_omitted_variable.md),
including an attempted fix that was withdrawn because it made the real-data
refit worse.

Slope magnitudes in this series should therefore be read as a **lower bound**
on degradation, most of all where the fit is negative.

## Reproducing

```bash
python scripts/run_endurance_models.py   # writes endurance_data_quality.csv
```

The accounting identity is asserted in
`tests/test_endurance_degradation.py::test_frame_diagnostics_accounts_for_every_lap`,
which is parametrised over races where the two filters remove different laps
rather than merely the same count — a distinction an earlier version of that
test missed on a single-race sample.
