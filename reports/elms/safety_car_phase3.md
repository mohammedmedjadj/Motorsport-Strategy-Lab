# ELMS — Phase 3: neutralisations

*ELMS only. The posteriors below are fitted on ELMS races alone and are never
pooled with WEC's or IMSA's — the whole point of this phase is that the three
differ.*

## A third regime, distinct from both series already modelled

| series | races | with ≥1 FCY | with ≥1 Safety Car | SC rate / lap |
|---|---|---|---|---|
| IMSA | 63 | 61 | **0** | 0.00004 (prior floor) |
| WEC | 33 | 9 | 19 | 0.00605 |
| **ELMS** | **29** | **15** | **23** | **0.01592** |

ELMS is the most Safety-Car-dominated series in this project: 79% of its races
see at least one, against WEC's 58% and IMSA's none at all. Its per-lap SC
rate is 2.6× WEC's.

Posterior estimates, Beta-Binomial for occurrence and Gamma-Poisson for rate,
both with Jeffreys priors, exactly as for the other two series:

- **FCY** — 15 of 29 races, P(≥1) = 0.517 [0.341, 0.690], rate 0.00760 /lap
  [0.00499, 0.01076]
- **SC** — 23 of 29 races, P(≥1) = 0.783 [0.622, 0.909], rate 0.01592 /lap
  [0.01201, 0.02037]

Both intervals exclude zero comfortably, which IMSA's Safety Car does not —
there the posterior is a prior floor over 63 races with no observed event, and
the model refuses to encode "impossible" from an absence of evidence.

## Why this matters beyond bookkeeping

A pooled "endurance" neutralisation model would sit somewhere between 0.00004
and 0.01592 per lap for the Safety Car and describe **none** of the three
series. Every strategy conclusion that depends on the value of a neutralised
stop — which is most of them, since a stop under caution is discounted by the
pace ratio — would be wrong in a different direction for each championship.

This is the third independent confirmation of the separation rule this project
applies everywhere: WEC ≠ IMSA was the first, GTD ≠ GTP the second, and ELMS
is a third series that would have been averaged into a fiction.

## A bug this phase caught rather than produced

ELMS flags were absent from `scripts/run_endurance_flags.py`, whose query
hard-coded `series_code IN ('imsa', 'wec')`. The laps had already been scoped,
so models were being requested for a series with no posterior.

That did not produce wrong numbers: `endurance_models.load_race_model` raises
`KeyError: "no neutralisation posterior for series 'elms'"` rather than falling
back to a default prior. Without that guard, ELMS stop plans would have been
built on an **invented** neutralisation risk and looked entirely plausible.
The guard cost three lines and caught an error that would have been invisible
in the results.

## Reproducing

```bash
python scripts/run_endurance_flags.py    # network; writes race_flags.csv
python scripts/run_endurance_models.py   # offline
```

The three-regime contrast is pinned in `tests/test_endurance_safety_car.py`.
