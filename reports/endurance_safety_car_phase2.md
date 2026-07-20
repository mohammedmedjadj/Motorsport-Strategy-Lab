# Phase 2 (endurance) — neutralisations in IMSA / WEC

Built on **96 races** (IMSA 2021-2026, WEC 2021-2026), which is a larger base
than the F1 phase's 27 editions. The estimators are the F1 layer's, reused
unchanged: Beta-Binomial for occurrence and Gamma-Poisson for the per-lap rate,
both with Jeffreys priors (`src/safety_car/model.py`). Only event *extraction*
is new, because this source encodes race control as a per-lap flag rather than
as `TrackStatus` intervals.

## Flag semantics (established empirically, not assumed)

| Flag | Race-laps | Races | Verdict |
|---|---|---|---|
| `GF` | 657 772 (car-laps) | all | Green — racing |
| `FCY` | 1 568 | 70 / 96 | **Full Course Yellow** — the dominant neutralisation, both series |
| `SF` | 157 | 19 | **Safety Car** — *WEC only* (2022-2026), contiguous runs, essentially never adjacent to FCY |
| `FF` | 124 | 89 | Chequered flag — median position **1.00** through the race. Not a neutralisation |
| `RF` | 4 | 2 | Red flag — too rare to model, excluded (as the F1 phase excludes red flags) |

`SF` was identified as a Safety Car, not a second yellow, because it occurs
**only in WEC**, in contiguous runs, and is adjacent to `FCY` exactly once in the
whole dataset — consistent with WEC running a full Safety Car procedure distinct
from FCY. This mirrors F1's SC/VSC split, so two kinds are modelled: `FCY`
(both series) and `SC` (WEC only).

## Results

| Series | Kind | Races with event | Events | P(≥1 per race) | Rate per lap | Duration (laps) |
|---|---|---|---|---|---|---|
| IMSA | FCY | 61 / 63 | 293 | **0.961** [0.902, 0.993] | 0.02097 [0.01864, 0.02343] | mean 5.2, max 119 |
| IMSA | SC | 0 / 63 | 0 | 0.008 [0.000, 0.039] | 0.00004 [0.00000, 0.00018] | — |
| WEC | FCY | 9 / 33 | 18 | 0.279 [0.144, 0.439] | 0.00251 [0.00150, 0.00378] | mean 1.8, max 5 |
| WEC | SC | 19 / 33 | 44 | **0.574** [0.407, 0.732] | 0.00605 [0.00440, 0.00795] | mean 3.6, max 18 |

**The two series are not interchangeable.** An IMSA race is near-certain to be
neutralised (96%, and roughly one FCY every 48 laps), whereas WEC reaches for the
Safety Car about twice as often as a Full Course Yellow. A strategy model
calibrated on one series would be badly wrong applied to the other.

The `IMSA / SC` row is the reason for the Jeffreys prior: a zero count returns
0.008 with an interval capped at 0.039 rather than a false certainty of exactly
zero — the same behaviour the F1 phase relies on for circuits with no observed
safety car. A regression test pins it.

The 119-lap IMSA maximum is real, not an artefact: it is the 2026 Daytona 24 h
(705 laps, 154 of them under FCY), and the per-lap car counts stay consistent
through the run.

## Method and its limits

**Lap indexing.** Cars are spread around the circuit, so "lap N" is not one
instant. The race-level timeline takes the *modal* flag across all cars reporting
lap N — a race-progress proxy, not a wall-clock reconstruction. Consequences,
stated plainly:

- A neutralisation that never becomes the modal state on any lap is **invisible**
  to this method, so event counts are lower bounds.
- Durations are in **laps, not minutes**, and a lap under caution is far slower
  than a green lap, so these durations are not directly comparable to F1's.

**Pooling across race lengths.** The per-lap rate is normalised by exposure and
so is comparable across formats. `P(≥1 per race)` is **not**: it pools 2 h 40
sprints with 24 h races, where a long race is mechanically far more likely to see
a caution. Use the rate for strategy work; read the occurrence column as a
descriptive summary of the calendar as actually run.

**No per-circuit split yet.** Unlike the F1 phase, which models each circuit
separately, this pools every event in a series. Some circuits (Daytona, Sebring)
are plainly more caution-prone than others; splitting needs the per-circuit
sample sizes checked first, exactly as Phase 0 did for the data itself.
