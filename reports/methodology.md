# Uncertainty-First Race Strategy Modelling and a Retrospective Audit of Real Formula 1 Pit-Stop Decisions

**Author:** Mohammed Reda Medjadj
**Date:** July 2026.
**Repository:** `motorsport-strategy-lab` (all numbers in this report are generated
by the scripts in `scripts/` and traceable to the phase reports in
`reports/`; simulation numbers use seed 20260712, 5000 draws).

## Abstract

I build a three-layer decision-support system for Formula 1 pit-stop
strategy from public timing data (FastF1): (1) a fixed-effects tyre
degradation model per circuit and compound; (2) a Bayesian safety-car (SC)
and virtual-safety-car (VSC) probability model on 2018-2025 history; and
(3) a Monte Carlo simulator that propagates the uncertainty of both layers
â€” coefficients resampled from their intervals, hazards from their
posteriors â€” into full outcome distributions for every candidate pit lap.
We then replay five real strategy decisions from the 2023-2024 seasons
through the simulator and compare its recommendations with what the
strategists actually did. The audit yields three findings: median race
time alone mis-ranks real decisions (Verstappen's Barcelona 2024 covering
stop costs +3.2s in median time yet holds the highest P(best) = 0.43 and
the best P(ahead) = 0.70); a known qualitative limitation â€” the absence of
field bunching behind the safety car â€” is converted into a measured ~6-7s
bias for SC-window decisions at the front of the field; and the most
criticised-by-outcome gamble in the set (Mercedes, Singapore 2023) was the
right bet by expected time and win probability. Cross-season validation
shows degradation slopes are not stable between editions of the same race
(frequently negative out-of-sample within-stint RÂ²), which is why every
model output ships as a distribution rather than a point estimate.

## 1. Motivation and related work

Public F1 data projects overwhelmingly stop at fitting a tyre-degradation
curve or predicting a pit lap as a single number. Tyre-degradation
notebooks built on FastF1 exist in large numbers, and professional
strategy tools (teams' internal simulators, broadcast strategy graphics)
solve a far richer version of this problem with private data. We do not
claim novelty for any individual layer. The contribution of this project
is the combination, on public data, of:

1. **end-to-end uncertainty propagation** â€” every layer's uncertainty
   (coefficient CIs, hazard posteriors, lap noise at the cross-validated
   RMSE) survives into the final recommendation, and
2. **a retrospective decision audit** â€” the model is confronted with five
   real, data-reconstructed decision moments and its agreements *and*
   failures are quantified, including a measured bias attributable to a
   documented modelling gap.

We cite no academic literature because none was consulted or used; the
methods employed (fixed-effects OLS, Jeffreys-prior Beta-Binomial and
Gamma-Poisson models, Monte Carlo simulation with common random numbers)
are textbook-standard and are described fully below.

## 2. Data

Single source: [FastF1](https://github.com/theOehrly/Fast-F1), which
exposes official live-timing data. No missing value is imputed or
fabricated anywhere in the pipeline; gaps are reported as gaps.

- **Pace/degradation scope:** 12 races â€” Monaco, Singapore, Barcelona,
  Suzuka Ã— seasons 2023-2025 (ground-effect era; 2022 excluded for
  porpoising noise). Circuits chosen to contrast the two modelled risk
  dimensions: street circuits with high historical SC reputation vs
  permanent circuits with high tyre stress (`reports/data_availability_phase0.md`).
- **SC/VSC scope:** the same four events extended to 2018-2025 â€” 27
  editions, the only exclusions being five COVID cancellations, each
  listed with its rejection reason (`reports/safety_car_phase3.md`).
- **Cleaning:** flag-based, no silent row drops. Of 14,342 laps, 12,091
  (84.3%) qualify as pace laps; every exclusion is accounted for by reason
  (in/out laps, inaccurate timing, wet compounds, non-green track status,
  deleted times) in `reports/data_quality_phase1.md`.
- A loader guard validates FastF1's fuzzy event resolution: requesting the
  cancelled 2020 Monaco GP otherwise silently returns a different race
  (observed: the Italian GP), which contaminated a first extraction run
  and is now a tested failure mode.

## 3. Method

### 3.1 Tyre degradation (per circuit)

Fixed-effects OLS on pooled seasons:
`lap_time = a_{driver,race} + fÂ·lap_number + d_c(tyre_age) + Îµ`, where
`a` absorbs car/driver/race-day pace, `f` proxies fuel burn, and `d_c` is
a per-compound polynomial (degree 1 or 2, selected per circuit by
cross-validation). Identification of fuel vs tyre age comes from stints
starting at different lap numbers with fresh tyres â€” which is also why
the fixed effect must be per driver-race, not per stint. Validation is
leave-one-race-out, scored on within-stint demeaned lap times (driver-race
intercepts cannot transfer to an unseen race). Coefficient recovery is
proven on synthetic data with known slopes before touching real data.

### 3.2 SC/VSC probability (per circuit)

From the `TrackStatus` change log we extract every SC/VSC/red-flag period
and map it to race laps via the leader's lap boundaries. Two quantities
are estimated with Jeffreys priors and 95% equal-tailed credible
intervals: P(â‰¥1 event per race) (Beta-Binomial) and the per-green-lap
deployment rate (Gamma-Poisson). With 6-8 editions per circuit, interval
width is treated as a first-class result.

### 3.3 Monte Carlo simulator

For a race state (circuit, lap, compound, tyre age, gaps to rivals with
their plans), the engine evaluates every feasible pit lap over 5000
simulated race continuations. Per draw: degradation and fuel coefficients
are resampled from their CIs, hazards from their Gamma posteriors,
neutralisation durations from observed events, and lap noise at the
Phase 2 CV RMSE. All candidates share each draw's realisation (common
random numbers), so P(candidate is best) is a clean per-draw argmin.
Circuit constants are measured from the data: green pace, pit loss
(median of in+out-lap cost vs the driver's own median, n = 47-123 stops
per circuit: Monaco 19.1s, Barcelona/Suzuka 23.5s, Singapore 27.3s) and
SC/VSC pace ratios (1.38-1.43 / 1.15-1.37). A stop under neutralisation
is cheaper by the measured pace ratio. Outputs per candidate: median,
mean, P10-P90, P(best), P(ahead of each rival).

Declared scope exclusions: no field bunching behind the SC (gap resets),
no red flags, no track-position/overtaking value, rivals frozen to their
historical plans.

### 3.4 Audit protocol

Five decision moments from 2023-2024, chosen to span: a successful
covering stop, a failed extended stint, a collective SC stop, an
aggressive VSC gamble, and a case designed to expose the model's blind
spot. Race states are reconstructed from the committed lap data
(compounds, tyre ages, cumulative-time gaps, real rival plans) â€” nothing
is quoted from memory. Every audit table shows the real decision's row
and a quantified verdict; margins under ~2s are declared ties given Â§4.1.

## 4. Results

### 4.1 Degradation (Phase 2)

Fuel-burn proxies: âˆ’0.050 to âˆ’0.081 s/lap across circuits (consistent
with the ~0.03 s/kg rule of thumb). Linear degradation terms: Barcelona
+0.09 to +0.11 s per lap of age, Suzuka +0.08 to +0.13, street circuits
substantially lower â€” with flattening quadratics where selected. CV RMSE
0.57-1.26 s/lap. The headline honest finding: **within-stint RÂ² is
frequently negative out of sample** (as low as âˆ’0.58) while the identical
pipeline scores ~0.85 at the noise floor on synthetic data â€” degradation
slopes genuinely move between editions of the same race. Consequence:
coefficients are only ever used as distributions.

### 4.2 SC/VSC (Phase 3)

Singapore has the highest per-lap SC rate, 0.020 [0.009, 0.037] â€” about
2.4Ã— the other circuits. Monaco's "guaranteed safety car" folklore does
not survive the data: P(â‰¥1 SC) = 0.44 [0.14, 0.77] over 2018-2025 (3 of
7 editions). All intervals span factors of 2-4; conclusions requiring
precision inside them are unsupported.

### 4.3 Audit (Phase 5)

| Case | Real decision | Model verdict |
|---|---|---|
| A. Barcelona 2024, Verstappen lap-17 cover | Won | +3.2s median vs optimum, **but** highest P(best) (0.43) and P(ahead) 0.70 vs 0.64 â€” vindicated by the distributions |
| B. Barcelona 2024, Norris extended stint | Lost by 2.2s | P(ahead) flat at 0.30-0.32 across all stop laps â€” the race was not lost on stop timing |
| C. Singapore 2023, Sainz SC stop lap 20 | Won | Model calls it +6.5s worse than staying out â€” **the model is wrong**: the missing bunching mechanism, now quantified as a ~6-7s bias |
| D. Singapore 2023, Russell VSC stop lap 44 | Crashed while attacking | Endorsed: better than staying out on median (1913.8 vs 1915.5s) and P(ahead SAI) (0.47 vs 0.42) â€” a near coin-flip for the win at ~zero cost |
| E. Monaco 2024, nobody stops | Leclerc won | Model independently selects no-stop (P(best) 0.69): Monaco's degradation never repays a 19.1s pit loss |

Cross-case: (i) distribution outputs â€” not the median â€” are what make
audits of real decisions fair; (ii) decision quality and outcome are
distinct (D); (iii) a documented qualitative limitation became a
measurable bias (C).

## 5. Limitations

- **No bunching, no track-position value, no red flags** â€” the simulator
  optimises expected race time; Case C measures what this costs where it
  matters most (SC windows at the front).
- **Degradation slopes are not stable across seasons** (Â§4.1); any
  in-race application would need online re-estimation from live laps.
- **Small SC samples**: 6-8 editions per circuit; the constant-hazard
  assumption understates lap-1 risk (deployment laps cluster early).
- **Compound allocation is not random** (teams fit HARD for long stints),
  so per-compound slopes are descriptive, not causal.
- **Rivals are frozen to history** in the audit; counterfactual reactions
  are not simulated.
- Classical homoscedastic standard errors in Phase 2; lap noise is
  heteroscedastic in reality.

## 6. Future work

Online (in-race) re-estimation of the degradation slope; a two-bin
early/late SC hazard; a queueing model of SC bunching (which Case C shows
is first-order); rival reaction policies; extension to more circuits.

## 7. Reproducibility

Python 3.13, dependencies pinned in `requirements.lock` (fastf1 3.8.3,
pandas 2.3.3, numpy 2.5.1, scipy 1.18.0). FastF1 cache under
`data/cache/` (gitignored); derived datasets committed under
`data/derived/`. All stochastic code is seeded. 62 pytest tests cover
ingestion, both models, the engine and the audit tooling, including
synthetic ground-truth recovery and leakage assertions. Each phase's full
output is a committed report in `reports/`.

