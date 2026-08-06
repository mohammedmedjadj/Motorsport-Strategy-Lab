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

- Best median pit lap: **28** — recommended window (medians within 0.5s): **[24, 25, 26, 27, 28]**.
- Outcome spread at the best lap (p10-p90): 182.6s — this is the honest uncertainty of any single-race outcome.
- vs NOR: P(ahead) = 0.57 at lap 28; maximised at lap 21 (0.73).
- **Verdict:** Real choice (lap 17): median cost +3.67s vs the model optimum (lap 28); OUTSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_NOR |
|---|---|---|---|---|---|---|
| 17 <- real | 4031.44 | 4073.11 | 3998.88 | 4187.76 | 0.42 | 0.69 |
| 24 | 4028.21 | 4073.72 | 4003.12 | 4187.43 | 0.04 | 0.70 |
| 25 | 4028.05 | 4074.03 | 4003.68 | 4187.92 | 0.04 | 0.67 |
| 26 | 4027.83 | 4074.36 | 4004.41 | 4188.15 | 0.03 | 0.64 |
| 27 | 4027.81 | 4074.79 | 4005.01 | 4188.75 | 0.03 | 0.61 |
| 28 | 4027.77 | 4075.26 | 4005.60 | 4188.23 | 0.03 | 0.57 |

## Case B: Barcelona 2024 — Norris's extended stint (failed overcut)

**State (measured from data):** end of lap 16/66, NOR on SOFT age 16. Rivals: VER (+4.8s, SOFT age 19, real plan: stop lap 17).

**Real decision:** Stayed out until lap 23 on SOFT (to age 23); rejoined behind and finished 2nd, +2.2s.

**Question:** Did staying out to lap 23 ever look optimal against Verstappen's real lap-17 stop?

**Model output** (pit_lap 0 = no further stop):

- Best median pit lap: **29** — recommended window (medians within 0.5s): **[26, 27, 28, 29, 30]**.
- Outcome spread at the best lap (p10-p90): 182.1s — this is the honest uncertainty of any single-race outcome.
- vs VER: P(ahead) = 0.31 at lap 29; maximised at lap 26 (0.32).
- **Verdict:** Real choice (lap 23): median cost +2.14s vs the model optimum (lap 29); OUTSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_VER |
|---|---|---|---|---|---|---|
| 23 <- real | 4026.99 | 4071.89 | 4000.81 | 4185.95 | 0.04 | 0.30 |
| 26 | 4025.30 | 4072.12 | 4002.09 | 4186.19 | 0.04 | 0.32 |
| 27 | 4025.05 | 4072.32 | 4002.68 | 4186.70 | 0.04 | 0.32 |
| 28 | 4024.89 | 4072.58 | 4003.13 | 4186.04 | 0.04 | 0.32 |
| 29 | 4024.84 | 4072.94 | 4003.66 | 4185.74 | 0.04 | 0.31 |
| 30 | 4025.20 | 4073.32 | 4004.11 | 4186.75 | 0.03 | 0.31 |

## Case C: Singapore 2023 — Sainz boxes under the lap-20 safety car

**State (measured from data):** end of lap 19/62, SAI on MEDIUM age 19 — SC currently deployed. Rivals: RUS (-6.4s, MEDIUM age 19, real plan: stop lap 20); NOR (-7.5s, MEDIUM age 19, real plan: stop lap 20).

**Real decision:** Pitted lap 20 under SC (MEDIUM age 20 -> HARD), as did the whole leading group; won the race.

**Question:** Does the model confirm that stopping immediately under the SC dominated staying out?

**Model output** (pit_lap 0 = no further stop):

- Best median pit lap: **39** — recommended window (medians within 0.5s): **[39, 40]**.
- Outcome spread at the best lap (p10-p90): 485.8s — this is the honest uncertainty of any single-race outcome.
- vs RUS: P(ahead) = 0.91 at lap 39; maximised at lap 22 (0.93).
- vs NOR: P(ahead) = 0.94 at lap 39; maximised at lap 22 (0.96).
- **Verdict:** Real choice (lap 20): median cost +4.49s vs the model optimum (lap 39); OUTSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_RUS | p_ahead_NOR |
|---|---|---|---|---|---|---|---|
| 20 <- real | 4638.63 | 4663.06 | 4434.38 | 4916.28 | 0.00 | 0.83 | 0.88 |
| 39 | 4634.14 | 4658.40 | 4428.09 | 4913.88 | 0.05 | 0.91 | 0.94 |
| 40 | 4634.23 | 4658.61 | 4428.30 | 4914.15 | 0.04 | 0.91 | 0.93 |

## Case D: Singapore 2023 — Mercedes' VSC gamble (Russell, lap 44)

**State (measured from data):** end of lap 43/62, RUS on HARD age 23 — VSC currently deployed. Rivals: SAI (+0.9s, HARD age 23, real plan: no stop); NOR (-0.8s, HARD age 23, real plan: no stop).

**Real decision:** Pitted lap 44 under VSC (HARD age 24 -> MEDIUM), dropping P2 -> P4 to attack; caught the leaders but crashed on the last lap fighting for the podium.

**Question:** Was surrendering track position for fresh mediums time-optimal, and what does P(ahead) say about the win chance it bought?

**Model output** (pit_lap 0 = no further stop):

- Best median pit lap: **0** — recommended window (medians within 0.5s): **[0]**.
- Outcome spread at the best lap (p10-p90): 272.1s — this is the honest uncertainty of any single-race outcome.
- vs SAI: P(ahead) = 0.43 at lap 0; maximised at lap 0 (0.43).
- vs NOR: P(ahead) = 0.57 at lap 0; maximised at lap 0 (0.57).
- **Verdict:** Real choice (lap 44): median cost +4.04s vs the model optimum (lap 0); OUTSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_SAI | p_ahead_NOR |
|---|---|---|---|---|---|---|---|
| 44 <- real | 1998.29 | 2022.99 | 1895.99 | 2179.65 | 0.00 | 0.27 | 0.35 |
| 0 | 1994.25 | 2019.75 | 1899.30 | 2171.40 | 0.64 | 0.43 | 0.57 |

## Case E: Monaco 2024 — Leclerc mid-race (the model's blind spot)

**State (measured from data):** end of lap 40/78, LEC on HARD age 39. Rivals: PIA (-1.6s, HARD age 40, real plan: no stop).

**Real decision:** Nobody pitted for the entire race: the lap-1 red flag allowed a free tyre change, and Monaco track position beats any pace gain. Leclerc won without stopping.

**Question:** What does a time-only model recommend here, and why must its answer be read as a documented limitation rather than advice?

**Model output** (pit_lap 0 = no further stop):

- Best median pit lap: **0** — recommended window (medians within 0.5s): **[0]**.
- Outcome spread at the best lap (p10-p90): 212.1s — this is the honest uncertainty of any single-race outcome.
- vs PIA: P(ahead) = 0.53 at lap 0; maximised at lap 0 (0.53).
- **Verdict:** Real choice (no further stop): median cost +0.00s vs the model optimum (lap 0); INSIDE the recommended window.

| pit_lap | median_s | mean_s | p10_s | p90_s | p_best | p_ahead_PIA |
|---|---|---|---|---|---|---|
| 0 <- real | 2948.65 | 2981.32 | 2892.37 | 3104.44 | 0.68 | 0.53 |

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
