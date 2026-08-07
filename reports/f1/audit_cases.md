# Phase 5 — Retrospective decision audit

Five real decision moments replayed through the simulator (5000
draws, seed 20260712). Race states (compounds, tyre ages, gaps, rival
plans) are reconstructed from the committed lap data, not quoted from
memory. Rivals follow their real historical plans; the studied
driver's alternatives are simulated.

Reading guide: the model optimises **expected race time** under its
stated scope (no SC bunching, no red flags, no track-position /
overtaking model). Where reality hinged on exactly those effects, the
disagreement is the finding.

## Case A: Barcelona 2024 — Verstappen covers Norris (successful defence)

**State (measured from data):** end of lap 16/66, VER on SOFT age 19. Rivals: NOR (-4.8s, SOFT age 16, real plan: stop lap 23).

**Real decision:** Pitted lap 17 (SOFT age 20 -> MEDIUM); kept the lead and won.

**Question:** Was lap 17 inside the model's optimal window, given Norris's real plan (stop lap 23)?

**Model output** (pit_lap 0 = no further stop):

- Best median pit lap: **25** — recommended window (medians within 0.5s): **[24, 25, 26, 27]**.
- Outcome spread at the best lap (p10-p90): 265.5s — this is the honest uncertainty of any single-race outcome.
- vs NOR: P(ahead) = 0.67 at lap 25; maximised at lap 22 (0.73).
- **Verdict:** Real choice (lap 17): median cost +4.97s vs the model optimum (lap 25); OUTSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_NOR |
|---|---|---|---|---|---|---|
| 17 <- real | 4032.41 | 4094.41 | 3989.50 | 4263.50 | 0.42 | 0.66 |
| 24 | 4027.72 | 4094.89 | 3995.93 | 4261.88 | 0.03 | 0.70 |
| 25 | 4027.44 | 4095.20 | 3996.63 | 4262.10 | 0.02 | 0.67 |
| 26 | 4027.68 | 4095.54 | 3997.29 | 4262.97 | 0.02 | 0.64 |
| 27 | 4027.80 | 4095.92 | 3998.27 | 4263.46 | 0.02 | 0.61 |

## Case B: Barcelona 2024 — Norris's extended stint (failed overcut)

**State (measured from data):** end of lap 16/66, NOR on SOFT age 16. Rivals: VER (+4.8s, SOFT age 19, real plan: stop lap 17).

**Real decision:** Stayed out until lap 23 on SOFT (to age 23); rejoined behind and finished 2nd, +2.2s.

**Question:** Did staying out to lap 23 ever look optimal against Verstappen's real lap-17 stop?

**Model output** (pit_lap 0 = no further stop):

- Best median pit lap: **27** — recommended window (medians within 0.5s): **[26, 27, 28, 29, 30]**.
- Outcome spread at the best lap (p10-p90): 265.3s — this is the honest uncertainty of any single-race outcome.
- vs VER: P(ahead) = 0.37 at lap 27; maximised at lap 28 (0.37).
- **Verdict:** Real choice (lap 23): median cost +1.72s vs the model optimum (lap 27); OUTSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_VER |
|---|---|---|---|---|---|---|
| 23 <- real | 4026.37 | 4093.07 | 3993.75 | 4260.45 | 0.02 | 0.34 |
| 26 | 4024.85 | 4093.34 | 3995.46 | 4260.98 | 0.03 | 0.37 |
| 27 | 4024.65 | 4093.52 | 3996.07 | 4261.40 | 0.03 | 0.37 |
| 28 | 4024.73 | 4093.79 | 3996.74 | 4261.10 | 0.03 | 0.37 |
| 29 | 4024.73 | 4094.10 | 3997.43 | 4261.49 | 0.03 | 0.37 |
| 30 | 4025.05 | 4094.46 | 3998.07 | 4261.88 | 0.02 | 0.36 |

## Case C: Singapore 2023 — Sainz boxes under the lap-20 safety car

**State (measured from data):** end of lap 19/62, SAI on MEDIUM age 19 — SC currently deployed. Rivals: RUS (-6.4s, MEDIUM age 19, real plan: stop lap 20); NOR (-7.5s, MEDIUM age 19, real plan: stop lap 20).

**Real decision:** Pitted lap 20 under SC (MEDIUM age 20 -> HARD), as did the whole leading group; won the race.

**Question:** Does the model confirm that stopping immediately under the SC dominated staying out?

**Model output** (pit_lap 0 = no further stop):

- Best median pit lap: **35** — recommended window (medians within 0.5s): **[33, 34, 35, 36, 37, 38, 41]**.
- Outcome spread at the best lap (p10-p90): 346.7s — this is the honest uncertainty of any single-race outcome.
- vs RUS: P(ahead) = 0.93 at lap 35; maximised at lap 35 (0.93).
- vs NOR: P(ahead) = 0.95 at lap 35; maximised at lap 34 (0.95).
- **Verdict:** Real choice (lap 20): median cost +5.91s vs the model optimum (lap 35); OUTSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_RUS | p_ahead_NOR |
|---|---|---|---|---|---|---|---|
| 20 <- real | 4483.97 | 4511.78 | 4357.15 | 4701.17 | 0.00 | 0.81 | 0.86 |
| 33 | 4478.52 | 4506.04 | 4350.62 | 4696.79 | 0.02 | 0.93 | 0.95 |
| 34 | 4478.26 | 4505.79 | 4350.39 | 4696.74 | 0.03 | 0.93 | 0.95 |
| 35 | 4478.06 | 4505.60 | 4350.18 | 4696.93 | 0.04 | 0.93 | 0.95 |
| 36 | 4478.22 | 4505.53 | 4350.14 | 4697.07 | 0.07 | 0.93 | 0.95 |
| 37 | 4478.13 | 4505.53 | 4350.29 | 4696.57 | 0.07 | 0.93 | 0.94 |
| 38 | 4478.31 | 4505.59 | 4350.35 | 4696.58 | 0.07 | 0.92 | 0.94 |
| 41 | 4478.49 | 4506.24 | 4351.19 | 4697.03 | 0.04 | 0.90 | 0.92 |

## Case D: Singapore 2023 — Mercedes' VSC gamble (Russell, lap 44)

**State (measured from data):** end of lap 43/62, RUS on HARD age 23 — VSC currently deployed. Rivals: SAI (+0.9s, HARD age 23, real plan: no stop); NOR (-0.8s, HARD age 23, real plan: no stop).

**Real decision:** Pitted lap 44 under VSC (HARD age 24 -> MEDIUM), dropping P2 -> P4 to attack; caught the leaders but crashed on the last lap fighting for the podium.

**Question:** Was surrendering track position for fresh mediums time-optimal, and what does P(ahead) say about the win chance it bought?

**Model output** (pit_lap 0 = no further stop):

- Best median pit lap: **46** — recommended window (medians within 0.5s): **[45, 46]**.
- Outcome spread at the best lap (p10-p90): 191.6s — this is the honest uncertainty of any single-race outcome.
- vs SAI: P(ahead) = 0.31 at lap 46; maximised at lap 45 (0.51).
- vs NOR: P(ahead) = 0.40 at lap 46; maximised at lap 45 (0.61).
- **Verdict:** Real choice (lap 44): median cost +1.11s vs the model optimum (lap 46); OUTSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_SAI | p_ahead_NOR |
|---|---|---|---|---|---|---|---|
| 44 <- real | 1913.31 | 1954.57 | 1890.77 | 2087.41 | 0.00 | 0.48 | 0.58 |
| 45 | 1912.65 | 1953.97 | 1890.12 | 2086.85 | 0.47 | 0.51 | 0.61 |
| 46 | 1912.19 | 1957.45 | 1895.09 | 2086.70 | 0.14 | 0.31 | 0.40 |
| 0 | 1914.93 | 1954.98 | 1893.22 | 2081.77 | 0.33 | 0.42 | 0.56 |

## Case E: Monaco 2024 — Leclerc mid-race (the model's blind spot)

**State (measured from data):** end of lap 40/78, LEC on HARD age 39. Rivals: PIA (-1.6s, HARD age 40, real plan: no stop).

**Real decision:** Nobody pitted for the entire race: the lap-1 red flag allowed a free tyre change, and Monaco track position beats any pace gain. Leclerc won without stopping.

**Question:** What does a time-only model recommend here, and why must its answer be read as a documented limitation rather than advice?

**Model output** (pit_lap 0 = no further stop):

- Best median pit lap: **41** — recommended window (medians within 0.5s): **[41, 42, 43, 44, 45]**.
- Outcome spread at the best lap (p10-p90): 166.5s — this is the honest uncertainty of any single-race outcome.
- vs PIA: P(ahead) = 0.43 at lap 41; maximised at lap 0 (0.55).
- **Verdict:** Real choice (no further stop): median cost +0.65s vs the model optimum (lap 41); OUTSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_PIA |
|---|---|---|---|---|---|---|
| 41 | 2927.73 | 2950.39 | 2888.09 | 3054.56 | 0.32 | 0.43 |
| 42 | 2927.78 | 2950.40 | 2888.09 | 3054.33 | 0.00 | 0.43 |
| 43 | 2927.79 | 2950.40 | 2888.14 | 3054.23 | 0.01 | 0.43 |
| 44 | 2927.82 | 2950.46 | 2888.16 | 3054.41 | 0.01 | 0.43 |
| 45 | 2927.95 | 2950.54 | 2888.19 | 3054.55 | 0.01 | 0.43 |
| 0 <- real | 2928.37 | 2943.73 | 2861.53 | 3049.09 | 0.58 | 0.55 |

## Cross-case analysis (the audit's findings)

**1. Three metrics, three different answers — which is the whole argument
for reporting a distribution (Case A).** Verstappen's real lap-17 cover
costs +4.97s in median race time against the lap-25 optimum. On P(best) it
is not merely competitive but the outright winner: 0.416 against 0.025 for
the median-optimal lap. On P(ahead of Norris) it is neither: lap 17 gives
0.659 where lap 22 would have given 0.731.

So the three summaries rank the same decision first, middling and not-
quite-best. Pitting early loses a little expected time, wins outright in
the scenarios that decide races (a later safety car, a faster-than-expected
Norris undercut), and is not the sharpest available bet on the head-to-
head. Any single-number verdict on this call — including the flattering one
— is an artefact of which number was chosen.

**2. Folklore correction: Norris's extended stint did not lose him
Barcelona 2024 (Case B).** P(ahead of Verstappen) never reaches 0.5 at any
candidate stop lap: it runs 0.145 to 0.369, his real lap-23 choice sitting
at 0.337 against a best-available 0.369 at lap 28. No pit lap available to
him makes him the favourite, and his +1.72s against the optimum is small
beside that. The race was decided by pace and track position, not by the
stop timing the post-race narrative focused on.

**3. The bunching blind spot, quantified (Case C).** The model calls
Sainz's universally-praised lap-20 safety-car stop 5.91s worse than
stopping at lap 35 — and here the MODEL is wrong, for a reason documented
since Phase 4: it does not model the field bunching behind the safety car.
In reality the SC had already erased Sainz's 6.4s lead, so staying out
would have gifted every rival a discounted stop while his own cushion was
gone; the model still credits him that cushion. This disagreement is the
audit's most useful output: it turns a known qualitative limitation into a
measured ~6s bias for SC-window decisions at the front of a bunched field.

**4. The model endorses the boldest real gamble of the set (Case D).**
Russell's lap-44 VSC stop is within 1.11s of the model optimum and beats
staying out on median time (1913.3 against 1914.9). It also buys the head-
to-heads the stop was for: P(ahead of Sainz) 0.477 and P(ahead of Norris)
0.580, both above what the median-optimal lap returns (0.311 and 0.401).
Mercedes bought a near coin-flip for the win at roughly zero expected-time
cost. History records the crash; the decision was sound.

**5. The declared blind spot, stated as one (Case E).** At Monaco 2024 the
model puts the real no-stop within 0.65s of its own optimum and gives it
P(best) 0.581, the highest of any candidate. That agreement is not a
success. The model has no track-position term, and the reason nobody
stopped was that overtaking at Monaco is close to impossible — not that the
lap times happened to work out. A time-only model reaching the right answer
for the wrong reason is exactly the case that has to be read as a
limitation rather than a validation.
