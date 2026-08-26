# ELMS — Phase 2: degradation

*ELMS only, and per class: `LMP2` and `LMP2 Pro/Am` are fitted separately and
never pooled. Before 2023 the `LMP2` label covers every entry; from 2023 it
means the professional subset only ([phase 0](data_availability_phase0.md) §3).*

## Specification

Identical to the WEC and IMSA fits, which is the point — a series is added by
scoping data, not by writing a new model:

    lap_time = a_{car,driver} + n · tyre_age + eps

`n` is the **net within-stint slope**: fuel gain and tyre loss combined.
Standard errors are cluster-robust by car with a `t(G−1)` reference. ELMS
fields run 7–17 cars, so that reference is doing real work rather than being a
formality — at 7 cars it is a `t(6)`, whose 95% interval is 22% wider than the
normal's.

## Fitted slopes

| | LMP2 | LMP2 Pro/Am |
|---|---|---|
| race-seasons | 25 | 17 |
| median net slope | **+0.0161 s/lap** | **+0.0205 s/lap** |
| races fitting a negative slope | 7 of 25 | 5 of 17 |
| steepest | +0.0751 | +0.0832 |
| flattest | −0.2134 (Portimao 2023) | −0.2979 (Portimao 2023) |

For comparison on the same code: WEC HYPERCAR +0.0139, IMSA GTP +0.0166, IMSA
GTD +0.0200.

**The negative fits are a known model defect, not a measurement.** Portimao
2023 returns −0.213 s/lap for a tyre that is wearing, because the track dries
by 17.8 s a lap over the race and the model has no term carrying race time.
Full diagnosis, including an attempted correction that was built, validated on
synthetic data, and then **withdrawn because it made the real-data refit
worse**, is in
[`reports/track_evolution_omitted_variable.md`](../track_evolution_omitted_variable.md).

Read every slope here as a lower bound.

## Fuel and degradation are not separable — in any race

**0 of 42 races** clear the separability threshold, against IMSA's 6 of 140
(all Sebring) and WEC's 0 of 28. Teams change tyres at essentially every fuel
stop, so `laps_since_refuel` and `tyre_age` move together after fixed effects
and fitting both yields a collinear ridge rather than a measurement.

ELMS being the cleanest zero of the three is consistent with its format: no
ELMS round in scope is long enough to need the fuel-only splash stops that make
Sebring's 12 hours the single exception anywhere in this project.

## The control experiment, and it comes back negative

Phase 0 gave a falsifiable reason to prefer ELMS over more Hypercar or GTP
data. LMP2 is close to a one-make formula — Oreca 07 chassis, Gibson engine —
where Hypercar and GTP are manufacturer prototypes equalised by Balance of
Performance. The season-to-season instability of degradation slopes measured
everywhere in this project had an obvious candidate cause in heterogeneous,
BoP-adjusted machinery. **A near-spec field is the control: if slopes still
fail to transfer in LMP2, the instability is not the hardware.**

Leave-one-race-out mean within-stint R², per circuit:

| circuit | LMP2 | LMP2 Pro/Am |
|---|---|---|
| Barcelona | +0.035 | +0.027 |
| Imola | −0.001 | −0.003 |
| Paul Ricard | −0.011 | −0.011 |
| Portimao | **−0.067** | **−0.455** |
| Spa | −0.004 | −0.012 |

Every value is at or below zero except two indistinguishable from it. A slope
fitted on a circuit's other seasons explains **none** of the held-out season's
within-stint variance, and at Portimao it is worse than predicting the mean.

**This closes the hypothesis.** The instability survives on a field where the
chassis and engine are the same for everyone, so it is not caused by
heterogeneous, BoP-adjusted machinery. It is a negative result and it is the
most useful thing this series contributed.

Bahrain — the one WEC circuit whose slope genuinely transfers — is an
exception rather than the best case of a general rule. It is not the only one
in the project: IMSA's Lime Rock transfers better in both GT3 classes (+0.573
and +0.497), which is a fact about short circuits with cheap stops rather than
about prototypes.

Note the omitted race-time term makes this conclusion *more* secure rather than
less: a trend that differs by race is one more reason fits do not transfer, so
correcting it could only reduce the failure, never create it.

## Reproducing

```bash
python scripts/run_endurance_models.py
```

Writes `endurance_degradation_fits.csv` and `endurance_degradation_loro.csv`.
The near-spec control result is pinned in `tests/test_endurance_artifacts.py`.
