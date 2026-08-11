# ELMS — Phase 7: packaging

*ELMS only. WEC and IMSA have their own; the three endurance series are never
merged into one write-up.*

Phase 7 is not new modelling. It answers *can someone else run this?* and
records what the series contributed that is worth taking elsewhere.

## 1. What was shipped

| | LMP2 | LMP2 Pro/Am |
|---|---|---|
| race-seasons | 25 of 29 eligible | 17 of 17 |
| seasons | 2021–2025 | 2023–2025 |
| circuits | 9 | 8 |
| race laps | 35,750 | 16,722 |
| kept for modelling | 69.9% | 69.3% |

Flag data covers 29 ELMS races, a wider pull than the lap scope, because
neutralisation rates need every race available while degradation needs clean
laps. Phases 0–4, a per-decision audit, a crew-rating comparison and this
document.

## 2. Clean-clone check

All ELMS derived data is committed under `data/derived/elms/` and
`data/derived/endurance/`, so everything in this scope runs offline from a
fresh clone. Every reported number carries a drift guard: the committed
artifact must equal a fresh recomputation, so a stale CSV fails the suite
rather than quietly ageing.

```bash
git clone https://github.com/mohammedmedjadj/Motorsport-Strategy-Lab
cd Motorsport-Strategy-Lab
pip install -r demo/requirements.txt

pytest tests/test_endurance_loader.py tests/test_endurance_degradation.py        tests/test_endurance_validation.py tests/test_endurance_safety_car.py        tests/test_endurance_simulator.py tests/test_endurance_artifacts.py        tests/test_endurance_audit.py tests/test_endurance_audit_cases.py        tests/test_multistop.py tests/test_traffic.py

python scripts/run_endurance_models.py
python scripts/run_multistop.py
git status --short data/        # expected: empty
```

## 3. What ELMS contributed

**A negative control that closed a hypothesis.** LMP2 is near-spec — one
chassis, one engine — so it tests whether the season-to-season instability of
degradation slopes comes from heterogeneous, BoP-adjusted machinery. It does
not: slopes fail to transfer here exactly as they do in Hypercar and GTP. That
question had been open since the F1 phase and could not be answered inside any
series already modelled.

**A second, independent crew-rating experiment** — and one that disagrees with
IMSA's. Two natural experiments now exist in this project; they do not agree,
and [`crew_rating_findings.md`](crew_rating_findings.md) reports that rather
than choosing the significant one.

**A third neutralisation regime** (23 of 29 races see a Safety Car, against
WEC's 19 of 33 and IMSA's 0 of 63), which is the third independent
confirmation that pooling series produces a model describing none of them.

**A bug in the scope key, and a second in the flag query.** Both were caught by
guards rather than by wrong numbers — see phase 3.

## 4. Known limitations, carried forward

- **No race-time term.** Track evolution lands on the tyre-age coefficient with
  its sign inverted; 12 of 42 ELMS races fit a negative slope. A correction was
  built, validated on synthetic data and **withdrawn** because it made the
  real-data refit worse
  ([`reports/track_evolution_omitted_variable.md`](../track_evolution_omitted_variable.md)).
  Read every ELMS slope as a lower bound.
- **No reliability layer.** WEC has one from a results-level export; no
  equivalent long-baseline source was found for ELMS, so it is absent rather
  than approximated.
- **The pit-procedure crew gap is unexplained**, not a finding — see phase 4.
- **The single-stop engine cannot represent a double stop under one caution**,
  which both Mugello 2024 class winners actually made.

## 5. Contribution ideas

Same as the other endurance series: the extractable artifact is
[`src/data/`](../../src/data/) — a tested, normalising client over the
community DuckDB, with the source's traps handled. ELMS adds one trap of its
own worth documenting upstream: **the `LMP2` label changes meaning in 2023**,
covering every entry before and the professional subset after. Nothing in the
data marks that change, and a consumer pooling seasons compares two different
populations without any error to warn them.
