# When tyres beat fuel: a rule that holds across four series

A cross-series result, and the only document in this project that is allowed to
be one. Everything else is written per series and per class precisely because
pooling them destroys findings — this is the exception because the finding *is*
the thing they have in common, and it was invisible until enough of them were
measured on identical code.

## The question

Endurance strategy has a fixed floor: the fuel tank forces a minimum number of
stops. The interesting question is whether tyre degradation is ever steep
enough to make an *extra* stop worth its cost. Phase 4 of this project answered
"never", on 21 circuits of prototype racing. That answer was wrong in the way
most wrong answers are — it was true of the data it had.

Scope now: **205 race-seasons**, four series, six classes.

| series | classes |
|---|---|
| WEC | HYPERCAR |
| IMSA | GTP, GTD, GTD PRO |
| ELMS | LMP2, LMP2 Pro/Am |

**25 of the 205 are tyre-limited** — the exact optimum, by dynamic program,
takes more stops than the fuel minimum.

> **This document was previously computed on 66 entries**, one representative
> season per circuit-class, and its own "Limits" section said so: *"Repeating
> this per season would give a better-powered version of the same test."* That
> is what the numbers below are. Every element of the rule got stronger, the
> 22.5 s edge landed in exactly the same place against three times as much
> data, and the class-level correlation went from −0.913 to **−0.982**. The
> reason the old scope was wrong is worth keeping: the plan depends on each
> race's *fitted degradation slope*, and this project's most-cited result is
> that slopes do not transfer between seasons — so "one representative season"
> was refuted by a finding printed two reports over.

## The rule: two conditions, both necessary, neither sufficient

### 1. The stop has to be cheap

| | pit loss, median | range |
|---|---|---|
| tyre-limited (25) | **7.5 s** | 4.7 – 22.5 |
| fuel-limited (180) | **57.1 s** | 5.4 – 98.2 |

Mann-Whitney **p = 1.1 × 10⁻¹⁴**, and the separation has a hard edge: **no race
with a pit loss above 22.5 s is tyre-limited anywhere in the data.** That edge
sat at 22.5 s on 66 entries and sits at 22.5 s on 205 — it did not move when the
sample tripled, which is the most encouraging thing about it.

A WEC Hypercar stop costs 60–90 s, which buys roughly 2,000 laps of degradation
at a typical +0.03 s/lap slope. No tyre wears fast enough to repay that.

*One fuel-limited entry reads 358 s (IMSA Road America 2022, GTD PRO) and is
excluded from the range above as a near-certain artefact: a six-minute service
is not a pit stop, it is a stoppage the pit-loss estimator has absorbed. It
changes nothing here — it is far above the threshold either way — but quoting
it as a measurement would be wrong.*

Necessary, not sufficient: **55 of the 205 entries clear the cheap-stop bar and
only 25 of those are tyre-limited.**

### 2. There has to be degradation to escape

Among those 55 cheap-stop entries:

| | net slope, median | range |
|---|---|---|
| tyre-limited (25) | **+0.0376 s/lap** | +0.0174 – +0.0804 |
| fuel-limited (30) | **+0.0112 s/lap** | −0.1645 – +0.0504 |

Mann-Whitney **p = 1.5 × 10⁻⁸**. Where the stop is cheap, what decides it is
whether the tyre is actually going away.

Note the fuel-limited group's lower bound: −0.16 s/lap is not a measurement but
the [unmodelled track-evolution
term](track_evolution_omitted_variable.md) showing through. Those races are
correctly classified as fuel-limited — a negative fitted slope cannot justify an
extra stop under any reading — but the number itself is a known defect.

## Sorting by pit loss sorts the strategy regime

| class | median pit loss | share tyre-limited |
|---|---|---|
| IMSA GTD | 24.4 s | **25.9%** |
| IMSA GTD PRO | 39.6 s | 15.2% |
| IMSA GTP | 57.0 s | 6.2% |
| ELMS LMP2 | 61.7 s | 4.0% |
| ELMS LMP2 Pro/Am | 63.8 s | 0.0% |
| WEC Hypercar | 74.0 s | 0.0% |

Correlation **−0.982**, and the ordering is now **perfectly monotonic**: there
is not a single inversion between the two columns. On the 66-entry sample the
correlation was −0.913 with one inversion, which was already the finding; this
is the same finding measured properly.

## The class was a proxy; the mechanism is the stop

An earlier version of this said "GT3 is tyre-limited where prototypes are not".
That reads as a fact about cars, and it is not one. Restricted to the cheap-stop
entries, the split happens *inside* every class:

| class | cheap-stop entries | of those, tyre-limited |
|---|---|---|
| IMSA GTD | 26 | 15 |
| IMSA GTD PRO | 13 | 7 |
| IMSA GTP | 6 | 2 |
| ELMS LMP2 | 4 | 1 |
| WEC HYPERCAR | 3 | 0 |
| ELMS LMP2 Pro/Am | 3 | 0 |

GT3 dominates the tyre-limited list only because GT3 races are where cheap stops
are common — a GT3 service is quicker in absolute terms and GT3 championships
run more short sprint rounds. Condition on the stop cost and the class stops
mattering. That is the difference between a correlation worth reporting and a
mechanism worth believing.

## Why this needed four series

With WEC alone the answer was "never" — every Hypercar stop is expensive, so
condition 1 never clears and the question never arises. With IMSA GTP added it
was "never, except Laguna Seca", which reads as a curiosity. Only once GT3 and
ELMS supplied enough entries on *both* sides of the pit-loss threshold did the
threshold itself become visible.

That is an argument for breadth over depth in this kind of work, and it is worth
stating because the instinct runs the other way: more seasons of the same class
would never have found this. The variable that mattered had almost no variance
until a fourth series was added.

**And then depth mattered after all.** Widening from one season per circuit-class
to every season did not change the rule, but it took the pit-loss test from
p = 10⁻⁵ to p = 10⁻¹⁴ and made the class ordering monotonic. Breadth found the
variable; depth is what made the evidence match the confidence the conclusion
was already being stated with.

## Limits, stated

- **25 positives.** The pit-loss edge at 22.5 s is where the data happens to
  stop, not a measured boundary. The honest claim is that no counterexample
  exists in 205 entries, not that 23 s is safe. It is a stronger claim than the
  one this document made at 66 entries, and it is the same kind of claim.
- **Time-only objective.** These optima ignore track position and multi-class
  traffic. An extra stop that is faster on paper can still lose a real race,
  which is exactly the limitation the F1 audit documents for Monaco.
- **Five race-seasons are not planned at all**, because a race with neither a
  Full Course Yellow nor a Safety Car has no neutralised laps to measure a pace
  ratio from. They are listed with their reasons in
  `data/derived/endurance/multistop_skipped.csv`, and
  [`tests/test_coverage.py`](../../tests/test_coverage.py) fails if any race
  goes missing without one.
- **The slopes underneath carry a known defect.** Races with strong track
  evolution fit slopes biased downward, so a handful of the fuel-limited
  classifications rest on a slope that is a lower bound. Correcting it could
  only move races *toward* tyre-limited, which would strengthen this rule rather
  than weaken it.
