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
— coefficients resampled from their intervals, hazards from their
posteriors — into full outcome distributions for every candidate pit lap.
We then replay five real strategy decisions from the 2023-2024 seasons
through the simulator and compare its recommendations with what the
strategists actually did. The audit yields three findings: median race
time alone mis-ranks real decisions (Verstappen's Barcelona 2024 covering
stop costs +4.97s in median time, holds the highest P(best) of any
candidate at 0.416, and is beaten on P(ahead of Norris) by lap 22, 0.659
against 0.731 — three summaries, three rankings); a known qualitative
limitation — the absence of field bunching behind the safety car — is
converted into a measured ~6s bias for SC-window decisions at the front of
the field; and the most
criticised-by-outcome gamble in the set (Mercedes, Singapore 2023) was the
right bet by expected time and win probability. Cross-season validation
shows degradation slopes are not stable between editions of the same race
(frequently negative out-of-sample within-stint R²), which is why every
model output ships as a distribution rather than a point estimate.

## 1. Motivation and related work

Public F1 data projects overwhelmingly stop at fitting a tyre-degradation
curve or predicting a pit lap as a single number. Tyre-degradation
notebooks built on FastF1 exist in large numbers, and professional
strategy tools (teams' internal simulators, broadcast strategy graphics)
solve a far richer version of this problem with private data. We do not
claim novelty for any individual layer. The contribution of this project
is the combination, on public data, of:

1. **end-to-end uncertainty propagation** — every layer's uncertainty
   (coefficient CIs, hazard posteriors, lap noise at the cross-validated
   RMSE) survives into the final recommendation, and
2. **a retrospective decision audit** — the model is confronted with five
   real, data-reconstructed decision moments and its agreements *and*
   failures are quantified, including a measured bias attributable to a
   documented modelling gap.

Five recent works occupy the same problem space and are the closest
comparisons, all F1-specific:

Aguad & Thraves (2024, *European Journal of Operational Research*) formulate
pit-stop strategy as a zero-sum feedback Stackelberg game solved by dynamic
programming — the race leader decides first, the follower reacts — and find
that ignoring the opponent's reaction costs a driver roughly 15% of their
win probability. Our own simulator carries a directly comparable
reaction-aware component (`src/simulator/adversarial.py::duel`): a rival
that observes the ego car's stop and chooses its own best-response cover or
overcut, with `cost_of_ignoring_the_cover` quantifying the same kind of loss
their paper reports — but evaluated across three series rather than one,
and checked against the retrospective audit rather than left as a pure
optimisation result.

Three works optimise or predict the pit-stop decision directly from data
with learned models rather than interpretable statistics: a deep-learning
decision-support system trained on raw telemetry across five architectures
(Bi-LSTM, TCN-GRU, GRU, InceptionTime, CNN-BiLSTM) to predict the optimal
stop lap (*Frontiers in Artificial Intelligence*, 2025); a joint
reinforcement-learning framework over energy management, tyre wear and
pit timing (arXiv:2512.21570, Dec. 2025); and an explainable RL agent
developed with Mercedes-AMG PETRONAS reporting an 8.6s average improvement
over fixed strategies (Thomas et al., arXiv:2501.04068, 2025). These
systems are more powerful function approximators than the fixed-effects
OLS and conjugate Bayesian models used here, at the cost of interpretability
— a reader cannot ask *why* a recommendation changed the way they can ask
of a coefficient with a confidence interval, which is the trade this project
deliberately makes in the other direction.

The closest work in spirit is Pitwall (arXiv:2607.06495, 2026), a
production system pairing a calibrated real-time Monte Carlo engine with
natural-language strategy briefings, validated against seven scored F1
seasons (2018-2025). It shares this project's commitment to calibrated
probabilities over point predictions but is, again, single-series and
oriented at live race-day output rather than at the question this project
asks: *does a model fitted this way generalise*, and *does it agree with
what real strategists decided*.

None of the five tests whether a fitted quantity (degradation, pit loss,
neutralisation risk) transfers across seasons or across series, and none
confronts its output against real human strategic decisions the way §4.3's
audit does. Both gaps are addressed here, and a third, broader test —
whether *any* fitted quantity in this project generalises, not just
degradation — is reported separately in
[`reports/generalization_audit.md`](generalization_audit.md), which extends
this same leave-one-race-out protocol to pit loss and neutralisation
occurrence across F1, WEC and IMSA.

Beyond these five, the methods themselves (fixed-effects OLS, Jeffreys-prior
Beta-Binomial and Gamma-Poisson models, Monte Carlo simulation with common
random numbers) are textbook-standard and are described fully below.

## 2. Data

Single source: [FastF1](https://github.com/theOehrly/Fast-F1), which
exposes official live-timing data. No missing value is imputed or
fabricated anywhere in the pipeline; gaps are reported as gaps.

- **Pace/degradation scope:** 12 races — Monaco, Singapore, Barcelona,
  Suzuka × seasons 2023-2025 (ground-effect era; 2022 excluded for
  porpoising noise). Circuits chosen to contrast the two modelled risk
  dimensions: street circuits with high historical SC reputation vs
  permanent circuits with high tyre stress (`reports/data_availability_phase0.md`).
- **SC/VSC scope:** the same four events extended to 2018-2025 — 27
  editions, the only exclusions being five COVID cancellations, each
  listed with its rejection reason (`reports/safety_car_phase3.md`).
- **Cleaning:** flag-based, no silent row drops. Over the 12 modelled races
  above, 14,342 laps yield 12,091 pace laps
  (84.3%); every exclusion is accounted for by reason
  (in/out laps, inaccurate timing, wet compounds, non-green track status,
  deleted times) in `reports/data_quality_phase1.md`.
- A loader guard validates FastF1's fuzzy event resolution: requesting the
  cancelled 2020 Monaco GP otherwise silently returns a different race
  (observed: the Italian GP), which contaminated a first extraction run
  and is now a tested failure mode.
- **Ingestion runs ahead of the modelling scope, on purpose.** It is
  era-blind and rolling, so the committed data also holds the 2026 races run
  so far (Suzuka, Monaco — 16,901 laps and 14,140 pace laps across all 14
  ingested races). No fitted quantity in this report uses them: the 2026
  regulation change (power unit, active aero, narrower cars and tyres) is
  treated as an era boundary that coefficients must not pool across, and the
  new era is instead held out as a test set. §4.1 reports what that test
  says.

## 3. Method

### 3.1 Tyre degradation (per circuit)

Fixed-effects OLS on pooled seasons:
`lap_time = a_{driver,race} + f·lap_number + d_c(tyre_age) + ε`, where
`a` absorbs car/driver/race-day pace, `f` proxies fuel burn, and `d_c` is
a per-compound polynomial (degree 1 or 2, selected per circuit by
cross-validation). Identification of fuel vs tyre age comes from stints
starting at different lap numbers with fresh tyres — which is also why
the fixed effect must be per driver-race, not per stint. Validation is
leave-one-race-out, scored on within-stint demeaned lap times (driver-race
intercepts cannot transfer to an unseen race). Coefficient recovery is
proven on synthetic data with known slopes before touching real data.

### 3.2 SC/VSC probability (per circuit)

From the `TrackStatus` change log we extract every SC/VSC/red-flag period
and map it to race laps via the leader's lap boundaries. Two quantities
are estimated with Jeffreys priors and 95% equal-tailed credible
intervals: P(≥1 event per race) (Beta-Binomial) and the per-green-lap
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
(compounds, tyre ages, cumulative-time gaps, real rival plans) — nothing
is quoted from memory. Every audit table shows the real decision's row
and a quantified verdict; margins under ~2s are declared ties given §4.1.

## 4. Results

### 4.1 Degradation (Phase 2)

Fuel-burn proxies: −0.050 to −0.081 s/lap across circuits (consistent
with the ~0.03 s/kg rule of thumb). Linear degradation terms: Barcelona
+0.09 to +0.11 s per lap of age, Suzuka +0.08 to +0.13, street circuits
substantially lower — with flattening quadratics where selected. CV RMSE
0.57-1.26 s/lap. The headline honest finding: **within-stint R² is
frequently negative out of sample** (as low as −0.58) while the identical
pipeline scores ~0.85 at the noise floor on synthetic data — degradation
slopes genuinely move between editions of the same race. Consequence:
coefficients are only ever used as distributions.

**Does a pre-2026 fit survive the regulation change?** With the first
new-era races ingested this stops being a caveat and becomes a measurement:
train strictly on 2023-2025, predict a 2026 race, score on the same
within-stint demeaned residual as the folds above. The result is genuinely
split — Suzuka 2026 scores R² −0.008 against a pre-era fold range of −0.582
to −0.043 (better than *any* old-era season), Monaco 2026 scores −0.177
against −0.071 to +0.322 (worse than any). So the boundary shows up sharply
in the *coefficients* — pooling 2026 into Suzuka's fit halves its tyre-age
slope and flips the selected polynomial degree, which is why the fits above
exclude it — but not, on two races, in *predictive transfer*. That is
consistent with §4.1's own finding that slopes move between any two seasons,
regulation change or not. Two races at two circuits cannot settle whether
the new formula is harder to predict; they are enough to justify not
pooling coefficients across it.

### 4.2 SC/VSC (Phase 3)

Singapore has the highest per-lap SC rate, 0.020 [0.009, 0.037] — about
2.4× the other circuits. Monaco's "guaranteed safety car" folklore does
not survive the data: P(≥1 SC) = 0.44 [0.14, 0.77] over 2018-2025 (3 of
7 editions). All intervals span factors of 2-4; conclusions requiring
precision inside them are unsupported.

### 4.3 Audit (Phase 5)

| Case | Real decision | Model verdict |
|---|---|---|
| A. Barcelona 2024, Verstappen lap-17 cover | Won | +4.97s median vs optimum, **but** the highest P(best) of any candidate (0.416 vs 0.025); on P(ahead of Norris) lap 22 beats it (0.731 vs 0.659) — the three metrics rank it differently, which is the finding |
| B. Barcelona 2024, Norris extended stint | Lost by 2.2s | P(ahead) never reaches 0.5 at any stop lap (0.145-0.369) — no available choice makes him favourite, so the race was not lost on stop timing |
| C. Singapore 2023, Sainz SC stop lap 20 | Won | Model calls it +5.91s worse than the lap-35 optimum — **the model is wrong**: the missing bunching mechanism, now quantified as a ~6s bias |
| D. Singapore 2023, Russell VSC stop lap 44 | Crashed while attacking | Endorsed: better than staying out on median (1913.3 vs 1914.9s), within 1.11s of the optimum, and P(ahead SAI) 0.477 — a near coin-flip for the win at ~zero cost |
| E. Monaco 2024, nobody stops | Leclerc won | Model independently selects no-stop (P(best) 0.581): Monaco's degradation never repays a 19.1s pit loss — but it has no track-position term, so this is the right answer for the wrong reason |

Cross-case: (i) distribution outputs — not the median — are what make
audits of real decisions fair; (ii) decision quality and outcome are
distinct (D); (iii) a documented qualitative limitation became a
measurable bias (C).

## 5. Threats to validity

The leave-one-race-out protocol in §3.1 was fixed before any held-out
result was inspected — the same code path scores every fold, so no
threshold or degree choice here was tuned against the number it was later
judged by. That discipline bounds *how* the following limitations can bias
the reported numbers, but does not remove them; each is stated against the
class of validity it actually threatens, rather than as an undifferentiated
list.

**Internal validity** — could the reported effect be an artefact of the
estimation itself, not the phenomenon it claims to measure?

- **Compound allocation is not random**: teams fit HARD tyres when they
  plan long stints, so per-compound degradation slopes are descriptive of
  observed usage, not a causal effect of compound choice isolated from
  strategy intent.
- **Classical homoscedastic standard errors** are used throughout Phase 2;
  lap-time noise is heteroscedastic in reality (traffic, fuel-load
  variance, track evolution), so reported confidence intervals are an
  approximation, not exact coverage.
- **The constant-hazard assumption** in the SC/VSC model understates
  lap-1 risk specifically — real deployments cluster in the opening laps
  (accidents, first-corner incidents) — a known mis-specification, not an
  assumption believed to be exactly true.

**External validity** — how far do the fitted numbers travel beyond the
races they were fitted on?

- **Degradation slopes are not stable across seasons** (§4.1, within-stint
  R² frequently negative out of sample): a slope fitted on two editions of
  a race routinely fails to predict a third. Any in-race application would
  need online re-estimation from live laps, not a frozen historical
  coefficient. A companion audit
  ([`reports/generalization_audit.md`](generalization_audit.md)) extends
  this exact test to pit loss and neutralisation occurrence across all
  three series in this project and finds the answer depends on the
  quantity: pit loss, closer to a fixed procedural constant, transfers
  far better than either fitted trend.
- **Small SC samples** (6-8 editions per circuit) mean the reported
  posteriors are honestly wide rather than falsely precise, but a wide
  interval is still a limit on what the point estimate alone can support.

**Construct validity** — does the simulator's objective, and the audit's
comparison, actually capture "good strategy," or a narrower proxy for it?

- **No bunching, no track-position value, no red flags**: the simulator
  optimises expected race time under green-flag racing, not finishing
  position or the value of clean air; Case C measures the size of this
  gap directly (a ~6-7s bias at SC windows near the front, where track
  position matters most and the omission is largest).
- **Rivals are frozen to their historical plans** in the audit: a
  recommendation is scored against what actually happened, not against
  how a rival would have adapted to a different ego decision. The audit
  therefore measures "was this decision good given what rivals in fact
  did," a narrower and more answerable question than "was this decision
  game-theoretically optimal" — the latter is what
  `src/simulator/adversarial.py`'s reactive-rival model (§1) targets
  separately, and even that model's rival is limited to a pit-lap-and-
  compound response, not a full re-plan.

## 6. Future work

Online (in-race) re-estimation of the degradation slope; a two-bin
early/late SC hazard; a queueing model of SC bunching (which Case C shows
is first-order); rival reaction policies; extension to more circuits.

## 7. Reproducibility

Python 3.13, dependencies pinned in `requirements.lock` (fastf1 3.8.3,
pandas 2.3.3, numpy 2.5.1, scipy 1.18.0). FastF1 cache under
`data/cache/` (gitignored); derived datasets committed under
`data/derived/`. All stochastic code is seeded. The F1 layer this report
covers is tested by a dedicated subset of the project's 268 pytest tests
(ingestion, both models, the engine and the audit tooling, including
synthetic ground-truth recovery and leakage assertions); the remaining
tests cover the WEC/IMSA extension described in the top-level README, out
of scope for this report. Each phase's full output is a committed report
in `reports/`.

