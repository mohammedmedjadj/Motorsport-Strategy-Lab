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

## The finding: overtaking difficulty is a *mostly* stable circuit constant

The season-to-season spread (SD column) is small at three of the four
circuits — across the regulation-stable seasons the highest-to-lowest
ratio is 1.2x at Barcelona and Singapore and 1.7x at Monaco. That is the
mirror image of this project's degradation result: tyre-degradation slopes
do **not** transfer between races (see the degradation reports), but
overtaking difficulty largely **does**, because it is set by track
geometry, which does not change.

**Suzuka is the honest exception and is not smoothed over here:** it runs
0.0348 / 0.0502 / 0.0136 across the same three seasons, a 3.7x spread.
Whatever drives that (weather, a red flag, a race that ran away from the
field) is not track geometry, so Suzuka's constant deserves materially
less trust than the other three — and the per-season table below is
printed precisely so a reader can see that rather than take the pooled
number on faith.

## Per season, including the 2026 regulation era

The 2026 rules narrowed the cars and added active aero
with the explicit aim of making following and overtaking easier, so this
is a constant where a regulation effect is plausible in advance. The
headline table above deliberately excludes the new era (it feeds a
strategy layer that audits pre-era races), and this table reports it
separately:

| Circuit | Season | Era | Adjacent swap rate / green lap |
|---|---|---|---|
| barcelona | 2023 | old | 0.0387 |
| barcelona | 2024 | old | 0.0401 |
| barcelona | 2025 | old | 0.0329 |
| monaco | 2023 | old | 0.0049 |
| monaco | 2024 | old | 0.0036 |
| monaco | 2025 | old | 0.0029 |
| monaco | 2026 | new | 0.0032 |
| singapore | 2023 | old | 0.0219 |
| singapore | 2024 | old | 0.0182 |
| singapore | 2025 | old | 0.0212 |
| suzuka | 2023 | old | 0.0348 |
| suzuka | 2024 | old | 0.0502 |
| suzuka | 2025 | old | 0.0136 |
| suzuka | 2026 | new | 0.0469 |

**No regulation effect is detectable in this data, and at Suzuka it could
not be even in principle.** Both new-era races fall inside their own
circuit's pre-era range (Monaco 0.0032 against a 0.0029-0.0049 range;
Suzuka 0.0469 against 0.0136-0.0502). At Suzuka the ordinary
season-to-season swing is already 3.7x, which is far larger than any
plausible regulation effect, so a single new-era race there carries no
information about the rule change either way. Two races is also simply
too few. This is reported as a question the data cannot yet answer, not
as evidence the rules changed nothing.

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
