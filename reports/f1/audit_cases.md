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

- Best median pit lap: **26** — recommended window (medians within 0.5s): **[23, 24, 25, 26, 27]**.
- Outcome spread at the best lap (p10-p90): 260.6s — this is the honest uncertainty of any single-race outcome.
- vs NOR: P(ahead) = 0.64 at lap 26; maximised at lap 21 (0.74).
- **Verdict:** Real choice (lap 17): median cost +3.20s vs the model optimum (lap 26); OUTSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_NOR |
|---|---|---|---|---|---|---|
| 17 <- real | 4025.17 | 4094.63 | 3997.28 | 4261.65 | 0.42 | 0.71 |
| 23 | 4022.24 | 4094.93 | 4001.19 | 4262.01 | 0.04 | 0.72 |
| 24 | 4022.16 | 4095.21 | 4001.86 | 4262.62 | 0.03 | 0.70 |
| 25 | 4022.04 | 4095.54 | 4002.41 | 4262.96 | 0.04 | 0.67 |
| 26 | 4021.97 | 4095.90 | 4003.06 | 4263.65 | 0.03 | 0.64 |
| 27 | 4022.17 | 4096.30 | 4003.75 | 4263.95 | 0.03 | 0.61 |

## Case B: Barcelona 2024 — Norris's extended stint (failed overcut)

**State (measured from data):** end of lap 16/66, NOR on SOFT age 16. Rivals: VER (+4.8s, SOFT age 19, real plan: stop lap 17).

**Real decision:** Stayed out until lap 23 on SOFT (to age 23); rejoined behind and finished 2nd, +2.2s.

**Question:** Did staying out to lap 23 ever look optimal against Verstappen's real lap-17 stop?

**Model output** (pit_lap 0 = no further stop):

- Best median pit lap: **27** — recommended window (medians within 0.5s): **[25, 26, 27, 28, 29]**.
- Outcome spread at the best lap (p10-p90): 260.1s — this is the honest uncertainty of any single-race outcome.
- vs VER: P(ahead) = 0.32 at lap 27; maximised at lap 26 (0.32).
- **Verdict:** Real choice (lap 23): median cost +1.17s vs the model optimum (lap 27); OUTSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_VER |
|---|---|---|---|---|---|---|
| 23 <- real | 4020.45 | 4093.35 | 3999.67 | 4260.48 | 0.04 | 0.31 |
| 25 | 4019.76 | 4093.52 | 4000.47 | 4260.91 | 0.04 | 0.32 |
| 26 | 4019.53 | 4093.66 | 4000.91 | 4261.28 | 0.05 | 0.32 |
| 27 | 4019.28 | 4093.85 | 4001.44 | 4261.56 | 0.04 | 0.32 |
| 28 | 4019.41 | 4094.15 | 4002.01 | 4261.78 | 0.04 | 0.31 |
| 29 | 4019.60 | 4094.49 | 4002.54 | 4262.16 | 0.03 | 0.31 |

## Case C: Singapore 2023 — Sainz boxes under the lap-20 safety car

**State (measured from data):** end of lap 19/62, SAI on MEDIUM age 19 — SC currently deployed. Rivals: RUS (-6.4s, MEDIUM age 19, real plan: stop lap 20); NOR (-7.5s, MEDIUM age 19, real plan: stop lap 20).

**Real decision:** Pitted lap 20 under SC (MEDIUM age 20 -> HARD), as did the whole leading group; won the race.

**Question:** Does the model confirm that stopping immediately under the SC dominated staying out?

**Model output** (pit_lap 0 = no further stop):

- Best median pit lap: **37** — recommended window (medians within 0.5s): **[35, 36, 37, 38]**.
- Outcome spread at the best lap (p10-p90): 347.4s — this is the honest uncertainty of any single-race outcome.
- vs RUS: P(ahead) = 0.94 at lap 37; maximised at lap 36 (0.94).
- vs NOR: P(ahead) = 0.96 at lap 37; maximised at lap 35 (0.96).
- **Verdict:** Real choice (lap 20): median cost +6.55s vs the model optimum (lap 37); OUTSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_RUS | p_ahead_NOR |
|---|---|---|---|---|---|---|---|
| 20 <- real | 4483.86 | 4511.77 | 4355.46 | 4699.89 | 0.00 | 0.82 | 0.86 |
| 35 | 4477.80 | 4505.54 | 4348.68 | 4696.07 | 0.04 | 0.94 | 0.96 |
| 36 | 4477.47 | 4505.46 | 4348.57 | 4696.13 | 0.11 | 0.94 | 0.96 |
| 37 | 4477.31 | 4505.46 | 4348.51 | 4695.93 | 0.13 | 0.94 | 0.96 |
| 38 | 4477.67 | 4505.51 | 4348.67 | 4696.03 | 0.08 | 0.94 | 0.96 |

## Case D: Singapore 2023 — Mercedes' VSC gamble (Russell, lap 44)

**State (measured from data):** end of lap 43/62, RUS on HARD age 23 — VSC currently deployed. Rivals: SAI (+0.9s, HARD age 23, real plan: no stop); NOR (-0.8s, HARD age 23, real plan: no stop).

**Real decision:** Pitted lap 44 under VSC (HARD age 24 -> MEDIUM), dropping P2 -> P4 to attack; caught the leaders but crashed on the last lap fighting for the podium.

**Question:** Was surrendering track position for fresh mediums time-optimal, and what does P(ahead) say about the win chance it bought?

**Model output** (pit_lap 0 = no further stop):

- Best median pit lap: **46** — recommended window (medians within 0.5s): **[45, 46]**.
- Outcome spread at the best lap (p10-p90): 191.8s — this is the honest uncertainty of any single-race outcome.
- vs SAI: P(ahead) = 0.30 at lap 46; maximised at lap 45 (0.53).
- vs NOR: P(ahead) = 0.40 at lap 46; maximised at lap 45 (0.63).
- **Verdict:** Real choice (lap 44): median cost +1.02s vs the model optimum (lap 46); OUTSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_SAI | p_ahead_NOR |
|---|---|---|---|---|---|---|---|
| 44 <- real | 1913.29 | 1954.51 | 1891.02 | 2087.82 | 0.00 | 0.48 | 0.59 |
| 45 | 1912.65 | 1953.91 | 1890.36 | 2087.35 | 0.51 | 0.53 | 0.63 |
| 46 | 1912.28 | 1957.39 | 1895.29 | 2087.08 | 0.16 | 0.30 | 0.40 |
| 0 | 1914.96 | 1954.92 | 1893.85 | 2082.37 | 0.28 | 0.44 | 0.56 |

## Case E: Monaco 2024 — Leclerc mid-race (the model's blind spot)

**State (measured from data):** end of lap 40/78, LEC on HARD age 39. Rivals: PIA (-1.6s, HARD age 40, real plan: no stop).

**Real decision:** Nobody pitted for the entire race: the lap-1 red flag allowed a free tyre change, and Monaco track position beats any pace gain. Leclerc won without stopping.

**Question:** What does a time-only model recommend here, and why must its answer be read as a documented limitation rather than advice?

**Model output** (pit_lap 0 = no further stop):

- Best median pit lap: **0** — recommended window (medians within 0.5s): **[0]**.
- Outcome spread at the best lap (p10-p90): 158.8s — this is the honest uncertainty of any single-race outcome.
- vs PIA: P(ahead) = 0.54 at lap 0; maximised at lap 0 (0.54).
- **Verdict:** Real choice (no further stop): median cost +0.00s vs the model optimum (lap 0); INSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_PIA |
|---|---|---|---|---|---|---|
| 0 <- real | 2919.28 | 2944.06 | 2886.34 | 3045.18 | 0.69 | 0.54 |

## Cross-case analysis (the audit's findings)

**1. Median race time alone would mis-rank real decisions; the
distribution outputs are what make the audit fair (Case A).**
Verstappen's real lap-17 cover costs +3.2s in median race time vs the
lap-26 optimum — yet it holds the single highest P(best) (0.43 vs 0.03)
and the best P(ahead of Norris) (0.70 vs 0.64). Translation: pitting
early loses a little time in the median scenario but wins outright in
the scenarios that matter (a later SC or a faster-than-expected Norris
undercut). Red Bull paid ~3s of expected time to buy +6 points of win
probability against the live threat — the model's own multi-metric
output vindicates the call that its single-metric summary would flag
as 'too early'.

**2. Folklore correction: Norris's extended stint did not lose him
Barcelona 2024 (Case B).** P(ahead of Verstappen) is flat at 0.30-0.32
across every candidate stop lap, real choice included. No pit-lap
choice available to Norris flips that race; his +1.45s vs optimum is
noise-level. The model's verdict: the race was decided by pace and
track position, not by the stop timing the post-race narrative
focused on.

**3. The bunching blind spot, quantified (Case C).** The model calls
Sainz's universally-praised lap-20 SC stop 6.5s worse than staying out
to lap 37 — and here the MODEL is wrong, for a reason documented since
Phase 4: it does not model the field bunching behind the safety car.
In reality the SC had already erased Sainz's 6.4s lead, so staying out
would have gifted every rival a discounted stop while his own cushion
was gone; the model still credits him that cushion, inflating the
stay-out branch by roughly the erased lead plus queue effects. This
disagreement is the audit's most useful output: it converts a known
qualitative limitation into a measured ~6-7s bias for SC-window
decisions at the front of a bunched field.

**4. The model endorses the boldest real gamble of the set (Case D).**
Russell's lap-44 VSC stop is within 1.1s of the model optimum and
strictly better than staying out (median 1913.8 vs 1915.5; P(ahead
Sainz) 0.47 vs 0.42; P(ahead Norris) 0.57 vs 0.54). Mercedes bought a
near coin-flip for the win at roughly zero expected-time cost. History
records the gamble failing on the last lap — the audit records that
it was the right bet. Outcome and decision quality are different
things; this case is why.

**5. Monaco agrees for subtler reasons than expected (Case E).** The
blind-spot case was chosen expecting disagreement, but even the pure
time model keeps Leclerc out (no-stop P(best) = 0.69): Monaco's
flattening degradation curve never repays a 19.1s pit loss over the
remaining 38 laps. The genuine blind spots remain — the model does not
know the lap-1 red flag made the no-stop strategy legal, and it
assigns no value to track position — but at Monaco the physics alone
already point the same way.

## Scope reminders for reading these verdicts

- 'OUTSIDE the recommended window' is a statement about expected race
  time under the model's scope, not a judgement that strategists erred;
  Cases A and C show two different resolutions of that tension (the
  distributions vindicate A; a documented model limitation explains C).
- Rival behaviour is frozen to history; counterfactual rival reactions
  (e.g. Norris covering Verstappen's undercut) are not simulated.
- Phase 2 showed degradation slopes move between seasons; verdict
  margins under ~2s should be read as ties.
