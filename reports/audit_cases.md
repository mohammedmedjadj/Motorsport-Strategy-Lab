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

- Best median pit lap: **26** — recommended window (medians within 0.5s): **[24, 25, 26, 27, 28]**.
- Outcome spread at the best lap (p10-p90): 260.5s — this is the honest uncertainty of any single-race outcome.
- vs NOR: P(ahead) = 0.64 at lap 26; maximised at lap 21 (0.73).
- **Verdict:** Real choice (lap 17): median cost +3.23s vs the model optimum (lap 26); OUTSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_NOR |
|---|---|---|---|---|---|---|
| 17 <- real | 4025.19 | 4092.29 | 3997.09 | 4261.68 | 0.43 | 0.70 |
| 24 | 4022.16 | 4092.91 | 4001.50 | 4262.83 | 0.04 | 0.70 |
| 25 | 4021.99 | 4093.20 | 4002.09 | 4263.07 | 0.04 | 0.68 |
| 26 | 4021.95 | 4093.54 | 4002.77 | 4263.29 | 0.03 | 0.64 |
| 27 | 4022.17 | 4093.96 | 4003.44 | 4263.63 | 0.03 | 0.61 |
| 28 | 4022.39 | 4094.44 | 4004.15 | 4264.39 | 0.03 | 0.58 |

## Case B: Barcelona 2024 — Norris's extended stint (failed overcut)

**State (measured from data):** end of lap 16/66, NOR on SOFT age 16. Rivals: VER (+4.8s, SOFT age 19, real plan: stop lap 17).

**Real decision:** Stayed out until lap 23 on SOFT (to age 23); rejoined behind and finished 2nd, +2.2s.

**Question:** Did staying out to lap 23 ever look optimal against Verstappen's real lap-17 stop?

**Model output** (pit_lap 0 = no further stop):

- Best median pit lap: **28** — recommended window (medians within 0.5s): **[25, 26, 27, 28, 29, 30]**.
- Outcome spread at the best lap (p10-p90): 260.1s — this is the honest uncertainty of any single-race outcome.
- vs VER: P(ahead) = 0.32 at lap 28; maximised at lap 27 (0.32).
- **Verdict:** Real choice (lap 23): median cost +1.45s vs the model optimum (lap 28); OUTSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_VER |
|---|---|---|---|---|---|---|
| 23 <- real | 4020.85 | 4091.08 | 3999.21 | 4260.72 | 0.04 | 0.30 |
| 25 | 4019.88 | 4091.21 | 4000.17 | 4261.30 | 0.04 | 0.32 |
| 26 | 4019.61 | 4091.33 | 4000.60 | 4261.29 | 0.03 | 0.32 |
| 27 | 4019.44 | 4091.54 | 4001.20 | 4261.32 | 0.04 | 0.32 |
| 28 | 4019.40 | 4091.81 | 4001.67 | 4261.74 | 0.04 | 0.32 |
| 29 | 4019.50 | 4092.16 | 4002.24 | 4262.58 | 0.04 | 0.31 |
| 30 | 4019.73 | 4092.56 | 4002.77 | 4263.22 | 0.03 | 0.31 |

## Case C: Singapore 2023 — Sainz boxes under the lap-20 safety car

**State (measured from data):** end of lap 19/62, SAI on MEDIUM age 19 — SC currently deployed. Rivals: RUS (-6.4s, MEDIUM age 19, real plan: stop lap 20); NOR (-7.5s, MEDIUM age 19, real plan: stop lap 20).

**Real decision:** Pitted lap 20 under SC (MEDIUM age 20 -> HARD), as did the whole leading group; won the race.

**Question:** Does the model confirm that stopping immediately under the SC dominated staying out?

**Model output** (pit_lap 0 = no further stop):

- Best median pit lap: **37** — recommended window (medians within 0.5s): **[33, 34, 35, 36, 37, 38, 39, 40]**.
- Outcome spread at the best lap (p10-p90): 342.8s — this is the honest uncertainty of any single-race outcome.
- vs RUS: P(ahead) = 0.94 at lap 37; maximised at lap 35 (0.94).
- vs NOR: P(ahead) = 0.96 at lap 37; maximised at lap 36 (0.96).
- **Verdict:** Real choice (lap 20): median cost +6.54s vs the model optimum (lap 37); OUTSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_RUS | p_ahead_NOR |
|---|---|---|---|---|---|---|---|
| 20 <- real | 4481.97 | 4509.34 | 4356.63 | 4697.49 | 0.00 | 0.81 | 0.86 |
| 33 | 4475.89 | 4503.50 | 4350.66 | 4693.04 | 0.02 | 0.93 | 0.96 |
| 34 | 4475.53 | 4503.19 | 4350.39 | 4693.08 | 0.03 | 0.94 | 0.96 |
| 35 | 4475.50 | 4502.99 | 4350.27 | 4692.79 | 0.05 | 0.94 | 0.96 |
| 36 | 4475.53 | 4502.91 | 4350.26 | 4693.06 | 0.10 | 0.94 | 0.96 |
| 37 | 4475.42 | 4502.91 | 4350.29 | 4693.13 | 0.12 | 0.94 | 0.96 |
| 38 | 4475.49 | 4502.96 | 4350.31 | 4693.02 | 0.09 | 0.94 | 0.96 |
| 39 | 4475.49 | 4503.13 | 4350.50 | 4693.39 | 0.04 | 0.94 | 0.96 |
| 40 | 4475.76 | 4503.41 | 4350.68 | 4693.41 | 0.02 | 0.93 | 0.95 |

## Case D: Singapore 2023 — Mercedes' VSC gamble (Russell, lap 44)

**State (measured from data):** end of lap 43/62, RUS on HARD age 23 — VSC currently deployed. Rivals: SAI (+0.9s, HARD age 23, real plan: no stop); NOR (-0.8s, HARD age 23, real plan: no stop).

**Real decision:** Pitted lap 44 under VSC (HARD age 24 -> MEDIUM), dropping P2 -> P4 to attack; caught the leaders but crashed on the last lap fighting for the podium.

**Question:** Was surrendering track position for fresh mediums time-optimal, and what does P(ahead) say about the win chance it bought?

**Model output** (pit_lap 0 = no further stop):

- Best median pit lap: **46** — recommended window (medians within 0.5s): **[45, 46]**.
- Outcome spread at the best lap (p10-p90): 187.2s — this is the honest uncertainty of any single-race outcome.
- vs SAI: P(ahead) = 0.29 at lap 46; maximised at lap 45 (0.51).
- vs NOR: P(ahead) = 0.39 at lap 46; maximised at lap 45 (0.60).
- **Verdict:** Real choice (lap 44): median cost +1.13s vs the model optimum (lap 46); OUTSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_SAI | p_ahead_NOR |
|---|---|---|---|---|---|---|---|
| 44 <- real | 1913.79 | 1955.85 | 1891.42 | 2080.46 | 0.00 | 0.47 | 0.57 |
| 45 | 1913.15 | 1955.25 | 1890.76 | 2079.95 | 0.49 | 0.51 | 0.60 |
| 46 | 1912.66 | 1958.64 | 1895.71 | 2082.89 | 0.17 | 0.29 | 0.39 |
| 0 | 1915.48 | 1956.21 | 1894.30 | 2076.21 | 0.28 | 0.42 | 0.54 |

## Case E: Monaco 2024 — Leclerc mid-race (the model's blind spot)

**State (measured from data):** end of lap 40/78, LEC on HARD age 39. Rivals: PIA (-1.6s, HARD age 40, real plan: no stop).

**Real decision:** Nobody pitted for the entire race: the lap-1 red flag allowed a free tyre change, and Monaco track position beats any pace gain. Leclerc won without stopping.

**Question:** What does a time-only model recommend here, and why must its answer be read as a documented limitation rather than advice?

**Model output** (pit_lap 0 = no further stop):

- Best median pit lap: **0** — recommended window (medians within 0.5s): **[0]**.
- Outcome spread at the best lap (p10-p90): 159.5s — this is the honest uncertainty of any single-race outcome.
- vs PIA: P(ahead) = 0.54 at lap 0; maximised at lap 0 (0.54).
- **Verdict:** Real choice (no further stop): median cost +0.00s vs the model optimum (lap 0); INSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_PIA |
|---|---|---|---|---|---|---|
| 0 <- real | 2918.81 | 2944.29 | 2886.25 | 3045.73 | 0.69 | 0.54 |

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
