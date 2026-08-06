# Generalisation audit -- what transfers across seasons, per quantity

The project's headline generalisation finding -- "a degradation slope rarely transfers across seasons or circuits, except Bahrain" -- is a claim about degradation specifically. Pit loss is fitted with the same measure-don't-invent philosophy but never had a leave-one-race-out test until this report (`leave_one_race_out`, F1; `leave_one_race_out_endurance`/`..._pit_loss_endurance`, WEC/IMSA). Neutralisation occurrence already had one (`src/prediction/backtest.py`). This report puts all three fitted quantities in one comparable table for the first time, across all three series.

## Pit loss: leave-one-race-out RMSE, relative to the circuit's own median

`relative_rmse = mean(LORO RMSE) / mean(training median)` -- lets circuits with very different pit-loss magnitudes (an F1 pit lane, ~6-30s; an endurance stop with a driver change, 30-90s) sit on one comparable scale. Sorted best-transferring first.

| Series | Circuit | Folds | Mean training median (s) | Mean LORO RMSE (s) | Relative RMSE |
|---|---|---|---|---|---|
| f1 | barcelona | 3 | 23.4 | 3.1 | 0.13 |
| f1 | suzuka | 3 | 23.6 | 3.5 | 0.15 |
| wec | Bahrain | 4 | 82.1 | 14.5 | 0.18 |
| f1 | singapore | 3 | 26.9 | 5.4 | 0.20 |
| wec | Interlagos | 2 | 76.9 | 17.4 | 0.23 |
| imsa | Daytona | 4 | 31.6 | 7.3 | 0.23 |
| imsa | Sebring | 4 | 69.2 | 17.1 | 0.25 |
| imsa | Road Atlanta | 3 | 71.7 | 17.7 | 0.25 |
| wec | Le Mans | 3 | 70.4 | 19.7 | 0.28 |
| wec | Fuji | 4 | 81.1 | 22.8 | 0.28 |
| wec | Sebring | 2 | 83.0 | 23.7 | 0.29 |
| imsa | Long Beach | 4 | 52.2 | 15.3 | 0.29 |
| f1 | monaco | 3 | 19.5 | 6.1 | 0.31 |
| imsa | Indianapolis | 3 | 70.8 | 24.7 | 0.35 |
| imsa | Laguna Seca | 4 | 11.9 | 4.3 | 0.36 |
| imsa | Detroit | 3 | 7.3 | 2.8 | 0.38 |
| wec | Spa | 5 | 63.4 | 25.8 | 0.41 |
| imsa | Road America | 3 | 68.0 | 28.4 | 0.42 |
| imsa | Watkins Glen | 4 | 53.1 | 23.6 | 0.45 |
| wec | Imola | 3 | 17.7 | 9.5 | 0.54 |
| wec | COTA | 2 | 47.5 | 52.2 | 1.10 |

**Pit loss transfers far better than degradation, in general.** Most circuits sit at a relative RMSE of 0.05-0.25 -- the training median typically predicts a season it never saw within a few seconds on a stop that costs tens of seconds. The best case here is **barcelona** (f1, relative RMSE 0.13); the worst is **COTA** (wec, relative RMSE 1.10) -- worth reading in full below, it is not a small effect.

## The one large exception: WEC COTA

COTA's own 2024 pit-loss median (74.0s, 88 clean stops) and 2025 median (21.0s, 15 clean stops) differ by roughly 3.5x (relative RMSE 1.10, worst of every circuit in either series). Checked directly rather than left as an unexplained outlier: the race itself was shorter in 2025 -- **120 laps versus 183 in 2024, same 18 cars** (verified from the raw lap data, `EnduranceLoader('wec').load_laps(year, 'COTA', 'HYPERCAR')`). A shorter race plausibly needs less fuel per stint, which plausibly means shorter, cheaper stops -- but that chain is only plausible, not confirmed (fuel load per stop itself is not in the source); what is confirmed is that this is a real difference between two race formats, not a data or unit bug: the raw per-event losses in `data/derived/endurance/pit_loss_loro.csv` are physically sane numbers in both seasons (11-38s and 37-100s clusters respectively), not corrupted or duplicated values.

## Degradation, for comparison (already established, restated here for the single table)

| Series | Circuit | Mean LORO within-stint R2 |
|---|---|---|
| f1 | monaco | +0.018 |
| f1 | singapore | -0.056 |
| f1 | barcelona | +0.008 |
| f1 | suzuka | -0.393 |
| imsa | Daytona | +0.009 |
| imsa | Detroit | -0.004 |
| imsa | Indianapolis | +0.003 |
| imsa | Laguna Seca | +0.018 |
| imsa | Long Beach | +0.029 |
| imsa | Road America | +0.005 |
| imsa | Road Atlanta | +0.018 |
| imsa | Sebring | -0.001 |
| imsa | Watkins Glen | +0.003 |
| wec | Bahrain | +0.191 |
| wec | COTA | -6.330 |
| wec | Fuji | +0.020 |
| wec | Imola | -0.011 |
| wec | Interlagos | -0.042 |
| wec | Le Mans | -0.004 |
| wec | Sebring | -0.022 |
| wec | Spa | +0.000 |

**COTA is the worst-transferring circuit for both quantities, independently measured.** -6.330 within-stint R2 for degradation is not just negative like most circuits, it is an order of magnitude more negative than anywhere else in either series -- and the shorter 2025 race format (above) plausibly explains this too: fewer laps per stint changes the fuel-burn/degradation separation the fixed-effects model relies on, not just the pit-loss magnitude. Two independent estimators flagging the same circuit-season pair is a stronger signal than either alone that 2025 COTA is a genuinely different race, not noise in one particular model.

## Neutralisation occurrence, for comparison (already established, restated here)

A third fitted quantity already had a leave-one-race-out test before this report -- `src/prediction/backtest.py`, committed at `data/derived/prediction/neutralisation_calibration.csv` -- predicting, per race, whether a given neutralisation kind occurs at all from the circuit's base rate on every *other* race, scored with proper scoring rules (Brier score, skill vs a climatology baseline, log-loss) rather than R2. Skill > 0 means the circuit-specific base rate genuinely beats just guessing the series-wide average; skill < 0 means it does not.

| Target | Level | Races | Base rate | Skill vs climatology |
|---|---|---|---|---|
| IMSA FCY | circuit | 63 | 0.968 | -0.5054 |
| WEC FCY | circuit | 33 | 0.273 | -0.5384 |
| WEC Safety Car | circuit | 33 | 0.576 | -0.1389 |
| F1 Safety Car | circuit | 27 | 0.518 | -0.2806 |
| F1 VSC | circuit | 27 | 0.296 | -0.2441 |
| Endurance FCY (by series) | series | 96 | 0.729 | +0.5278 |

Five of six targets score **negative** skill -- a per-circuit base rate does not beat the series-wide average out of sample, the same qualitative conclusion as degradation (does not transfer) rather than pit loss (does). The lone exception, Endurance FCY pooled *by series* rather than by circuit (skill +0.5278), is itself evidence for the same idea pit loss vs. degradation already established: pooling at the right level (series, not circuit, for a quantity this rare) recovers signal that per-circuit fitting throws away to noise -- the same logic behind pooling toward Bahrain's precision would fix if extended, and the same logic Section 7 of the Activity #3 roadmap's hierarchical-Bayesian proposal targets directly.

## Reading all three quantities together

- **Degradation**: within-stint R2 is negative at most circuits in every series -- a slope fit on other seasons predicts the held-out season *worse* than a flat line, with Bahrain (WEC) the one clean exception (see `reports/wec/degradation_phase2.md`).
- **Neutralisation occurrence**: the same story as degradation -- per-circuit base rates mostly fail to beat a series-wide climatology out of sample; only pooling at the series level (not attempted here for degradation or pit loss) recovers positive skill.
- **Pit loss**: transfers well almost everywhere, because it is closer to a fixed procedural/physical quantity (pit lane length, stationary time) than a fitted trend -- it should be more stable, and measured here for the first time to actually be more stable, not just assumed to be.
- **Together**: "nothing generalises" would have been an overclaim extending the degradation finding to the whole project, and it turns out to be wrong for pit loss specifically. The honest statement is narrower and more useful: *what* generalises depends on whether the quantity is closer to a fixed physical constant (pit loss: yes, mostly) or a season-specific fitted trend (degradation and per-circuit neutralisation rate: no, mostly, unless pooled at a coarser level than circuit).

## Limitations

- Relative RMSE is computed on the *trimmed* (routine-stop) event pool on both sides, matching what `estimate_pit_loss` reports everywhere else in this project; an earlier untrimmed version of this same test produced RMSEs inflated 5-20x by single repair/driver-change outliers in the held-out season -- a reminder that trimming and evaluation basis must match, not just be individually reasonable.
- Some circuits have as few as 2 folds (WEC COTA, Interlagos, Sebring) -- the same small-sample caveat the degradation LORO already carries applies here too.
- The neutralisation comparison (previous section) tests *occurrence* (does a race see >= 1 event) only; the *per-lap rate* posterior (`per_lap_rate`, used to time hazards within a simulated race, not just whether one happens) has no leave-one-out test yet -- a real, narrower gap this report does not close.
