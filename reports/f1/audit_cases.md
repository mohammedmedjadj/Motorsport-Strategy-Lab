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

- Best median pit lap: **32** — recommended window (medians within 0.5s): **[30, 31, 32, 33, 34]**.
- Outcome spread at the best lap (p10-p90): 250.6s — this is the honest uncertainty of any single-race outcome.
- vs NOR: P(ahead) = 0.88 at lap 32; maximised at lap 30 (0.89).
- **Verdict:** Real choice (lap 17): median cost +19.27s vs the model optimum (lap 32); OUTSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_NOR |
|---|---|---|---|---|---|---|
| 17 <- real | 4078.62 | 4147.99 | 4061.25 | 4311.85 | 0.00 | 0.12 |
| 30 | 4059.53 | 4131.52 | 4045.90 | 4297.03 | 0.12 | 0.89 |
| 31 | 4059.36 | 4131.36 | 4045.69 | 4296.84 | 0.15 | 0.89 |
| 32 | 4059.35 | 4131.36 | 4045.73 | 4296.38 | 0.15 | 0.88 |
| 33 | 4059.51 | 4131.50 | 4045.94 | 4297.12 | 0.12 | 0.87 |
| 34 | 4059.83 | 4131.83 | 4046.20 | 4296.86 | 0.07 | 0.85 |

## Case B: Barcelona 2024 — Norris's extended stint (failed overcut)

**State (measured from data):** end of lap 16/66, NOR on SOFT age 16. Rivals: VER (+4.8s, SOFT age 19, real plan: stop lap 17).

**Real decision:** Stayed out until lap 23 on SOFT (to age 23); rejoined behind and finished 2nd, +2.2s.

**Question:** Did staying out to lap 23 ever look optimal against Verstappen's real lap-17 stop?

**Model output** (pit_lap 0 = no further stop):

- Best median pit lap: **33** — recommended window (medians within 0.5s): **[31, 32, 33, 34, 35]**.
- Outcome spread at the best lap (p10-p90): 251.2s — this is the honest uncertainty of any single-race outcome.
- vs VER: P(ahead) = 0.96 at lap 33; maximised at lap 31 (0.97).
- **Verdict:** Real choice (lap 23): median cost +9.10s vs the model optimum (lap 33); OUTSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_VER |
|---|---|---|---|---|---|---|
| 23 <- real | 4064.28 | 4135.39 | 4049.32 | 4300.09 | 0.00 | 0.88 |
| 31 | 4055.54 | 4127.85 | 4042.16 | 4293.53 | 0.11 | 0.97 |
| 32 | 4055.29 | 4127.61 | 4041.88 | 4293.08 | 0.15 | 0.97 |
| 33 | 4055.18 | 4127.52 | 4041.81 | 4293.02 | 0.16 | 0.96 |
| 34 | 4055.29 | 4127.62 | 4041.94 | 4292.97 | 0.14 | 0.96 |
| 35 | 4055.52 | 4127.85 | 4042.19 | 4292.96 | 0.09 | 0.95 |

## Case C: Singapore 2023 — Sainz boxes under the lap-20 safety car

**State (measured from data):** end of lap 19/62, SAI on MEDIUM age 19 — SC currently deployed. Rivals: RUS (-6.4s, MEDIUM age 19, real plan: stop lap 20); NOR (-7.5s, MEDIUM age 19, real plan: stop lap 20).

**Real decision:** Pitted lap 20 under SC (MEDIUM age 20 -> HARD), as did the whole leading group; won the race.

**Question:** Does the model confirm that stopping immediately under the SC dominated staying out?

**Model output** (pit_lap 0 = no further stop):

- Best median pit lap: **39** — recommended window (medians within 0.5s): **[39, 40, 41, 42, 43, 44]**.
- Outcome spread at the best lap (p10-p90): 381.9s — this is the honest uncertainty of any single-race outcome.
- vs RUS: P(ahead) = 0.91 at lap 39; maximised at lap 38 (0.92).
- vs NOR: P(ahead) = 0.93 at lap 39; maximised at lap 39 (0.93).
- **Verdict:** Real choice (lap 20): median cost +10.65s vs the model optimum (lap 39); OUTSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_RUS | p_ahead_NOR |
|---|---|---|---|---|---|---|---|
| 20 <- real | 4521.11 | 4539.32 | 4367.15 | 4747.46 | 0.00 | 0.73 | 0.76 |
| 39 | 4510.46 | 4529.19 | 4355.70 | 4737.59 | 0.06 | 0.91 | 0.93 |
| 40 | 4510.85 | 4529.08 | 4355.59 | 4737.38 | 0.06 | 0.91 | 0.93 |
| 41 | 4510.75 | 4528.96 | 4355.59 | 4737.71 | 0.06 | 0.91 | 0.93 |
| 42 | 4510.61 | 4528.99 | 4355.72 | 4736.96 | 0.07 | 0.91 | 0.93 |
| 43 | 4510.92 | 4529.08 | 4356.16 | 4737.16 | 0.06 | 0.91 | 0.93 |
| 44 | 4510.82 | 4529.28 | 4356.48 | 4737.10 | 0.05 | 0.90 | 0.92 |

## Case D: Singapore 2023 — Mercedes' VSC gamble (Russell, lap 44)

**State (measured from data):** end of lap 43/62, RUS on HARD age 23 — VSC currently deployed. Rivals: SAI (+0.9s, HARD age 23, real plan: no stop); NOR (-0.8s, HARD age 23, real plan: no stop).

**Real decision:** Pitted lap 44 under VSC (HARD age 24 -> MEDIUM), dropping P2 -> P4 to attack; caught the leaders but crashed on the last lap fighting for the podium.

**Question:** Was surrendering track position for fresh mediums time-optimal, and what does P(ahead) say about the win chance it bought?

**Model output** (pit_lap 0 = no further stop):

- Best median pit lap: **46** — recommended window (medians within 0.5s): **[45, 46]**.
- Outcome spread at the best lap (p10-p90): 216.8s — this is the honest uncertainty of any single-race outcome.
- vs SAI: P(ahead) = 0.39 at lap 46; maximised at lap 45 (0.67).
- vs NOR: P(ahead) = 0.46 at lap 46; maximised at lap 45 (0.73).
- **Verdict:** Real choice (lap 44): median cost +0.72s vs the model optimum (lap 46); OUTSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_SAI | p_ahead_NOR |
|---|---|---|---|---|---|---|---|
| 44 <- real | 1962.00 | 1999.12 | 1920.91 | 2143.23 | 0.00 | 0.65 | 0.71 |
| 45 | 1961.50 | 1998.70 | 1920.43 | 2142.86 | 0.62 | 0.67 | 0.73 |
| 46 | 1961.28 | 2004.59 | 1928.59 | 2145.37 | 0.19 | 0.39 | 0.46 |
| 0 | 1967.20 | 2003.14 | 1927.31 | 2142.10 | 0.15 | 0.45 | 0.54 |

## Case E: Monaco 2024 — Leclerc mid-race (the model's blind spot)

**State (measured from data):** end of lap 40/78, LEC on HARD age 39. Rivals: PIA (-1.6s, HARD age 40, real plan: no stop).

**Real decision:** Nobody pitted for the entire race: the lap-1 red flag allowed a free tyre change, and Monaco track position beats any pace gain. Leclerc won without stopping.

**Question:** What does a time-only model recommend here, and why must its answer be read as a documented limitation rather than advice?

**Model output** (pit_lap 0 = no further stop):

- Best median pit lap: **41** — recommended window (medians within 0.5s): **[41, 42, 43, 44, 45]**.
- Outcome spread at the best lap (p10-p90): 191.4s — this is the honest uncertainty of any single-race outcome.
- vs PIA: P(ahead) = 0.55 at lap 41; maximised at lap 0 (0.56).
- **Verdict:** Real choice (no further stop): median cost +4.58s vs the model optimum (lap 41); OUTSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_PIA |
|---|---|---|---|---|---|---|
| 41 | 2906.45 | 2935.57 | 2867.92 | 3059.36 | 0.40 | 0.55 |
| 42 | 2906.58 | 2935.59 | 2867.95 | 3059.30 | 0.00 | 0.55 |
| 43 | 2906.64 | 2935.62 | 2868.03 | 3059.31 | 0.01 | 0.55 |
| 44 | 2906.66 | 2935.70 | 2868.12 | 3059.34 | 0.01 | 0.55 |
| 45 | 2906.87 | 2935.84 | 2868.18 | 3059.19 | 0.01 | 0.54 |
| 0 <- real | 2911.03 | 2936.09 | 2862.67 | 3060.32 | 0.45 | 0.56 |

## Cross-case analysis (the audit's findings)

**1. Three metrics, three different answers — which is the whole argument
for reporting a distribution (Case A).** Verstappen's real lap-17 cover
costs +19.27s in median race time against the lap-32 optimum. On P(best) it
is beaten by lap 32 (0.150): 0.000 against 0.150 for the median-optimal
lap. On P(ahead of Norris) it is neither: lap 17 gives 0.124 where lap 30
would have given 0.892.

So the three summaries rank the same decision first, middling and not-
quite-best. Pitting early loses a little expected time, wins outright in
the scenarios that decide races (a later safety car, a faster-than-expected
Norris undercut), and is not the sharpest available bet on the head-to-
head. Any single-number verdict on this call — including the flattering one
— is an artefact of which number was chosen.

**2. Folklore correction: Norris's extended stint did not lose him
Barcelona 2024 (Case B).** P(ahead of Verstappen) now reaches 0.5 at some
candidate stop lap, which it did not when this finding was first written:
it runs 0.000 to 0.971, his real lap-23 choice sitting at 0.879 against a
best-available 0.971 at lap 31. No pit lap available to him makes him the
favourite, and his +9.10s against the optimum is small beside that. The
race was decided by pace and track position, not by the stop timing the
post-race narrative focused on.

**3. The bunching blind spot, quantified (Case C).** The model calls
Sainz's universally-praised lap-20 safety-car stop 10.65s worse than
stopping at lap 39 — and here the MODEL is wrong, for a reason documented
since Phase 4: it does not model the field bunching behind the safety car.
In reality the SC had already erased Sainz's 6.4s lead, so staying out
would have gifted every rival a discounted stop while his own cushion was
gone; the model still credits him that cushion. This disagreement is the
audit's most useful output: it turns a known qualitative limitation into a
measured ~11s bias for SC-window decisions at the front of a bunched field.

**4. The model endorses the boldest real gamble of the set (Case D).**
Russell's lap-44 VSC stop is within 0.72s of the model optimum and beats
staying out on median time (1962.0 against 1967.2). It also buys the head-
to-heads the stop was for: P(ahead of Sainz) 0.652 and P(ahead of Norris)
0.710, both above what the median-optimal lap returns (0.390 and 0.461).
Mercedes bought a near coin-flip for the win at roughly zero expected-time
cost. History records the crash; the decision was sound.

**5. The declared blind spot, stated as one (Case E).** At Monaco 2024 the
model puts the real no-stop within 4.58s of its own optimum and gives it
P(best) 0.449, the highest of any candidate. That agreement is not a
success. The model has no track-position term, and the reason nobody
stopped was that overtaking at Monaco is close to impossible — not that the
lap times happened to work out. A time-only model reaching the right answer
for the wrong reason is exactly the case that has to be read as a
limitation rather than a validation.
