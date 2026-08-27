# ELMS — Phase 4: simulator and full-race plans

*ELMS only, per class. Every constant below is measured on ELMS races.*

## Measured inputs

| | LMP2 | LMP2 Pro/Am |
|---|---|---|
| median pit loss | 64.8 s | 62.2 s |
| median fuel range | 24 laps | 24.5 laps |
| tyre-change premium | **25.1 s** | **35.4 s** |
| fuel-only stop | 44.4 s | 35.2 s |

ELMS stops are expensive on a short tank, which is why the series is almost
entirely fuel-limited on stop count.

The crew comparison at the stop is reported in
[`crew_rating_findings.md`](crew_rating_findings.md) §4 and is **not** taken at
face value there: the two classes differ by 10.3 s in premium but also by 9.2 s
in the fuel-only stop, which a driver rating should not change. That pattern
looks like a difference in procedure or sample rather than crew, and is
recorded as unexplained.

## Full-race plans

The exact dynamic program over fuel-feasible stint partitions, run on every
scoped circuit:

| | LMP2 | LMP2 Pro/Am |
|---|---|---|
| circuits planned | 9 | 8 |
| optimum equals the fuel minimum | 8 of 9 | **8 of 8** |
| tyre-limited | 1 (Mugello) | none |

**Mugello LMP2 is the exception, and it is the pit loss that makes it.** Its
9.2 s stop is the cheapest measured anywhere in ELMS — the next is 14.4 s, and
the series median is 64.9 s — and its +0.0655 s/lap slope is the steepest.
Both conditions of the cross-series rule are met.

Mugello Pro/Am, at the same circuit in the same year, is **not** tyre-limited:
its 10.8 s stop is comparably cheap but its slope is shallower. That pair is
one of the cleanest illustrations available that the rule needs both terms —
see [`reports/when_tyres_beat_fuel.md`](../cross_series/when_tyres_beat_fuel.md).

## Track position

Median adjacent-swap rate **0.0463** across 17 circuit-class entries, position
reconstructed from cumulative time within the class. Mugello is the least
sticky (0.0713 LMP2), Aragon the most (0.0208).

## Scope limitation, stated

The single-stop engine answers "when is the next stop?" and models one stop.
ELMS races take 4–6, so its totals rank candidates rather than being achievable
race times, and the full plan comes from the dynamic program above. The
per-decision audit ([`audit_cases.md`](audit_cases.md)) shows the sharpest
consequence: at Mugello 2024 both class winners stopped twice consecutively
under one Safety Car, a strategy the engine has no way to represent.

## Reproducing

```bash
python scripts/run_endurance_models.py   # pit loss, fuel range, traffic, track position
python scripts/run_multistop.py          # full-race plans
```
