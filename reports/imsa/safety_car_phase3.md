# Phase 2 (IMSA) — Full Course Yellow probability model

Built on **63 IMSA GTP-class races (2021-2026)** pulled in one aggregated query
(`data/derived/endurance/race_flags.csv`) — larger than the F1 phase's 27
editions. Estimates are posterior means with 95% equal-tailed credible
intervals under a Jeffreys prior (`src/safety_car/model.py`, reused unchanged
from F1: Beta-Binomial occurrence, Gamma-Poisson rate). Only event *extraction*
is new, because this source encodes race control as a per-lap flag rather than
`TrackStatus` intervals — see [Phase 0](data_availability_phase0.md) for how
`FCY` was distinguished from the chequered flag (`FF`) and red flag (`RF`).

IMSA shows **no Safety Car flag at all** (that is a WEC-only procedure — see
[the WEC report](../wec/safety_car_phase3.md)); only Full Course Yellow is
modelled here.

## Per-circuit results (4-6 editions each — the scoped circuits)

### Watkins Glen (5 editions, comparable sample to F1's 6-8 per circuit)

- FCY: **5/5 races** (P = 0.917 [0.621, 1.000]) — rate 0.0423/lap [0.0297, 0.0571]
- Durations (laps): n=36, i.e. roughly 7 FCY periods per race on average

### Sebring (6 editions)

- FCY: **6/6 races** (P = 0.929 [0.670, 1.000]) — rate 0.0261/lap [0.0196, 0.0335]
- Durations (laps): n=53 — the lower per-lap rate than Watkins Glen is
  consistent with Sebring's much longer race distance diluting the same
  absolute FCY frequency

### Mosport (4 editions)

- FCY: **4/4 races** (P = 0.900 [0.555, 1.000]) — rate 0.0349/lap [0.0201, 0.0536]
- Durations (laps): n=16

### Road America (5 editions)

- FCY: **5/5 races** (P = 0.917 [0.621, 1.000]) — rate 0.0503/lap [0.0296, 0.0764]
  — the **highest** rate of the four scoped circuits
- Durations (laps): n=17

## Series-wide result (all 63 races pooled)

| Kind | Races with event | Events | P(≥1 per race) | Rate per lap | Duration (laps) |
|---|---|---|---|---|---|
| FCY | 61 / 63 | 293 | **0.961** [0.902, 0.993] | 0.02097 [0.01864, 0.02343] | mean 5.2, max 119 |

**Every scoped circuit individually confirms the series-wide picture**: an IMSA
race is essentially certain to see at least one FCY (all four circuits sit at
90-93% on their own small samples, consistent with the pooled 96%). The
119-lap maximum duration is real, not an artefact: it is the 2026 Daytona 24h
(705 laps, 154 of them under FCY), with car counts staying consistent through
the run.

## Method and its limits

**Lap indexing.** Cars are spread around the circuit, so "lap N" is not one
instant. The race-level timeline takes the *modal* flag across all cars
reporting lap N — a race-progress proxy, not a wall-clock reconstruction.
Consequences, stated plainly:

- A neutralisation that never becomes the modal state on any lap is
  **invisible** to this method, so event counts are lower bounds.
- Durations are in **laps, not minutes**, and a lap under caution is far
  slower than a green lap (Phase 3 measures the pace ratio directly), so these
  durations are not directly comparable to F1's SC/VSC durations.

**Pooling across race lengths.** The per-lap rate is normalised by exposure and
so is comparable across formats (sprint vs 12/24h). `P(≥1 per race)` is
**not**: a 12/24h race is mechanically far more likely to see at least one FCY
than a 2h40 sprint regardless of the true underlying rate. Use the rate for
strategy work; read the occurrence column as a descriptive summary of the
calendar as actually run.

**5-6 editions per circuit is a structurally small sample**, exactly as F1's
6-8 editions per circuit are — the credible intervals above are wide, and that
width is the honest result, not a modelling failure.
