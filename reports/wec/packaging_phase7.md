# WEC — Phase 7: packaging

*This report covers WEC only. IMSA has its own phase 7
([`reports/imsa/packaging_phase7.md`](../imsa/packaging_phase7.md)) and the
two are deliberately never merged: they share an upstream dataset and a
simulator engine, and almost nothing else that matters to a strategy model.*

Phase 7 is not new modelling. It answers one question — *can someone else
run this?* — and writes up what this project learned that is worth giving
back to the people who maintain the data it depends on.

## 1. What was actually shipped for WEC

| | |
|---|---|
| Series / class | WEC, HYPERCAR |
| Seasons | 2022–2026 |
| Races with lap data (eligible) | **28**, across 11 circuits |
| Races with flag data | **33** — a wider pull, because neutralisation rates need every race they can get, not just the ones with clean laps |
| Neutralisation events measured | **44 Safety Cars, 18 FCY periods** |
| Phase reports | `reports/wec/` — phases 0–6, plus this one |

The two race counts differ on purpose and the difference is not a defect:
the degradation and simulator layers need per-lap times of a usable quality
(≥ 4 cars, ≥ 40 laps), while the neutralisation layer only needs the flag
timeline, so it deliberately uses every race available. Five WEC races carry
usable flags but not usable laps.

## 2. Clean-clone check

The Definition of Done for this phase is that a fresh clone reproduces the
work without a hidden local file, an uncommitted artifact, or network
access. Evidence, not assertion:

- `git clone` into an empty directory, then run the endurance-scoped test
  subset — see §5 for the exact command. All WEC derived data is committed
  under `data/derived/wec/` and `data/derived/endurance/`, so nothing in
  this scope touches the network.
- Every reported number has a drift guard: the committed artifact must equal
  a fresh recomputation, so a stale CSV fails the suite instead of quietly
  going out of date.
- `scripts/run_multistop.py` regenerates `multistop_plans.csv`
  byte-for-byte, which is how the phase-4/6 refactors were verified.

One documented skip exists project-wide: `tests/test_f1_history.py` skips
when the Kaggle F1 export is absent. It is gitignored external data and is
F1's breadth layer, not WEC's — no WEC result depends on it.

## 3. What a reader can do without running anything

Each phase's full output is a committed markdown report, and every number in
[`reports/wec/methodology.md`](methodology.md) traces to one of them. The
interactive demo ([`demo/README.md`](../../demo/README.md)) has a WEC panel
that refits a real race model live and shows both the next-stop Monte Carlo
and the exact multi-stop dynamic program, with WEC's own neutralisation
posterior — never IMSA's.

## 4. Contribution ideas for the upstream data community

WEC has no FastF1. FastF1 covers Formula 1 only, and this project therefore
replaced the entire F1 ingestion path for endurance with its own loader over
the community-maintained DuckDB at `hf://datasets/tobil/imsa/imsa.duckdb`,
whose `laps_with_metadata` view joins laps, stints, weather and event
metadata for WEC, IMSA, ELMS and ALMS.

The useful contribution is therefore **not** a new scraper. The data exists.
What does not exist is a packaged, tested client with a normalised schema —
and building one from timing feeds instead would mean reverse-engineering a
commercial live-timing provider, which is a far larger and far less
defensible undertaking than improving what is already published.

Four things this project found that are worth upstreaming:

1. **Document that `laps_with_metadata` mixes sessions.** Practice,
   qualifying, warm-up, test and race laps share the view. Filtering an
   event without also pinning `session = 'race'` silently returns several
   overlapping races' worth of lap numbers — silently, because the result is
   a perfectly well-formed frame. This project pins the session in the
   loader and regression-tests it.

2. **Document that `stint_number` is the driver stint, not the tyre
   stint.** Tyre life lives in `est_tire_age`, which resets independently.
   Endurance separates three things F1 conflates — pit visits, tyre life and
   driver stints — and a model that collapses them loses exactly the
   structure it needs.

3. **Flag rows are per car, and must be collapsed before they describe a
   race.** This is the one that cost this project a real bug: asking whether
   *any* car reported a caution flag counts a single car's transient reading
   as a race-wide neutralisation, which inflated WEC's measured FCY
   occurrence from a true 9 of 33 races to 24 of 33. The fix is a modal
   collapse — the flag most cars reported on that lap — and it belongs in
   the dataset's documentation, because every consumer will hit it.

4. **A normalised lap schema is the artifact worth extracting.**
   [`src/data/`](../../src/data/) is already a small, tested library: a
   `BaseLoader` interface, one normalised lap frame every series maps into,
   the two source traps above handled, local materialisation of remote
   queries, and a hard rule that a field the source cannot provide stays
   `NaN` rather than being invented. Packaged standalone it would be roughly
   what FastF1 is for F1 — at a scale of a few hundred lines, because the
   hard part (the data) is already someone else's finished work.

## 5. Reproducing WEC's numbers

```bash
git clone https://github.com/mohammedmedjadj/Motorsport-Strategy-Lab
cd Motorsport-Strategy-Lab
pip install -r demo/requirements.txt        # includes requirements.txt

# WEC's layer, offline, from the committed derived data:
pytest tests/test_endurance_loader.py tests/test_endurance_degradation.py \
       tests/test_endurance_validation.py tests/test_endurance_safety_car.py \
       tests/test_endurance_simulator.py tests/test_endurance_artifacts.py \
       tests/test_endurance_audit.py tests/test_endurance_audit_cases.py \
       tests/test_endurance_pit_loss_validation.py tests/test_multistop.py \
       tests/test_traffic.py tests/test_adversarial_endurance.py \
       tests/test_wec_reliability.py

# Regenerate the artifacts and confirm they do not move:
python scripts/run_endurance_models.py
python scripts/run_multistop.py
git status --short data/        # expected: empty
```

The endurance test modules cover WEC and IMSA together, because the loader,
the degradation fit and the simulator engine are shared code. What is *not*
shared — and what the suite checks separately — is every fitted quantity:
each series has its own scope, its own posteriors and its own artifacts.

To re-pull from the upstream DuckDB rather than read the committed CSVs, run
`scripts/run_endurance_flags.py` and `scripts/run_endurance_models.py` with
a refresh; that is the only step in this scope that needs the network.

## 6. What is deliberately not packaged

- **No pip package.** The project is a research repository, not a library;
  `src/data/` is the part that would justify extraction (§4.4), and that is
  a proposal here rather than a shipped artifact.
- **No live WEC ingestion.** There is no equivalent of F1's post-race
  refresh workflow for WEC, because the upstream dataset publishes on its
  own cadence and this project does not control it. Races appear when the
  source has them.
- **No tyre-compound layer.** The source carries no compound for WEC, so
  degradation is a single net slope. This is stated everywhere it matters
  rather than papered over with an assumed compound.
