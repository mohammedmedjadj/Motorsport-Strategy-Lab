# When tyres beat fuel: a rule that holds across four series

A cross-series result, and the only document in this project that is allowed
to be one. Everything else is written per series and per class precisely
because pooling them destroys findings — this is the exception because the
finding *is* the thing they have in common, and it was invisible until enough
of them were measured on identical code.

## The question

Endurance strategy has a fixed floor: the fuel tank forces a minimum number of
stops. The interesting question is whether tyre degradation is ever steep
enough to make an *extra* stop worth its cost. Phase 4 of this project
answered "never", on 21 circuits of prototype racing. That answer was wrong in
the way most wrong answers are — it was true of the data it had.

Scope now: **66 circuit-class entries**, four series, six classes.

| series | classes |
|---|---|
| WEC | HYPERCAR |
| IMSA | GTP, GTD, GTD PRO |
| ELMS | LMP2, LMP2 Pro/Am |

Nine of the 66 are tyre-limited — the exact optimum, by dynamic program, takes
more stops than the fuel minimum.

## The rule: two conditions, both necessary, neither sufficient

### 1. The stop has to be cheap

| | pit loss, median | range |
|---|---|---|
| tyre-limited (9) | **7.7 s** | 4.9 – 22.5 |
| fuel-limited (57) | **56.0 s** | 8.0 – 91.1 |

Mann-Whitney **p = 0.00001**, and the separation has a hard edge: **no race
with a pit loss above 22.5 s is tyre-limited anywhere in the data.** A WEC
Hypercar stop costs 60–91 s, which buys roughly 2,000 laps of degradation at a
typical +0.03 s/lap slope — no tyre wears fast enough to repay that.

Necessary, not sufficient: 19 of the 66 entries clear the cheap-stop bar and
only 9 of those are tyre-limited.

### 2. There has to be degradation to escape

Among those 19 cheap-stop entries:

| | net slope, median | range |
|---|---|---|
| tyre-limited (9) | **+0.0331 s/lap** | +0.0241 – +0.0655 |
| fuel-limited (10) | **+0.0040 s/lap** | −0.2743 – +0.0495 |

Mann-Whitney **p = 0.0013**. Where the stop is cheap, what decides it is
whether the tyre is actually going away.

## The class was a proxy; the mechanism is the stop

An earlier version of this finding said "GT3 is tyre-limited where prototypes
are not". That reads as a fact about cars, and it is not one. Restricted to
the cheap-stop entries, the split happens *inside* every class:

| class | cheap-stop entries | of those, tyre-limited |
|---|---|---|
| IMSA GTD | 9 | 5 |
| IMSA GTD PRO | 3 | 2 |
| IMSA GTP | 2 | 1 |
| ELMS LMP2 | 1 | 1 |
| WEC HYPERCAR | 2 | 0 |
| ELMS LMP2 Pro/Am | 2 | 0 |

GT3 dominates the tyre-limited list only because GT3 races are where cheap
stops are common — a GT3 service is quicker in absolute terms and GT3
championships run more short sprint rounds. Condition on the stop cost and the
class stops mattering. That is the difference between a correlation worth
reporting and a mechanism worth believing.

## Why this needed four series

With WEC alone the answer was "never" — every Hypercar stop is expensive, so
condition 1 never clears and the question never arises. With IMSA GTP added it
was "never, except Laguna Seca", which reads as a curiosity. Only once GT3 and
ELMS supplied enough entries on *both* sides of the pit-loss threshold did the
threshold itself become visible.

That is an argument for breadth over depth in this kind of work, and it is
worth stating because the instinct runs the other way: more seasons of the
same class would never have found this. The variable that mattered had almost
no variance until a fourth series was added.

## Limits, stated

- **Nine positives.** The pit-loss edge at 22.5 s is where the data happens to
  stop, not a measured boundary; the honest claim is that no counterexample
  exists in 66 entries, not that 23 s is safe.
- **Time-only objective.** These optima ignore track position and multi-class
  traffic. An extra stop that is faster on paper can still lose a real race,
  which is exactly the limitation the F1 audit documents for Monaco.
- **One entry per circuit-class**, using a representative season. Repeating
  this per season would give a better-powered version of the same test.
- The fuel-limited group's slope range includes physically impossible negative
  values (−0.27 s/lap), which are noisy per-race fits on small fields rather
  than measurements — they widen the comparison group without changing its
  centre.

## Reproducing

```bash
python scripts/run_multistop.py    # writes data/derived/endurance/multistop_plans.csv
```

Every number above is a group statistic over that one committed artifact, and
the two tests are pinned in `tests/test_multistop.py`.
