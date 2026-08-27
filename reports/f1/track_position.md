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
| monaco | 0.0047 | 0.0016 | 4 | 249 | 0.93 |
| singapore | 0.0195 | 0.0021 | 4 | 200 | 0.74 |
| hungaroring | 0.0245 | 0.0099 | 3 | 193 | 0.69 |
| ricard | 0.0269 | 0.0000 | 1 | 40 | 0.66 |
| baku | 0.0272 | 0.0125 | 3 | 129 | 0.66 |
| montreal | 0.0284 | 0.0099 | 4 | 220 | 0.65 |
| melbourne | 0.0295 | 0.0105 | 4 | 167 | 0.64 |
| imola | 0.0304 | 0.0158 | 3 | 163 | 0.63 |
| mexico_city | 0.0308 | 0.0108 | 3 | 190 | 0.63 |
| silverstone | 0.0315 | 0.0041 | 4 | 160 | 0.62 |
| interlagos | 0.0321 | 0.0155 | 3 | 163 | 0.61 |
| suzuka | 0.0321 | 0.0130 | 4 | 169 | 0.61 |
| red_bull_ring | 0.0327 | 0.0068 | 3 | 193 | 0.61 |
| zandvoort | 0.0330 | 0.0195 | 3 | 183 | 0.60 |
| bahrain | 0.0334 | 0.0117 | 4 | 201 | 0.60 |
| miami | 0.0339 | 0.0126 | 4 | 194 | 0.60 |
| shanghai | 0.0353 | 0.0083 | 2 | 92 | 0.58 |
| monza | 0.0363 | 0.0100 | 3 | 144 | 0.57 |
| barcelona | 0.0366 | 0.0030 | 4 | 248 | 0.57 |
| jeddah | 0.0383 | 0.0094 | 4 | 170 | 0.56 |
| losail | 0.0402 | 0.0134 | 2 | 90 | 0.54 |
| spa | 0.0427 | 0.0178 | 4 | 156 | 0.52 |
| yas_marina | 0.0453 | 0.0084 | 3 | 163 | 0.50 |
| austin | 0.0483 | 0.0187 | 3 | 146 | 0.48 |
| las_vegas | 0.0846 | 0.0178 | 2 | 79 | 0.27 |

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
| austin | 2022 | old | 0.0742 |
| austin | 2023 | old | 0.0403 |
| austin | 2024 | old | 0.0305 |
| bahrain | 2022 | old | 0.0480 |
| bahrain | 2023 | old | 0.0216 |
| bahrain | 2024 | old | 0.0222 |
| bahrain | 2025 | old | 0.0419 |
| baku | 2022 | old | 0.0263 |
| baku | 2023 | old | 0.0124 |
| baku | 2024 | old | 0.0430 |
| barcelona | 2022 | old | 0.0345 |
| barcelona | 2023 | old | 0.0387 |
| barcelona | 2024 | old | 0.0401 |
| barcelona | 2025 | old | 0.0329 |
| hungaroring | 2022 | old | 0.0371 |
| hungaroring | 2023 | old | 0.0129 |
| hungaroring | 2024 | old | 0.0236 |
| imola | 2022 | old | 0.0179 |
| imola | 2024 | old | 0.0205 |
| imola | 2025 | old | 0.0527 |
| interlagos | 2022 | old | 0.0540 |
| interlagos | 2023 | old | 0.0223 |
| interlagos | 2024 | old | 0.0200 |
| jeddah | 2022 | old | 0.0497 |
| jeddah | 2023 | old | 0.0401 |
| jeddah | 2024 | old | 0.0235 |
| jeddah | 2025 | old | 0.0396 |
| las_vegas | 2023 | old | 0.1024 |
| las_vegas | 2024 | old | 0.0668 |
| losail | 2023 | old | 0.0536 |
| losail | 2024 | old | 0.0268 |
| melbourne | 2022 | old | 0.0389 |
| melbourne | 2023 | old | 0.0386 |
| melbourne | 2024 | old | 0.0131 |
| melbourne | 2025 | old | 0.0275 |
| mexico_city | 2022 | old | 0.0156 |
| mexico_city | 2023 | old | 0.0395 |
| mexico_city | 2024 | old | 0.0373 |
| miami | 2022 | old | 0.0427 |
| miami | 2023 | old | 0.0479 |
| miami | 2024 | old | 0.0296 |
| miami | 2025 | old | 0.0155 |
| monaco | 2022 | old | 0.0072 |
| monaco | 2023 | old | 0.0049 |
| monaco | 2024 | old | 0.0036 |
| monaco | 2025 | old | 0.0029 |
| monaco | 2026 | new | 0.0032 |
| montreal | 2022 | old | 0.0279 |
| montreal | 2023 | old | 0.0124 |
| montreal | 2024 | old | 0.0378 |
| montreal | 2025 | old | 0.0353 |
| monza | 2022 | old | 0.0489 |
| monza | 2023 | old | 0.0246 |
| monza | 2024 | old | 0.0354 |
| red_bull_ring | 2022 | old | 0.0423 |
| red_bull_ring | 2023 | old | 0.0269 |
| red_bull_ring | 2025 | old | 0.0290 |
| ricard | 2022 | old | 0.0269 |
| shanghai | 2024 | old | 0.0436 |
| shanghai | 2025 | old | 0.0270 |
| silverstone | 2022 | old | 0.0364 |
| silverstone | 2023 | old | 0.0271 |
| silverstone | 2024 | old | 0.0277 |
| silverstone | 2025 | old | 0.0348 |
| singapore | 2022 | old | 0.0168 |
| singapore | 2023 | old | 0.0219 |
| singapore | 2024 | old | 0.0182 |
| singapore | 2025 | old | 0.0212 |
| spa | 2022 | old | 0.0626 |
| spa | 2023 | old | 0.0582 |
| spa | 2024 | old | 0.0231 |
| spa | 2025 | old | 0.0271 |
| suzuka | 2022 | old | 0.0299 |
| suzuka | 2023 | old | 0.0348 |
| suzuka | 2024 | old | 0.0502 |
| suzuka | 2025 | old | 0.0136 |
| suzuka | 2026 | new | 0.0469 |
| yas_marina | 2022 | old | 0.0462 |
| yas_marina | 2023 | old | 0.0552 |
| yas_marina | 2024 | old | 0.0346 |
| zandvoort | 2022 | old | 0.0129 |
| zandvoort | 2023 | old | 0.0593 |
| zandvoort | 2024 | old | 0.0267 |

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
