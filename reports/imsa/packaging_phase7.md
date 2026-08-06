# IMSA — Phase 7: packaging

*This report covers IMSA only. WEC has its own phase 7
([`reports/wec/packaging_phase7.md`](../wec/packaging_phase7.md)) and the
two are deliberately never merged. They share an upstream dataset and a
simulator engine; they do not share a neutralisation regime, a scope, or a
single fitted number.*

Phase 7 is not new modelling. It answers one question — *can someone else
run this?* — and writes up what this project learned that is worth giving
back to the people who maintain the data it depends on.

## 1. What was actually shipped for IMSA

| | |
|---|---|
| Series / class | IMSA, GTP |
| Seasons | 2023–2026 |
| Races with lap data (eligible) | **33**, across 10 circuits |
| Races with flag data | **63** — a wider pull, because neutralisation rates need every race they can get, not just the ones with clean laps |
| Neutralisation events measured | **293 full-course yellows, zero Safety Cars** |
| Phase reports | `reports/imsa/` — phases 0–6, plus this one |

That last row is IMSA's defining property and the single strongest reason
this series is modelled apart from WEC. Across 63 races the source records
no Safety Car at all. The model does **not** respond by hard-coding "IMSA
never sees one": the SC hazard is a Jeffreys-prior floor (half a
pseudo-event over the same exposure), and the SC pace ratio falls back to
the measured FCY ratio, because an absence of evidence in 63 races is not
evidence of impossibility. WEC, over its 33 races, measures 44 Safety Cars
and 18 FCY periods. Pooling the two would produce a hazard model that
describes neither series.

## 2. Clean-clone check

The Definition of Done for this phase is that a fresh clone reproduces the
work without a hidden local file, an uncommitted artifact, or network
access. Evidence, not assertion:

- `git clone` into an empty directory, then run the endurance-scoped test
  subset — see §5 for the exact command. All IMSA derived data is committed
  under `data/derived/imsa/` and `data/derived/endurance/`, so nothing in
  this scope touches the network.
- Every reported number has a drift guard: the committed artifact must equal
  a fresh recomputation, so a stale CSV fails the suite instead of quietly
  going out of date.
- The field-wide standing-start trim (§4.3) carries its own regression test,
  so the data-quality bug it fixes cannot silently return.

One documented skip exists project-wide: `tests/test_f1_history.py` skips
when the Kaggle F1 export is absent. It is gitignored external data and is
F1's breadth layer, not IMSA's — no IMSA result depends on it.

## 3. What a reader can do without running anything

Each phase's full output is a committed markdown report, and every number in
[`reports/imsa/methodology.md`](methodology.md) traces to one of them. The
interactive demo ([`demo/README.md`](../../demo/README.md)) has an IMSA
panel that refits a real race model live and shows both the next-stop Monte
Carlo and the exact multi-stop dynamic program, using IMSA's own posterior —
and stating on the page that its Safety Car hazard is a prior floor rather
than a measurement.

## 4. Contribution ideas for the upstream data community

IMSA has no FastF1. FastF1 covers Formula 1 only, so this project replaced
the entire F1 ingestion path for endurance with its own loader over the
community-maintained DuckDB at `hf://datasets/tobil/imsa/imsa.duckdb`, whose
`laps_with_metadata` view joins laps, stints, weather and event metadata for
IMSA, WEC, ELMS and ALMS.

The useful contribution is therefore **not** a new scraper. The data exists.
What does not exist is a packaged, tested client with a normalised schema.

Four things this project found that are worth upstreaming:

1. **Document that `laps_with_metadata` mixes sessions.** Practice,
   qualifying, warm-up, test and race laps share the view. Filtering an
   event without also pinning `session = 'race'` silently returns several
   overlapping races' worth of lap numbers — silently, because the result is
   a perfectly well-formed frame.

2. **Document that `stint_number` is the driver stint, not the tyre
   stint.** Tyre life lives in `est_tire_age`, which resets independently.
   At Watkins Glen 2023 the #01 GTP car made 13 pit visits across only 4
   driver stints; the difference is fuel-only stops, and a schema that
   collapses the two destroys exactly the structure an endurance strategy
   model needs.

3. **Standing-start and early-caution laps are labelled green.** This is the
   IMSA-specific finding, and it was found the hard way: at Road America
   2024 (a 62-lap sprint) laps 2 and 3 carry the `GF` flag while the field's
   median lap time on them is **246.6 s and 197.8 s against a ~113 s green
   median**. A per-car quantile trim cannot catch it — in a short race the
   anomaly compromises most of each car's laps, pushing every car's own
   cutoff up to swallow it. This project added a field-wide trim (a lap
   number is dropped when the *median across all cars* exceeds 1.3× the
   race's green median) with a regression test. Upstream, the cleaner fix is
   to not label those laps green.

4. **Is IMSA's Safety Car genuinely absent, or simply never emitted?** In 63
   races the dataset records 293 full-course yellows and no Safety Car. That
   is plausible — IMSA's procedure is built on full-course cautions — but a
   consumer cannot distinguish "this series does not use them" from "this
   field is not populated for this series", and the two imply very different
   models. A line in the dataset's documentation would settle it. This is
   the single most valuable question this project would ask upstream.

The extractable artifact is [`src/data/`](../../src/data/): a `BaseLoader`
interface, one normalised lap frame every series maps into, the traps above
handled, local materialisation of remote queries, and a hard rule that a
field the source cannot provide stays `NaN` rather than being invented.
Packaged standalone it would be roughly what FastF1 is for F1 — at a scale
of a few hundred lines, because the hard part is already someone else's
finished work.

## 5. Reproducing IMSA's numbers

```bash
git clone https://github.com/mohammedmedjadj/Motorsport-Strategy-Lab
cd Motorsport-Strategy-Lab
pip install -r demo/requirements.txt        # includes requirements.txt

# IMSA's layer, offline, from the committed derived data:
pytest tests/test_endurance_loader.py tests/test_endurance_degradation.py \
       tests/test_endurance_validation.py tests/test_endurance_safety_car.py \
       tests/test_endurance_simulator.py tests/test_endurance_artifacts.py \
       tests/test_endurance_audit.py tests/test_endurance_audit_cases.py \
       tests/test_endurance_pit_loss_validation.py tests/test_multistop.py \
       tests/test_traffic.py

# Regenerate the artifacts and confirm they do not move:
python scripts/run_endurance_models.py
python scripts/run_multistop.py
git status --short data/        # expected: empty
```

The endurance test modules cover IMSA and WEC together, because the loader,
the degradation fit and the simulator engine are shared code. What is *not*
shared — and what the suite checks separately — is every fitted quantity:
each series has its own scope, its own posteriors and its own artifacts.

To re-pull from the upstream DuckDB rather than read the committed CSVs, run
`scripts/run_endurance_flags.py` and `scripts/run_endurance_models.py` with
a refresh; that is the only step in this scope that needs the network.

## 6. What is deliberately not packaged

- **No pip package.** The project is a research repository, not a library;
  `src/data/` is the part that would justify extraction (§4), and that is a
  proposal here rather than a shipped artifact.
- **No live IMSA ingestion.** There is no equivalent of F1's post-race
  refresh workflow, because the upstream dataset publishes on its own
  cadence and this project does not control it.
- **No tyre-compound layer.** The source carries no compound for IMSA, so
  degradation is a single net slope.
- **No reliability layer.** WEC has one, built from a separate results-level
  Kaggle export covering 2011–2023. No equivalent long-baseline results
  source was found for IMSA, so the layer is absent rather than
  approximated — an asymmetry between the two series that is real, and
  stated here rather than hidden by presenting them together.
