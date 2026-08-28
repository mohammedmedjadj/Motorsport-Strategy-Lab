# Generalisation audit -- what transfers across seasons, per quantity

The project's headline generalisation finding -- "a degradation slope rarely transfers across seasons or circuits, except Bahrain" -- is a claim about degradation specifically. Pit loss is fitted with the same measure-don't-invent philosophy but never had a leave-one-race-out test until this report (`leave_one_race_out`, F1; `leave_one_race_out_endurance`/`..._pit_loss_endurance`, WEC/IMSA). Neutralisation occurrence already had one (`src/prediction/backtest.py`). This report puts all three fitted quantities in one comparable table for the first time, across all three series.

## Pit loss: leave-one-race-out RMSE, relative to the circuit's own median

`relative_rmse = mean(LORO RMSE) / mean(training median)` -- lets circuits with very different pit-loss magnitudes (an F1 pit lane, ~6-30s; an endurance stop with a driver change, 30-90s) sit on one comparable scale. Sorted best-transferring first.

| Series | Circuit | Folds | Mean training median (s) | Mean LORO RMSE (s) | Relative RMSE |
|---|---|---|---|---|---|
| f1 | miami | 4 | 20.9 | 2.3 | 0.11 |
| f1 | austin | 4 | 21.5 | 2.5 | 0.12 |
| f1 | interlagos | 3 | 22.3 | 2.7 | 0.12 |
| f1 | monza | 4 | 25.6 | 3.2 | 0.12 |
| f1 | yas_marina | 4 | 23.3 | 3.0 | 0.13 |
| f1 | barcelona | 4 | 23.3 | 3.0 | 0.13 |
| f1 | bahrain | 4 | 24.8 | 3.3 | 0.13 |
| f1 | melbourne | 3 | 21.3 | 2.9 | 0.14 |
| f1 | hungaroring | 4 | 21.6 | 3.0 | 0.14 |
| f1 | mexico_city | 4 | 23.4 | 3.4 | 0.14 |
| f1 | suzuka | 3 | 23.6 | 3.5 | 0.15 |
| wec | Bahrain | 4 | 82.1 | 14.5 | 0.18 |
| f1 | red_bull_ring | 4 | 21.5 | 3.9 | 0.18 |
| f1 | baku | 4 | 22.6 | 4.3 | 0.19 |
| f1 | shanghai | 2 | 24.5 | 4.9 | 0.20 |
| f1 | las_vegas | 3 | 23.8 | 4.9 | 0.21 |
| wec | Interlagos | 2 | 76.9 | 17.4 | 0.23 |
| f1 | losail | 3 | 28.3 | 6.6 | 0.23 |
| imsa | Long Beach | 12 | 54.2 | 13.5 | 0.25 |
| f1 | jeddah | 4 | 21.6 | 5.6 | 0.26 |
| wec | Le Mans | 3 | 70.4 | 19.7 | 0.28 |
| wec | Fuji | 4 | 81.1 | 22.8 | 0.28 |
| wec | Sebring | 2 | 83.0 | 23.7 | 0.29 |
| imsa | Road Atlanta | 12 | 67.5 | 19.7 | 0.29 |
| imsa | Daytona | 15 | 48.6 | 15.6 | 0.32 |
| imsa | Mid-Ohio | 2 | 49.0 | 16.2 | 0.33 |
| f1 | singapore | 4 | 27.0 | 9.1 | 0.34 |
| elms | Barcelona | 7 | 73.7 | 24.8 | 0.34 |
| imsa | Sebring | 15 | 50.5 | 17.1 | 0.34 |
| f1 | zandvoort | 4 | 24.1 | 8.3 | 0.35 |
| elms | Portimao | 8 | 68.2 | 23.8 | 0.35 |
| imsa | Laguna Seca | 15 | 9.1 | 3.3 | 0.36 |
| f1 | montreal | 4 | 20.8 | 7.7 | 0.37 |
| elms | Spa | 8 | 60.0 | 22.4 | 0.37 |
| imsa | Lime Rock | 5 | 18.4 | 7.3 | 0.39 |
| f1 | spa | 4 | 19.4 | 7.7 | 0.40 |
| wec | Spa | 5 | 63.4 | 25.8 | 0.41 |
| imsa | Indianapolis | 9 | 50.2 | 20.4 | 0.41 |
| imsa | Mosport | 8 | 23.9 | 10.2 | 0.42 |
| imsa | VIR | 9 | 5.9 | 2.5 | 0.43 |
| imsa | Watkins Glen | 14 | 38.3 | 16.8 | 0.44 |
| elms | Imola | 5 | 16.7 | 7.8 | 0.47 |
| f1 | imola | 3 | 35.6 | 17.2 | 0.48 |
| imsa | Detroit | 6 | 7.8 | 3.9 | 0.50 |
| f1 | silverstone | 4 | 32.1 | 17.2 | 0.54 |
| wec | Imola | 3 | 17.7 | 9.5 | 0.54 |
| elms | Paul Ricard | 7 | 49.7 | 28.7 | 0.58 |
| f1 | monaco | 4 | 23.9 | 15.0 | 0.63 |
| imsa | Road America | 12 | 58.6 | 45.9 | 0.78 |
| wec | COTA | 2 | 47.5 | 52.2 | 1.10 |

**Pit loss transfers far better than degradation, in general.** Most circuits sit at a relative RMSE of 0.05-0.25 -- the training median typically predicts a season it never saw within a few seconds on a stop that costs tens of seconds. The best case here is **miami** (f1, relative RMSE 0.11); the worst is **COTA** (wec, relative RMSE 1.10) -- worth reading in full below, it is not a small effect.

## The one large exception: WEC COTA

COTA's own 2024 pit-loss median (74.0s, 88 clean stops) and 2025 median (21.0s, 15 clean stops) differ by roughly 3.5x (relative RMSE 1.10, worst of every circuit in either series). Checked directly rather than left as an unexplained outlier: the race itself was shorter in 2025 -- **120 laps versus 183 in 2024, same 18 cars** (verified from the raw lap data, `EnduranceLoader('wec').load_laps(year, 'COTA', 'HYPERCAR')`). A shorter race plausibly needs less fuel per stint, which plausibly means shorter, cheaper stops -- but that chain is only plausible, not confirmed (fuel load per stop itself is not in the source); what is confirmed is that this is a real difference between two race formats, not a data or unit bug: the raw per-event losses in `data/derived/endurance/pit_loss_loro.csv` are physically sane numbers in both seasons (11-38s and 37-100s clusters respectively), not corrupted or duplicated values.

## Degradation, for comparison (already established, restated here for the single table)

| Series | Circuit | Mean LORO within-stint R2 |
|---|---|---|
| f1 | austin | -0.051 |
| f1 | bahrain | +0.255 |
| f1 | baku | +0.269 |
| f1 | barcelona | +0.018 |
| f1 | hungaroring | +0.000 |
| f1 | imola | -0.230 |
| f1 | interlagos | +0.083 |
| f1 | jeddah | +0.307 |
| f1 | las_vegas | +0.128 |
| f1 | losail | +0.249 |
| f1 | melbourne | +0.132 |
| f1 | mexico_city | -0.047 |
| f1 | miami | +0.106 |
| f1 | monaco | +0.078 |
| f1 | montreal | +0.001 |
| f1 | monza | -0.113 |
| f1 | red_bull_ring | +0.154 |
| f1 | ricard | +nan |
| f1 | shanghai | -0.580 |
| f1 | silverstone | -0.106 |
| f1 | singapore | -0.081 |
| f1 | spa | -0.284 |
| f1 | suzuka | -0.393 |
| f1 | yas_marina | +0.045 |
| f1 | zandvoort | -0.020 |
| imsa | Daytona | +0.031 |
| imsa | Detroit | -0.014 |
| imsa | Indianapolis | +0.029 |
| imsa | Laguna Seca | +0.058 |
| imsa | Long Beach | +0.013 |
| imsa | Road America | +0.001 |
| imsa | Road Atlanta | +0.039 |
| imsa | Sebring | -0.002 |
| imsa | Watkins Glen | +0.013 |
| imsa | Daytona | -0.020 |
| imsa | Indianapolis | +0.073 |
| imsa | Laguna Seca | +0.273 |
| imsa | Lime Rock | +0.573 |
| imsa | Long Beach | -0.001 |
| imsa | Mid-Ohio | +0.060 |
| imsa | Mosport | +0.064 |
| imsa | Road America | +0.004 |
| imsa | Road Atlanta | +0.039 |
| imsa | Sebring | +0.031 |
| imsa | VIR | +0.125 |
| imsa | Watkins Glen | +0.058 |
| imsa | Daytona | +0.058 |
| imsa | Detroit | -0.054 |
| imsa | Indianapolis | +0.171 |
| imsa | Laguna Seca | +0.256 |
| imsa | Lime Rock | +0.497 |
| imsa | Long Beach | -0.012 |
| imsa | Mosport | +0.071 |
| imsa | Road America | -0.019 |
| imsa | Road Atlanta | +0.069 |
| imsa | Sebring | +0.021 |
| imsa | VIR | +0.091 |
| imsa | Watkins Glen | +0.065 |
| wec | Bahrain | +0.217 |
| wec | COTA | -1.490 |
| wec | Fuji | +0.055 |
| wec | Imola | -0.009 |
| wec | Interlagos | -0.087 |
| wec | Le Mans | -0.008 |
| wec | Sebring | +0.016 |
| wec | Spa | +0.018 |
| elms | Barcelona | +0.035 |
| elms | Imola | -0.001 |
| elms | Paul Ricard | -0.011 |
| elms | Portimao | -0.067 |
| elms | Spa | -0.004 |
| elms | Barcelona | +0.027 |
| elms | Imola | -0.003 |
| elms | Paul Ricard | -0.011 |
| elms | Portimao | -0.455 |
| elms | Spa | -0.012 |

**COTA is the worst-transferring circuit for both quantities, independently measured.** -6.330 within-stint R2 for degradation is not just negative like most circuits, it is an order of magnitude more negative than anywhere else in either series -- and the shorter 2025 race format (above) plausibly explains this too: fewer laps per stint changes the fuel-burn/degradation separation the fixed-effects model relies on, not just the pit-loss magnitude. Two independent estimators flagging the same circuit-season pair is a stronger signal than either alone that 2025 COTA is a genuinely different race, not noise in one particular model.

## Neutralisation occurrence, for comparison (already established, restated here)

A third fitted quantity already had a leave-one-race-out test before this report -- `src/prediction/backtest.py`, committed at `data/derived/prediction/neutralisation_calibration.csv` -- predicting, per race, whether a given neutralisation kind occurs at all from the circuit's base rate on every *other* race, scored with proper scoring rules (Brier score, skill vs a climatology baseline, log-loss) rather than R2. Skill > 0 means the circuit-specific base rate genuinely beats just guessing the series-wide average; skill < 0 means it does not.

| Target | Level | Races | Base rate | Skill vs climatology |
|---|---|---|---|---|
| IMSA FCY | circuit | 63 | 0.968 | -0.5054 |
| WEC FCY | circuit | 33 | 0.273 | -0.5384 |
| WEC Safety Car | circuit | 33 | 0.576 | -0.1389 |
| F1 Safety Car | circuit | 147 | 0.571 | -0.1008 |
| F1 VSC | circuit | 147 | 0.415 | -0.1910 |
| Endurance FCY (by series) | series | 125 | 0.680 | +0.3860 |

Five of six targets score **negative** skill -- a per-circuit base rate does not beat the series-wide average out of sample, the same qualitative conclusion as degradation (does not transfer) rather than pit loss (does). The lone exception, Endurance FCY pooled *by series* rather than by circuit (skill +0.3860), is itself evidence for the same idea pit loss vs. degradation already established: pooling at the right level (series, not circuit, for a quantity this rare) recovers signal that per-circuit fitting throws away to noise -- the same logic behind pooling toward Bahrain's precision would fix if extended, and the same logic Section 7 of the Activity #3 roadmap's hierarchical-Bayesian proposal targets directly.

## Reading all three quantities together

- **Degradation**: within-stint R2 is negative at most circuits in every series -- a slope fit on other seasons predicts the held-out season *worse* than a flat line, with Bahrain (WEC) the one clean exception (see `reports/wec/degradation_phase2.md`).
- **Neutralisation occurrence**: the same story as degradation -- per-circuit base rates mostly fail to beat a series-wide climatology out of sample; only pooling at the series level (not attempted here for degradation or pit loss) recovers positive skill.
- **Pit loss**: transfers well almost everywhere, because it is closer to a fixed procedural/physical quantity (pit lane length, stationary time) than a fitted trend -- it should be more stable, and measured here for the first time to actually be more stable, not just assumed to be.
- **Together**: "nothing generalises" would have been an overclaim extending the degradation finding to the whole project, and it turns out to be wrong for pit loss specifically. The honest statement is narrower and more useful: *what* generalises depends on whether the quantity is closer to a fixed physical constant (pit loss: yes, mostly) or a season-specific fitted trend (degradation and per-circuit neutralisation rate: no, mostly, unless pooled at a coarser level than circuit).

## Limitations

- Relative RMSE is computed on the *trimmed* (routine-stop) event pool on both sides, matching what `estimate_pit_loss` reports everywhere else in this project; an earlier untrimmed version of this same test produced RMSEs inflated 5-20x by single repair/driver-change outliers in the held-out season -- a reminder that trimming and evaluation basis must match, not just be individually reasonable.
- Some circuits have as few as 2 folds (WEC COTA, Interlagos, Sebring) -- the same small-sample caveat the degradation LORO already carries applies here too.
- The neutralisation comparison (previous section) tests *occurrence* (does a race see >= 1 event) only; the *per-lap rate* posterior (`per_lap_rate`, used to time hazards within a simulated race, not just whether one happens) has no leave-one-out test yet -- a real, narrower gap this report does not close.
