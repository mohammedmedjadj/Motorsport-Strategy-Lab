# Reports — the map

Four series, seven modelled classes. **Nothing is pooled across a series, and
nothing is pooled across a class within one.** That rule is not tidiness: IMSA's
GTP and GTD run the same rounds and disagree on this project's headline
endurance conclusion, so a single "IMSA" fit would have averaged the
disagreement away.

The directory layout follows that rule exactly — a class that is modelled
separately gets its own branch.

```
reports/
  f1/                  Formula 1 — one class, 26 circuits
  wec/                 WEC — one class (Hypercar)
    hypercar/          .. its complete per-race tables
  imsa/                IMSA — three classes, never pooled
    gtp/               .. manufacturer prototypes
    gtd/               .. GT3, Pro/Am (mandatory bronze/silver driver)
    gtdpro/            .. GT3, all-professional line-ups
  elms/                ELMS — two classes, never pooled
    lmp2/              .. near-spec Oreca 07, professional crews from 2023
    lmp2_proam/        .. the same car, mandatory bronze-rated driver
  cross_series/        results that need more than one championship to exist
  prediction/          out-of-sample calibration of the neutralisation models
```

## Two kinds of document

**Generated** — files named `*_all_races.md` are written by
[`scripts/run_class_reports.py`](../scripts/run_class_reports.py) from the
committed CSVs. Every one covers **all** of its class's race-seasons: every
fitted slope with its interval, every lap-accounting row, every validation fold,
every full-race plan. They carry a `GENERATED` header and must not be edited by
hand.

They exist because the hand-written reports were not per-class and the gap was
invisible from reading them. `imsa/gtp/data_quality_phase1.md` opens "lap-level
accounting for every scoped race-season" and accounts for 10; the artifact
carries 140 across three classes. GTD's 60 race-seasons and GTD PRO's 47 had no
lap accounting anywhere.

**Hand-written** — everything else. The phase reports, the methodologies, the
audits, the cross-series results. These carry the argument; the generated files
carry the evidence. A generated report cannot go stale, and a hand-written one
can, which is what [`tests/test_reports_are_not_stale.py`](../tests/test_reports_are_not_stale.py)
is for.

## The seven classes at a glance

| class | race-seasons | circuits | seasons | median slope | tyre-change premium |
|---|---|---|---|---|---|
| [F1](f1/) | 115 rounds | 26 | 2022–2026 | per compound, see [degradation](f1/degradation_phase2.md) | — (refuelling banned) |
| [WEC Hypercar](wec/hypercar/) | 28 | 11 | 2022–2026 | +0.0139 s/lap | 21.6 s |
| [IMSA GTP](imsa/gtp/) | 33 | 10 | 2023–2026 | +0.0166 s/lap | **8.7 s** |
| [IMSA GTD](imsa/gtd/) | 60 | 13 | 2021–2026 | +0.0200 s/lap | **17.6 s** |
| [IMSA GTD PRO](imsa/gtdpro/) | 47 | 12 | 2022–2026 | +0.0190 s/lap | 16.9 s |
| [ELMS LMP2](elms/lmp2/) | 25 | 9 | 2021–2025 | +0.0161 s/lap | 25.1 s |
| [ELMS LMP2 Pro/Am](elms/lmp2_proam/) | 17 | 8 | 2023–2025 | +0.0205 s/lap | 35.4 s |

GTD and GTD PRO are the **same car under the same Balance of Performance**, and
differ only in whether an amateur-rated driver is mandatory. Keeping them apart
is what makes the crew-rating question measurable without any external
driver-rating data — and the 8.7 s against 17.6 s in that last column is the
measurement that showed the tyre-change premium is a property of the car, not
of the crew.

## Where to start

- **What more than one championship says that one cannot** —
  [`cross_series/synthesis.md`](cross_series/synthesis.md).
- **The rule that overturned this project's own conclusion twice** —
  [`cross_series/when_tyres_beat_fuel.md`](cross_series/when_tyres_beat_fuel.md).
- **A defect this project has not fixed, written up as such** —
  [`cross_series/track_evolution_omitted_variable.md`](cross_series/track_evolution_omitted_variable.md).
- **The full write-ups**, one per series, never merged:
  [F1](f1/methodology.md) ·
  [WEC](wec/methodology.md) ·
  [IMSA](imsa/methodology.md) ·
  [ELMS](elms/methodology.md).
