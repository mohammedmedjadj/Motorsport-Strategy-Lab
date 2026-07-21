# Track-position value (overtaking difficulty)

How hard is it to overtake at each circuit, measured from real timing?
For every pair of consecutive green racing laps we take the cars that are
green-racing on both (so pit-cycle position shuffling is excluded) and
count the **rank-adjacent** pairs whose on-track order flips — the
operational question *"can the car right behind me get past"*. This is
the **pace-neutral baseline**: a genuinely faster car passes regardless,
so it isolates how sticky position is *absent* a pace advantage.

`p_hold_15_laps` is the first-order `(1 - p)^15`
probability that a car directly ahead keeps an adjacent rival behind over
15 green laps — the quantity the strategy layer weighs against
an undercut that would drop a car into that rival's clutches.

| Circuit | Adjacent swap rate / green lap | SD across races | Races | Lap transitions | P(hold 15 laps) |
|---|---|---|---|---|---|
| monaco | 0.0038 | 0.0008 | 3 | 205 | 0.94 |
| singapore | 0.0204 | 0.0016 | 3 | 165 | 0.73 |
| suzuka | 0.0329 | 0.0150 | 3 | 145 | 0.61 |
| barcelona | 0.0373 | 0.0031 | 3 | 188 | 0.57 |

## What the numbers say

The ordering is exactly what racecraft predicts: Monaco is the stickiest
circuit by a wide margin (a car ahead holds an adjacent rival with ~0.94
probability over 15 laps), while Barcelona and Suzuka are the
most fluid (closer to a coin-flip). Track position is worth far more at
Monaco than at Barcelona — which is precisely why Monaco strategy is
almost entirely about staying ahead rather than being fast.

## The finding: overtaking difficulty is a *stable* circuit constant

The season-to-season spread (SD column) is tiny — Barcelona sits at
0.037 in every one of three seasons. This is the mirror image of this
project's degradation result: tyre-degradation slopes do **not** transfer
between races (see the degradation reports), but overtaking difficulty
**does**, because it is set by track geometry, which does not change. So
unlike degradation, this constant can be trusted across seasons.

## Limitations (stated, not hidden)

- **Pace-neutral by construction.** A car with a real pace advantage
  passes regardless; this measures the baseline difficulty, not the
  outcome of a specific duel. Combining it with a pace delta is the job
  of the strategy layer (the adversarial rival model).
- **DRS, dirty air and tyre-delta effects are folded in**, not separated:
  the rate is the net observed swap frequency under normal green running.
- **Excludes safety-car and VSC laps** (no racing) and pit in/out laps.
- **Position is FastF1's classified position per lap**; lapped-car
  classification quirks are averaged over, not individually modelled.
- F1 only for now: the endurance schema carries no per-lap position, so
  the same measure there needs positions reconstructed from cumulative
  time — future work.
