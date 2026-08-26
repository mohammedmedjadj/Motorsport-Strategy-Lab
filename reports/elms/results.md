# ELMS — measured results

*ELMS only. It shares its source and this project's code with WEC and IMSA and
shares no fitted number with either. Both LMP2 classes are modelled
separately; see [`data_availability_phase0.md`](data_availability_phase0.md)
for why, and [`crew_rating_findings.md`](crew_rating_findings.md) for the
crew comparison that separation made possible.*

## 1. Scope

| | LMP2 | LMP2 Pro/Am |
|---|---|---|
| Race-seasons | 25 | 17 |
| Seasons | 2021–2025 | 2023–2025 |
| Circuits | 9 | 8 |
| Median net slope | +0.0161 s/lap | +0.0205 s/lap |
| Races fitting a negative slope | 7 of 25 | 5 of 17 |

52,472 race laps in total, 69.6% of them kept for modelling (median per race).
Standard errors are cluster-robust by car with a `t(G−1)` reference; ELMS
fields run 7–17 cars, so that reference is doing real work.

## 2. The control experiment, and it comes back negative

Phase 0 gave a scientific reason to prefer ELMS over more Hypercar or GTP
data, and it was a specific, falsifiable one:

> ELMS's prototype class is **LMP2**, close to a one-make formula (Oreca 07
> chassis, Gibson engine) where Hypercar and GTP are manufacturer prototypes
> equalised by Balance of Performance. The degradation instability this
> project measured in F1 and endurance — slopes that fail to transfer between
> seasons — has an obvious candidate explanation in heterogeneous,
> BoP-adjusted machinery. **A near-spec field is the natural control: if
> slopes still fail to transfer in LMP2, the instability is a property of the
> data, not of the hardware.**

They still fail. Leave-one-race-out mean within-stint R², per circuit:

| circuit | LMP2 | LMP2 Pro/Am |
|---|---|---|
| Barcelona | +0.035 | +0.027 |
| Imola | −0.001 | −0.003 |
| Paul Ricard | −0.011 | −0.011 |
| Portimao | **−0.067** | **−0.455** |
| Spa | −0.004 | −0.012 |

Every value is at or below zero except two that are indistinguishable from it.
A pooled slope fitted on a circuit's other seasons explains **none** of the
held-out season's within-stint variance, and at Portimao it is actively worse
than predicting the mean.

**This closes a hypothesis the project has carried since its F1 phase.** The
season-to-season instability of degradation slopes is not an artefact of
heterogeneous, BoP-adjusted machinery: it survives on a field where the
chassis and engine are the same for everyone. Whatever drives it — track
evolution, weather, traffic, tyre allocation, or the genuine year-to-year
variation of a compound — is not the car.

It is a negative result, and it is the most useful thing ELMS contributed.
Bahrain is the one *WEC* circuit whose slope genuinely transfers, and IMSA's
Lime Rock GT3 classes transfer better still (+0.573 and +0.497). Both are
short circuits by the standards of their series. The exception is rare, but it
is not unique, and this document previously said it was.

## 3. Fuel and degradation are not separable, at all

**0 of 42 races** clear the separability threshold — a cleaner result than
IMSA's (6 of 140) or WEC's (0 of 28). Teams change tyres at essentially every
fuel stop, so `laps_since_refuel` and `tyre_age` move together and fitting
both yields a collinear ridge. Only the net slope is reported, as everywhere
else in this project.

## 4. Stops and track position

Median measured pit loss **64.8 s** against a **24-lap** fuel range — an
expensive stop on a short tank, which is why ELMS is almost entirely
fuel-limited on stop count. The one exception is LMP2 at Mugello, whose 9.2 s
pit loss is the cheapest in the series; it is one of the nine entries behind
the cross-series rule in
[`reports/when_tyres_beat_fuel.md`](../when_tyres_beat_fuel.md).

Median adjacent-swap rate **0.0463** over 17 circuit-class entries, position
reconstructed from cumulative time within the class.

## 5. Neutralisations: a third regime

| series | races with ≥1 FCY | races with ≥1 SC | SC rate/lap |
|---|---|---|---|
| IMSA | 61 of 63 | 0 of 63 | 0.00004 (prior floor) |
| WEC | 9 of 33 | 19 of 33 | 0.00605 |
| **ELMS** | 15 of 29 | **23 of 29** | **0.01592** |

ELMS is the most Safety-Car-dominated of the three, ahead of WEC, where IMSA
records none at all. Three series, three regimes — the same conclusion each
time this project has checked: a pooled "endurance" neutralisation model would
describe none of them.

Getting these numbers required fixing `scripts/run_endurance_flags.py`, whose
query hard-coded `IN ('imsa', 'wec')`. That was caught by the `KeyError` guard
in `load_race_model` rather than by a suspicious result — without it, ELMS
models would have been built on a default Jeffreys prior and produced entirely
plausible stop plans from an invented neutralisation risk.

## 6. What is not here

- **Per-decision audit: now present** ([`audit_cases.md`](audit_cases.md)),
  covering Mugello 2024's double Safety Car stop in both classes.
- **Phase-by-phase report set: now present** — phases
  [0](data_availability_phase0.md), [1](data_quality_phase1.md),
  [2](degradation_phase2.md), [3](safety_car_phase3.md),
  [4](simulator_phase4.md) and [7](packaging_phase7.md), plus the
  [audit](audit_cases.md). No phase 5/6 equivalents: the audit *is* ELMS's
  phase 5, and this document plus the crew comparison serve as its phase 6.
- **No established crew effect**, and the ELMS test disagrees with IMSA's.
  See [`crew_rating_findings.md`](crew_rating_findings.md), which is explicit
  about what its p-value does and does not license.

## 7. Reproducing

```bash
python scripts/run_endurance_flags.py    # network: race-control flags
python scripts/run_endurance_models.py   # offline: fits, quality, LORO, traffic
python scripts/run_multistop.py          # offline: full-race plans
```

Every number above comes from the artifacts those three scripts write, all
committed. The ELMS-specific claims in §2 and §5 are pinned in
`tests/test_endurance_artifacts.py` and `tests/test_endurance_safety_car.py`.
