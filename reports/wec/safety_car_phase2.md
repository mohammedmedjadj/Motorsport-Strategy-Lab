# Phase 2 (WEC) — Safety Car / Full Course Yellow probability model

Built on **33 WEC HYPERCAR-class races (2021-2026)** pulled in one aggregated
query (`data/derived/endurance/race_flags.csv`) — comparable to the F1 phase's
27 editions. Estimates are posterior means with 95% equal-tailed credible
intervals under a Jeffreys prior (`src/safety_car/model.py`, reused unchanged
from F1: Beta-Binomial occurrence, Gamma-Poisson rate). Only event *extraction*
is new, because this source encodes race control as a per-lap flag rather than
`TrackStatus` intervals.

## The Safety Car / FCY distinction

WEC's `SF` flag does not appear in IMSA at all. Checked across all 96 races in
both series: `SF` occurs only in WEC, in contiguous runs, adjacent to `FCY`
exactly **once** in the whole dataset — a genuine Safety Car procedure distinct
from the Full Course Yellow, not a second yellow flag. Both kinds are modelled
here, mirroring F1's SC/VSC split — see [Phase 0](data_availability_phase0.md)
for the full verification.

## Per-circuit results (3-6 editions each — the scoped circuits)

### Spa (6 editions)

- **SC**: 5/6 races (P = **0.786** [0.442, 0.981]) — rate 0.0193/lap [0.0111, 0.0297]
- FCY: 3/6 races (P = 0.500 [0.167, 0.833]) — rate 0.0076/lap [0.0029, 0.0145]
- Spa reaches for the Safety Car **more than twice as often** as an FCY.

### Fuji (4 editions)

- **SC**: 3/4 races (P = 0.700 [0.284, 0.972]) — rate 0.0074/lap [0.0029, 0.0141]
- FCY: 1/4 races (P = 0.300 [0.028, 0.716]) — rate 0.0029/lap [0.0005, 0.0073]

### Bahrain (4 editions)

- **SC**: 3/4 races (P = 0.700 [0.284, 0.972]) — rate 0.0057/lap [0.0020, 0.0114]
- FCY: 1/4 races (P = 0.300 [0.028, 0.716]) — rate 0.0036/lap [0.0009, 0.0083]

### Imola (3 editions — the shortest history of the scoped circuits)

- **SC**: 2/3 races (P = 0.625 [0.177, 0.961]) — rate 0.0056/lap [0.0013, 0.0127]
- FCY: 1/3 races (P = 0.375 [0.039, 0.823]) — rate 0.0024/lap [0.0002, 0.0074]
- With only 3 editions, these intervals are the widest of the eight scoped
  circuits (both series) — read them as a starting estimate, not a settled
  number.

## Series-wide result (all 33 races pooled)

| Kind | Races with event | Events | P(≥1 per race) | Rate per lap | Duration (laps) |
|---|---|---|---|---|---|
| FCY | 9 / 33 | 18 | 0.279 [0.144, 0.439] | 0.00251 [0.00150, 0.00378] | mean 1.8, max 5 |
| SC | 19 / 33 | 44 | **0.574** [0.407, 0.732] | 0.00605 [0.00440, 0.00795] | mean 3.6, max 18 |

**Every scoped circuit individually confirms the series-wide picture**, and
Spa most emphatically: the Safety Car is used **more often than the FCY at
every one of the four scoped circuits**, not just in the pooled series
average. This directly contradicts the naive expectation that FCY (the
"cheaper", less disruptive tool) would be preferred — WEC's actual practice
leans the other way.

**IMSA, for contrast, shows zero Safety Car races out of 63** — the two series
are not interchangeable; see [the IMSA report](../imsa/safety_car_phase2.md).

## Method and its limits

**Lap indexing.** Cars are spread around the circuit, so "lap N" is not one
instant. The race-level timeline takes the *modal* flag across all cars
reporting lap N — a race-progress proxy, not a wall-clock reconstruction.
Consequences, stated plainly:

- A neutralisation that never becomes the modal state on any lap is
  **invisible** to this method, so event counts are lower bounds.
- Durations are in **laps, not minutes** (Phase 3 measures the pace ratio
  directly), so these durations are not directly comparable to F1's SC/VSC
  durations.

**Pooling across race lengths.** The per-lap rate is normalised by exposure
(Spa/Fuji/Imola are 6h, Bahrain is 8h) and so is comparable across formats.
`P(≥1 per race)` is not: a longer race is mechanically more likely to see at
least one neutralisation. Use the rate for strategy work.

**3-6 editions per circuit is a structurally small sample**, comparable to F1's
6-8 per circuit — Imola's 3 editions in particular should be read as an early
estimate. **SC and FCY are modelled independently**, though in reality a Full
Course Yellow can escalate into a Safety Car, so the two rates are not fully
independent — the same caveat the F1 phase states for its own SC/VSC pair.
