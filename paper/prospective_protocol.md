# Prospective test of the committed-strategy replay

This file freezes a test before its data exist. It is committed before the
2026 São Paulo Grand Prix (race on 8 November 2026) is run, and the
repository's history is the record of that. The result will be reported
against this file whichever way it falls.

## What is frozen

Everything the committed replay uses, at the commit that adds this file:

- the planner: `src/simulator/` and `committed_lap` in
  `scripts/run_committed_strategy.py`, with `N_DRAWS = 1500` and
  `SEED = 20260712`;
- the decision rule: `src/audit/systematic.py` with `LOOKBACK = 5`,
  `N_FINISHERS = 5`, `MIN_FIRST_STOP_LAP = 8` and `N_RIVALS = 2`, the
  team's next stop (or the flag for a one-stop car) as the horizon, and wet or
  intermediate tyres skipped;
- the circuit models: the degradation coefficients, pit losses and
  neutralisation model committed in `data/derived/f1/` at this commit. They are
  **not** refitted on the new races.

The new races are ingested with the project's existing pipeline
(`scripts/run_ingestion.py`), unchanged except where a data source stops
answering, in which case the substitution is documented next to the result.

## Races

Every Formula 1 Grand Prix from the 2026 São Paulo Grand Prix onward: São
Paulo, Las Vegas, Qatar and Abu Dhabi in 2026, then the 2027 season as it is
run. A race with no fitted model for its circuit is skipped, as in the
published audit.

## Hypotheses

1. **Primary.** Over all replayed first stops in these races, the median of
   planner lap minus real lap lies inside the interval published in the paper
   for the committed replay, [+1, +4] laps.
2. **Secondary.** Over the one-stop decisions among them, the median is
   positive (the planner stops later than the team).

Both are reported with the race-clustered bootstrap used in the paper, with
the number of decisions and races. A primary result outside the interval is a
failure of the published claim, not a reason to change the protocol.

## Evaluation

The evaluation reads the frozen code and models above and writes its output to
`reports/f1/prospective_test.md`. It is added as a separate commit after the
races, so that the code that scores the test can be compared line by line with
the code frozen here.

## Amendment, 8 November 2026, still before the São Paulo race

A reviewer pointed out that the primary hypothesis above compares the median of
a new sample with a *confidence* interval for the published median, when what
is needed is a *prediction* interval for the median of a sample of the size
that will actually be observed. Four races are far too few for that interval to
be informative. The hypotheses are therefore restated as follows, before any of
the races they cover has been run.

The prediction intervals are computed by resampling whole races, with
replacement, from the 74 races of the published committed replay (seed
20261108, 20,000 draws), and taking the median of the decisions in each
resampled set of races.

1. **Primary: the 2027 season.** Every race of the 2027 season with a fitted
   model for its circuit. The median of planner lap minus real lap over its
   replayed first stops is predicted to lie in **[+1, +4.5]** laps, the 95%
   prediction interval for a set of 24 races. If fewer races are scored, the
   interval is recomputed for that number of races by the same procedure,
   which is fixed here.
2. **Secondary: the rest of 2026** (São Paulo, Las Vegas, Qatar, Abu Dhabi).
   The 95% prediction interval for four races is **[−2, +12]**. It is reported
   for completeness; a result inside it says little, and the primary test is
   the one that can fail.
3. **One-stop decisions** in either set: the median is predicted to be
   positive, reported with its race-clustered interval.

Nothing else in this file changes.
