# motorsport-strategy-lab — Race Strategy Simulator & Decision Audit

A research project on motorsport race strategy: a three-layer decision-support
system (tyre degradation model, safety-car probability model, Monte Carlo
strategy simulator) plus a retrospective audit comparing the model's
recommendations against real strategy calls from actual races.

Built first on **Formula 1** (via FastF1) and since extended to **endurance
racing — IMSA and WEC**, which FastF1 does not cover and which required a new
ingestion path and re-derived models. See
[Endurance racing](#endurance-racing-imsa--wec).

**Status: complete (phases 0-7).** Full methodology and findings:
[`reports/methodology.md`](reports/methodology.md).

## Why this project

Most public F1 data projects stop at "predict the pit-stop lap" â€” a basic
regression that already exists in dozens of notebooks. This project goes
further:

1. It quantifies **uncertainty** instead of producing a single number â€” a
   pit window is a distribution of outcomes, not a point estimate.
2. It combines two independently modelled risk sources (tyre degradation and
   safety-car deployment) inside a **Monte Carlo simulator**, which is how
   real strategy teams reason about races.
3. Its differentiating core is a **retrospective decision audit**: for real,
   documented race moments (a successful undercut, a missed one, a safety car
   that reshuffled the order), we compare what the model would have
   recommended at that instant against what the strategists actually did, and
   analyse the gap honestly â€” including when the model is wrong.

F1 data comes from [FastF1](https://github.com/theOehrly/Fast-F1); endurance
data from a community-maintained IMSA/WEC DuckDB (see
[Endurance racing](#endurance-racing-imsa--wec)). No data is invented or
simulated to fill gaps; missing data is documented as missing.

## Key results

- **The audit's headline (Case A, Barcelona 2024):** Verstappen's real
  lap-17 covering stop costs +3.2s in median race time vs the model's
  optimum â€” yet holds the highest P(best) (0.43) and the best P(ahead of
  Norris) (0.70). Median race time alone mis-ranks real decisions; the
  distribution outputs are the point of the design.
- **A limitation turned into a measurement (Case C, Singapore 2023):** the
  model calls Sainz's universally-praised SC stop ~6.5s "too early" â€”
  because it does not model field bunching. The audit converts that known
  gap into a measured bias for SC-window decisions at the front.
- **Decision vs outcome (Case D):** Mercedes' Singapore 2023 VSC gamble
  failed on track but was the right bet â€” better median time AND higher
  win probability than staying out.
- **Cross-season instability:** degradation slopes fitted on two seasons
  often predict a third season's stints worse than a flat line (negative
  within-stint RÂ²), while the same pipeline scores 0.85 on synthetic data
  at its noise floor. All coefficients are therefore used as
  distributions, never point values.
- **Folklore checked against data:** Monaco's "guaranteed safety car" is
  3 races out of 7 (2018-2025), P = 0.44 [0.14, 0.77].

Full numbers: [`reports/`](reports/) â€” one committed report per phase.

## For the FastF1 community

Three pieces of this repo are designed to be reusable beyond the project
(see `reports/methodology.md` for context):

1. the flag-based cleaning layer (`src/ingestion/cleaning.py`) â€” pace-lap
   selection with per-reason accounting instead of silent drops;
2. the `TrackStatus` event extractor (`src/safety_car/dataset.py`) â€”
   SC/VSC/red periods mapped to race laps, with the fuzzy-match guard for
   cancelled events (`src/ingestion/loader.py`);
3. the measured circuit constants (pit losses, SC/VSC pace ratios) and
   the method to recompute them from any race.

## System overview

| Layer | Module | What it does |
|---|---|---|
| 1. Tyre degradation | `src/degradation/` | Models lap-time evolution vs tyre age, per compound and per circuit |
| 2. Safety-car risk | `src/safety_car/` | Models SC/VSC deployment probability per circuit from historical `TrackStatus` data, with explicit uncertainty |
| 3. Strategy simulator | `src/simulator/` | Monte Carlo simulation combining layers 1â€“2 to recommend a pit window at a given race state, with a full outcome distribution |
| 4. Decision audit | `src/audit/` | Replays real race decision points through the simulator and compares against what actually happened |

### Modelling extensions

Built on top of the four core layers, each with tests and an honest write-up in
[`reports/`](reports/):

- **Vectorised Monte Carlo** — the simulator evaluates all draws in one broadcast
  pass (~12x faster; bit-identical to the per-draw path).
- **Optional quasi-Monte Carlo** (`simulate(..., sampler="qmc")`) — scrambled
  Sobol' over the smooth coefficient/noise subspace; large variance reduction on
  smooth integrands, a no-op when safety-car jumps dominate (measured, documented).
- **Multi-objective Pareto front** (`recommend.pareto_front`) — exact non-dominated
  pit laps trading race time against track position, the trade-off the single-
  objective recommendation collapses.
- **Gaussian-process degradation** (`degradation.gp_model`) — a nonparametric
  robustness check that confirms the cross-season instability is intrinsic to the
  data, not an OLS artefact (GP ties OLS out-of-sample).
- **Online Kalman filter** (`degradation.kalman`) — estimates the current tyre
  degradation rate lap-by-lap with uncertainty; converges to the retrospective
  slope and tracks a mid-stint cliff.

## Endurance racing (IMSA / WEC)

FastF1 covers only Formula 1, so endurance racing needed a new ingestion path
and its own models. Source: a community-maintained DuckDB whose
`laps_with_metadata` view carries IMSA, WEC, ELMS and ALMS together.

**Phase 0 verified the data before any architecture was written**, which caught
two traps that would have silently corrupted every downstream model:

- the source mixes practice/qualifying/warmup with race laps, so an unfiltered
  event made the #01 GTP car "run" 266 laps of a 201-lap race;
- `stint_number` is the **driver** stint, not the tyre stint — tyre life lives in
  `est_tire_age` and resets independently. The #01 car made **13 pit visits
  across only 4 driver stints**; the gap is fuel-only stops.

| Layer | Module | Finding |
|---|---|---|
| Data | `src/data/` | Normalised multi-series lap schema; 2 real races committed for offline tests |
| Degradation | `src/degradation/endurance.py` | Spa +0.042 s/lap; Watkins Glen −0.007 (covers zero) |
| Neutralisations | `src/safety_car/endurance.py` | 96 races; IMSA FCY P=0.96, WEC prefers the Safety Car (P=0.57) |
| Simulator | `src/simulator/endurance.py` | Pit loss ~62 s, FCY pace ratio ~2.0×, fuel range ~30 laps |

Three results worth stating plainly:

- **The two series are not interchangeable.** An IMSA race is near-certain to be
  neutralised (P = 0.96, one FCY per ~48 laps); WEC reaches for a Safety Car
  about twice as often as a Full Course Yellow.
- **Fuel is a binding constraint, and F1 has no equivalent.** At Spa the tyres
  want a stop near lap 106; the tank runs dry at lap 90, and that boundary — not
  tyre wear — decides the strategy.
- **A fuel/degradation split was attempted and rejected on the evidence.** 88-93%
  of pit visits also change tyres, leaving the two regressors correlated +0.95 to
  +0.99, so only the identified *net* slope is quoted, behind a `separable` flag.

Reports: [Phase 0](reports/endurance_availability_phase0.md) ·
[degradation](reports/endurance_degradation_phase1.md) ·
[neutralisations](reports/endurance_safety_car_phase2.md) ·
[simulator](reports/endurance_simulator_phase3.md)

## Data scope (MVP)

**Seasons: 2023, 2024, 2025** â€” the three most recent completed seasons, all
inside the 2022â€“2025 ground-effect regulation era, so car and tyre behaviour
is broadly comparable across the dataset. (2022 is deliberately excluded from
the MVP: early ground-effect cars suffered porpoising issues that add noise
to degradation modelling; it can be added later as a robustness check.)

**Circuits (4), chosen to contrast the two risk dimensions the system models:**

| Circuit | Grand Prix | Why it is in the set |
|---|---|---|
| Monaco | Monaco GP | Street circuit, historically among the highest SC rates, near-zero overtaking â€” strategy is almost purely track-position driven |
| Marina Bay | Singapore GP | Street circuit with a near-100% historical SC rate â€” the strongest test for the SC-probability layer |
| Barcelona-Catalunya | Spanish GP | Permanent circuit, historically low SC rate, high front-tyre stress â€” a clean laboratory for the degradation layer |
| Suzuka | Japanese GP | Permanent high-load circuit, low SC rate, strong tyre energy â€” contrasts with Barcelona on degradation character |

This gives a 2Ã—2-ish contrast: high-SC/low-degradation-signal street tracks
vs low-SC/high-degradation permanent tracks, which is exactly the trade-off
the Monte Carlo simulator has to arbitrate.

**Verified availability.** The table in
[`reports/data_availability_phase0.md`](reports/data_availability_phase0.md)
is generated by [`scripts/check_data_availability.py`](scripts/check_data_availability.py)
from real FastF1 session loads (laps, track status, weather) for all 12
circuit-season combinations â€” the selection above was only frozen after that
check passed. Known caveats found during verification are listed in that
report and re-stated in the Limitations section of the methodology report.

## Repository structure

```
motorsport-strategy-lab/
  data/
    cache/              # FastF1 cache (gitignored)
    derived/            # small versioned derived datasets (committed)
  src/
    ingestion/          # FastF1 loading, cleaning, validation
    degradation/        # tyre degradation: OLS fixed-effects model + LORO CV,
                        #   GP robustness check (gp_model), online Kalman filter
    data/               # multi-series loaders (IMSA/WEC); normalised lap schema
    safety_car/         # SC/VSC probability model; endurance FCY/Safety Car
    simulator/          # vectorised Monte Carlo simulator (optional Sobol QMC),
                        #   multi-objective Pareto front over pit laps
    audit/              # retrospective audit scripts
  notebooks/            # exploration only â€” never the source of truth
  scripts/              # one-shot utilities (e.g. data availability check)
  tests/                # pytest: ingestion, models, simulator invariants
  reports/              # methodology report, audit cases, data quality
  README.md
  pyproject.toml
  requirements.txt      # top-level deps; requirements.lock pins exact versions
```

## Engineering rules

- **No fabricated data.** If FastF1 does not provide something, it is
  documented as unavailable, never estimated silently.
- **No data leakage.** The decision models only use information that was
  knowable at the simulated moment of the race. Race outcomes never leak into
  features.
- **Uncertainty is first-class.** Every probability and every recommendation
  ships with an interval or a distribution, never a bare point estimate.
- **Reproducibility.** Fixed seeds for all stochastic code (Monte Carlo),
  pinned dependency versions (`requirements.lock`), FastF1 cache enabled.
- **Tested.** `pytest` covers ingestion parsing/cleaning, degradation model
  non-regression, and simulator physical-consistency invariants.
- **Typed and documented.** Docstrings and type hints everywhere in `src/`.

## Setup

```bash
git clone <repo-url>
cd motorsport-strategy-lab
python -m venv .venv
.venv/Scripts/activate          # Windows; use .venv/bin/activate on Unix
pip install -r requirements.txt # or requirements.lock for exact pins
python scripts/check_data_availability.py   # populates the FastF1 cache
pytest
```

The first data run downloads several hundred MB into `data/cache/`
(gitignored). Subsequent runs are served from the cache.

## Phase plan & Definition of Done

Each phase stops for explicit validation before the next one starts.

| Phase | Deliverable | Definition of Done |
|---|---|---|
| 0. Setup & scoping | Repo, environment, verified data scope, this README | Repo initialised; all 12 candidate sessions load through FastF1 with laps + `TrackStatus` + weather confirmed present; plan validated |
| 1. Ingestion pipeline | `src/ingestion/` + tests + data quality report | One clean, documented DataFrame per circuit-season; in/out laps and inaccurate laps handled; tests pass; report states % of laps excluded and why |
| 2. Tyre degradation model | `src/degradation/` + tests + figures | Per-compound/per-circuit fits with honest metrics (RÂ², error) from cross-validation that never mixes laps of one race across train/test; limitations documented (e.g. fuel effect not isolated) |
| 3. SC/VSC probability model | `src/safety_car/` + tests | Per-circuit deployment probabilities **with confidence intervals**; explicit discussion of small-sample reliability |
| 4. Monte Carlo simulator | `src/simulator/` + tests | Given (circuit, current lap, compound, tyre age, gaps), produces a pit-window recommendation as an outcome distribution; seeded and reproducible; invariant tests pass (window inside race bounds, probabilities sum to 1, etc.) |
| 5. Retrospective audit | `reports/audit_cases.md` | 4â€“6 real race moments (validated with Mohammed) replayed through the simulator; model vs real decision compared quantitatively; disagreements analysed honestly |
| 6. Methodology report | `reports/methodology.md` | Mini-paper (abstract, motivation/related work, method, results, limitations, future work); every number traceable to project output; no invented citations |
| 7. Packaging | Final README, clean-clone check | Everything runs from a fresh clone; 2â€“3 concrete FastF1-community contribution ideas proposed; short factual activity description drafted |

## Known limitations (stated up front)

- **Sample size for SC probability is structurally small** (one race per
  circuit per season, ~3 usable races per circuit in the MVP window plus
  historical extensions where data quality allows). The SC model will report
  wide intervals; that is a feature, not a bug.
- **Fuel load and tyre age are confounded** within a stint; without private
  telemetry the fuel effect can only be partially controlled (e.g. by
  modelling a linear fuel correction). This will be quantified and discussed
  in Phase 2 rather than hidden.
- **Track evolution, traffic and driver-specific pace** are not explicitly
  modelled in the MVP; they are absorbed into residual noise.

## License & attribution

Data accessed through FastF1, which sources official F1 live timing. This
project is unaffiliated with Formula 1. Code license to be chosen before
public release (MIT planned).

