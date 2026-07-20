# Phase 1 (endurance) — degradation on IMSA / WEC

Fitted per race on green, non-pit, traffic-trimmed laps
(`src/degradation/endurance.py`), with car-**and-driver** fixed effects, since
endurance rotates drivers within a car and driver pace differences are large.

## Result

| Race | Class | Laps | Cars | Net slope (s/lap of tyre age) | 95% CI | RMSE |
|---|---|---|---|---|---|---|
| WEC Spa 2024 | HYPERCAR | 1 764 | 19 | **+0.042** | [+0.031, +0.053] | 1.42 s |
| IMSA Watkins Glen 2023 | GTP | 1 143 | 8 | −0.007 | [−0.018, +0.003] | 1.35 s |

Two honestly contrasting regimes: at Spa the net within-stint slope is clearly
positive; at Watkins Glen the interval **covers zero** — the car's fuel-burn gain
cancels the tyre loss, so there is no detectable *net* degradation.

## What "net slope" means, and why nothing finer is quoted

The reported coefficient is the **net** within-stint pace evolution: fuel gain
(car gets lighter → faster) *plus* tyre loss (rubber goes off → slower). The
model deliberately does **not** split those two.

That was not the original intent. The plan was that endurance's fuel-only stops
would reset a `laps_since_refuel` regressor while leaving `tyre_age` untouched,
decoupling the two and giving a cleaner identification than F1 enjoys. **The data
refuted it.** Teams overwhelmingly change tyres whenever they refuel:

| Race | Pit visits | Accompanied by a tyre change |
|---|---|---|
| IMSA Watkins Glen 2023 | 64 | 56 (**88%**) |
| WEC Spa 2024 | 97 | 90 (**93%**) |

So the two regressors move together, with a post-fixed-effects correlation of
**+0.99 (Watkins Glen)** and **+0.95 (Spa)**. Fitting both produces a collinear
ridge rather than a measurement — at Watkins Glen it returned a fuel slope of
−0.111 s/lap and a degradation slope of +0.108 s/lap, wide near-mirror-image
intervals summing to about the observed net of ~0. Quoting either number would be
fabricating a decomposition the data cannot support.

The decomposition is therefore kept only as a diagnostic. `EnduranceFit` exposes
`fuel_deg_correlation` and a `separable` flag (threshold |r| < 0.90); both races
report `separable = False`, and a regression test pins that so the guard cannot
quietly disappear.

This is the same discipline the F1 model applies to its own identification — the
difference is that F1's structure *does* support the split, and this data does
not. Should a race with a meaningful number of fuel-only stops appear, `separable`
will flip to True on its own and the decomposition becomes quotable.

## Modelling choices

- **Fuel proxy is laps since the last pit visit**, not lap number: endurance
  cars refuel, so fuel load is not monotone across a race as it is in F1.
- **Traffic trim.** Multi-class racing means a prototype stuck behind GT traffic
  loses seconds through no fault of its tyres. Laps slower than a car's own 90th
  percentile are dropped before fitting — the endurance analogue of F1's pace-lap
  filter. Cars with fewer than 20 usable green laps are excluded.
- **FCY / red-flag laps and every pit lap are excluded** outright.

## Limitations

- Single race per series so far; no cross-race validation yet, so these slopes
  are descriptive of these two races, **not** general circuit constants. The F1
  project's leave-one-race-out finding (slopes move materially between events)
  should be assumed to apply here until tested.
- `est_tire_age` is the upstream dataset's *estimate*, and it appears to advance
  on green laps only. Tyre compound is not available at all, so no per-compound
  split is possible.
- Classical homoscedastic standard errors, as in the F1 model.
- No stint-level pit-loss measurement yet: `pit_time` is a pit-visit duration,
  not the strategic time loss against a pace baseline.
