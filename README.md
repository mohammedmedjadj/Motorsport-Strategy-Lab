# motorsport-strategy-lab — Race Strategy Simulator & Decision Audit

A research project on motorsport race strategy: a three-layer decision-support
system (tyre degradation model, safety-car probability model, Monte Carlo
strategy simulator) plus a retrospective audit comparing the model's
recommendations against real strategy calls from actual races.

Built first on **Formula 1** (via FastF1) and since extended to **endurance
racing — WEC and IMSA**, which FastF1 does not cover and which required a new
ingestion path and re-derived models, brought to the same depth as the F1
work: verified data availability, a fitted and cross-validated degradation
model, a Bayesian neutralisation model, and a Monte Carlo simulator, each with
its own committed report.

**Status: F1 complete (phases 0-7); WEC and IMSA extended through an
equivalent Phase 0-3.** Full F1 methodology: [`reports/methodology.md`](reports/methodology.md).
Jump to: [Formula 1](#formula-1) · [WEC](#wec) · [IMSA](#imsa).

## Why this project

Most public F1 data projects stop at "predict the pit-stop lap" — a basic
regression that already exists in dozens of notebooks. This project goes
further:

1. It quantifies **uncertainty** instead of producing a single number — a
   pit window is a distribution of outcomes, not a point estimate.
2. It combines two independently modelled risk sources (tyre degradation and
   safety-car deployment) inside a **Monte Carlo simulator**, which is how
   real strategy teams reason about races.
3. Its differentiating core is a **retrospective decision audit**: for real,
   documented race moments (a successful undercut, a missed one, a safety car
   that reshuffled the order), we compare what the model would have
   recommended at that instant against what the strategists actually did, and
   analyse the gap honestly — including when the model is wrong.

F1 data comes from [FastF1](https://github.com/theOehrly/Fast-F1); WEC and
IMSA data come from a community-maintained DuckDB (see [WEC](#wec) and
[IMSA](#imsa) below). No data is invented or simulated to fill gaps; missing
data is documented as missing, in every series.

## Repository map

The project is organised so each series is self-contained and symmetric:

```
src/degradation/   model.py (F1) | endurance.py + endurance_validation.py (WEC/IMSA, shared)
src/safety_car/    model.py (F1) | endurance.py (WEC/IMSA, shared)
src/simulator/      engine.py (F1) | endurance.py (WEC/IMSA, shared)
src/data/           F1 uses src/ingestion/ (FastF1); WEC/IMSA use base_loader.py + endurance_loader.py
data/derived/       f1/ | imsa/ | wec/ | endurance/ (cross-series neutralisation data)
reports/            f1/ | imsa/ | wec/ | methodology.md (F1 mini-paper)
```

WEC and IMSA share one loader and one degradation/neutralisation/simulator
module each (`*_endurance.py` / `endurance.py`), because both series need the
same three-way split — pit visit vs tyre change vs driver stint — that FastF1
never has to make for F1. Series-specific numbers (degradation slopes,
neutralisation rates, simulator constants) are always fitted and reported
separately; nothing is pooled across series.

---

## Formula 1

### Key results

- **The audit's headline (Case A, Barcelona 2024):** Verstappen's real
  lap-17 covering stop costs +3.2s in median race time vs the model's
  optimum — yet holds the highest P(best) (0.43) and the best P(ahead of
  Norris) (0.70). Median race time alone mis-ranks real decisions; the
  distribution outputs are the point of the design.
- **A limitation turned into a measurement (Case C, Singapore 2023):** the
  model calls Sainz's universally-praised SC stop ~6.5s "too early" —
  because it does not model field bunching. The audit converts that known
  gap into a measured bias for SC-window decisions at the front.
- **Decision vs outcome (Case D):** Mercedes' Singapore 2023 VSC gamble
  failed on track but was the right bet — better median time AND higher
  win probability than staying out.
- **Cross-season instability:** degradation slopes fitted on two seasons
  often predict a third season's stints worse than a flat line (negative
  within-stint R²), while the same pipeline scores 0.85 on synthetic data
  at its noise floor. All coefficients are therefore used as
  distributions, never point values.
- **Folklore checked against data:** Monaco's "guaranteed safety car" is
  3 races out of 7 (2018-2025), P = 0.44 [0.14, 0.77].

Full numbers: [`reports/f1/`](reports/f1/) — one committed report per phase.

### For the FastF1 community

Three pieces of this repo are designed to be reusable beyond the project
(see `reports/methodology.md` for context):

1. the flag-based cleaning layer (`src/ingestion/cleaning.py`) — pace-lap
   selection with per-reason accounting instead of silent drops;
2. the `TrackStatus` event extractor (`src/safety_car/dataset.py`) —
   SC/VSC/red periods mapped to race laps, with the fuzzy-match guard for
   cancelled events (`src/ingestion/loader.py`);
3. the measured circuit constants (pit losses, SC/VSC pace ratios) and
   the method to recompute them from any race.

### System overview

| Layer | Module | What it does |
|---|---|---|
| 1. Tyre degradation | `src/degradation/` | Models lap-time evolution vs tyre age, per compound and per circuit |
| 2. Safety-car risk | `src/safety_car/` | Models SC/VSC deployment probability per circuit from historical `TrackStatus` data, with explicit uncertainty |
| 3. Strategy simulator | `src/simulator/` | Monte Carlo simulation combining layers 1–2 to recommend a pit window at a given race state, with a full outcome distribution |
| 4. Decision audit | `src/audit/` | Replays real race decision points through the simulator and compares against what actually happened |

### Modelling extensions

Built on top of the four core layers, each with tests and an honest write-up in
[`reports/f1/`](reports/f1/):

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

### Data scope (MVP)

**Seasons: 2023, 2024, 2025** — the three most recent completed seasons, all
inside the 2022–2025 ground-effect regulation era, so car and tyre behaviour
is broadly comparable across the dataset. (2022 is deliberately excluded from
the MVP: early ground-effect cars suffered porpoising issues that add noise
to degradation modelling; it can be added later as a robustness check.)

**Circuits (4), chosen to contrast the two risk dimensions the system models:**

| Circuit | Grand Prix | Why it is in the set |
|---|---|---|
| Monaco | Monaco GP | Street circuit, historically among the highest SC rates, near-zero overtaking — strategy is almost purely track-position driven |
| Marina Bay | Singapore GP | Street circuit with a near-100% historical SC rate — the strongest test for the SC-probability layer |
| Barcelona-Catalunya | Spanish GP | Permanent circuit, historically low SC rate, high front-tyre stress — a clean laboratory for the degradation layer |
| Suzuka | Japanese GP | Permanent high-load circuit, low SC rate, strong tyre energy — contrasts with Barcelona on degradation character |

This gives a 2×2-ish contrast: high-SC/low-degradation-signal street tracks
vs low-SC/high-degradation permanent tracks, which is exactly the trade-off
the Monte Carlo simulator has to arbitrate.

**Verified availability.** The table in
[`reports/f1/data_availability_phase0.md`](reports/f1/data_availability_phase0.md)
is generated by [`scripts/check_data_availability.py`](scripts/check_data_availability.py)
from real FastF1 session loads (laps, track status, weather) for all 12
circuit-season combinations — the selection above was only frozen after that
check passed. Known caveats found during verification are listed in that
report and re-stated in the Limitations section of the methodology report.

### F1 phase plan & Definition of Done

Each phase stops for explicit validation before the next one starts.

| Phase | Deliverable | Definition of Done |
|---|---|---|
| 0. Setup & scoping | Repo, environment, verified data scope | Repo initialised; all 12 candidate sessions load through FastF1 with laps + `TrackStatus` + weather confirmed present; plan validated |
| 1. Ingestion pipeline | `src/ingestion/` + tests + data quality report | One clean, documented DataFrame per circuit-season; in/out laps and inaccurate laps handled; tests pass; report states % of laps excluded and why |
| 2. Tyre degradation model | `src/degradation/` + tests + figures | Per-compound/per-circuit fits with honest metrics (R², error) from cross-validation that never mixes laps of one race across train/test; limitations documented (e.g. fuel effect not isolated) |
| 3. SC/VSC probability model | `src/safety_car/` + tests | Per-circuit deployment probabilities **with confidence intervals**; explicit discussion of small-sample reliability |
| 4. Monte Carlo simulator | `src/simulator/` + tests | Given (circuit, current lap, compound, tyre age, gaps), produces a pit-window recommendation as an outcome distribution; seeded and reproducible; invariant tests pass (window inside race bounds, probabilities sum to 1, etc.) |
| 5. Retrospective audit | `reports/f1/audit_cases.md` | 4–6 real race moments (validated with Mohammed) replayed through the simulator; model vs real decision compared quantitatively; disagreements analysed honestly |
| 6. Methodology report | `reports/methodology.md` | Mini-paper (abstract, motivation/related work, method, results, limitations, future work); every number traceable to project output; no invented citations |
| 7. Packaging | Final README, clean-clone check | Everything runs from a fresh clone; 2–3 concrete FastF1-community contribution ideas proposed; short factual activity description drafted |

### F1 known limitations (stated up front)

- **Sample size for SC probability is structurally small** (one race per
  circuit per season, ~3 usable races per circuit in the MVP window plus
  historical extensions where data quality allows). The SC model will report
  wide intervals; that is a feature, not a bug.
- **Fuel load and tyre age are confounded** within a stint; without private
  telemetry the fuel effect can only be partially controlled (e.g. by
  modelling a linear fuel correction). This is quantified and discussed
  in the Phase 2 report rather than hidden.
- **Track evolution, traffic and driver-specific pace** are not explicitly
  modelled in the MVP; they are absorbed into residual noise.

---

## WEC

FastF1 covers only Formula 1, so the World Endurance Championship needed a new
ingestion path and its own models, brought to the same depth as F1's: verified
data availability, a fitted and cross-validated degradation model, a Bayesian
neutralisation model, and a Monte Carlo simulator.

### Data scope

**4 HYPERCAR races, 2024 season**, spanning short and long formats and three
continents:

| Circuit | Race | Why it is in the set |
|---|---|---|
| Spa | 6h | European high-speed circuit; the reference case for the whole build |
| Fuji | 6h | Contrasts Spa on layout and climate |
| Bahrain | 8h | The longest of the four scoped formats |
| Imola | 6h | Surfaces the pit-loss and degradation anomalies discussed below |

**Le Mans 2024 was deliberately rejected**: the source holds only 43
HYPERCAR laps for it (a 24h race runs 300+) — the event is incomplete
upstream. Picking it because it is the famous race would have poisoned every
model built on it, the same Phase 0 discipline that shapes the F1 scope.

All 33 available HYPERCAR-class WEC races (2021-2026) were used for the
neutralisation model, which needs the largest sample it can get; the 4 above
were selected for degradation/simulator work.

**Verified availability, and what the verification caught:** see
[`reports/wec/data_availability_phase0.md`](reports/wec/data_availability_phase0.md).
It documents the source (one DuckDB view covering IMSA, WEC, ELMS and ALMS —
so the plan's separate Al Kamel API was unverified and unnecessary), and the
two traps caught before any model was built: the source mixes
practice/qualifying/warmup with race laps, and `stint_number` is the
**driver** stint, not the tyre stint.

### System overview

| Layer | Module | Key finding |
|---|---|---|
| 0. Data | `src/data/` (shared with IMSA) | Normalised multi-series lap schema; `pit visit` / `tyre change` / `driver stint` kept as three separate signals |
| 1. Tyre degradation | `src/degradation/endurance.py` | Net slope significant and positive at 3 of 4 circuits (Spa +0.042, Fuji +0.014, Bahrain +0.051 s/lap); Imola anomalously negative (−0.044) |
| 2. Neutralisations | `src/safety_car/endurance.py` | WEC runs a genuine Safety Car distinct from FCY, and uses it **more** than FCY at every scoped circuit (Spa: P=0.79 SC vs P=0.50 FCY) |
| 3. Strategy simulator | `src/simulator/endurance.py` | Both neutralisation kinds sampled independently (mirrors F1's SC/VSC); at Spa the fuel tank, not tyre wear, decides the optimal stop lap |

Reports: [data availability](reports/wec/data_availability_phase0.md) ·
[degradation](reports/wec/degradation_phase1.md) ·
[neutralisations](reports/wec/safety_car_phase2.md) ·
[simulator](reports/wec/simulator_phase3.md)

### Key results

- **Degradation slopes do not transfer across circuits, and can flip sign.**
  Leave-one-race-out across the 4 scoped circuits gives a **negative** mean
  R² (−0.012): a slope pooled from three circuits predicts a fourth's
  within-stint pace evolution *worse* than a flat line, and for Bahrain and
  Imola the pooled and own slopes disagree in sign. This reproduces the F1
  project's central finding independently, and more starkly.
- **A fuel/degradation split was attempted and rejected on the evidence.**
  84-99% of pit visits also change tyres, leaving the fuel and tyre-age
  regressors correlated +0.95 to +1.00 after fixed effects at every circuit.
  Only the identified *net* slope is reported, behind a `separable` flag.
- **Fuel is a binding constraint, and F1 has no equivalent.** At Spa the tyres
  want a stop near lap 106; the tank runs dry at lap 90, and that boundary —
  not tyre wear — decides the strategy (pinned by a regression test).
- **Pit loss varies by circuit as much as it does in F1.** Imola's 26.8s is a
  third of Spa/Fuji/Bahrain's 63-81s — the WEC analogue of the F1 project's
  own Monaco-vs-Singapore (19.1s vs 27.3s) pit-loss contrast.

### WEC phase plan & Definition of Done

| Phase | Deliverable | Definition of Done |
|---|---|---|
| 0. Data availability | [`reports/wec/data_availability_phase0.md`](reports/wec/data_availability_phase0.md) | Source verified by direct query, not assumed; scope frozen (4 circuits, 2024); both verification traps documented and regression-tested |
| 1. Degradation | [`reports/wec/degradation_phase1.md`](reports/wec/degradation_phase1.md) + `src/degradation/endurance_validation.py` + tests | Net slope fitted per circuit with CIs; leave-one-race-out across all 4 circuits; separability diagnostic reported, never a fabricated fuel/degradation split |
| 2. Neutralisations | [`reports/wec/safety_car_phase2.md`](reports/wec/safety_car_phase2.md) + tests | Per-circuit AND series-wide Beta-Binomial/Gamma-Poisson posteriors with Jeffreys priors, on 33 races; SC vs FCY distinguished empirically |
| 3. Simulator | [`reports/wec/simulator_phase3.md`](reports/wec/simulator_phase3.md) + tests | Both neutralisation kinds modelled; fuel-range constraint enforced; demo scenario per circuit; reproducible and seeded |

### WEC known limitations (stated up front)

- **Per-race, not per-season**, for degradation and the simulator: each
  circuit's model is fitted on one 2024 race. The LORO result above is
  cross-*circuit*; cross-season stability has not yet been tested.
- **No tyre compound in the source** — degradation is a single net slope, not
  a per-compound polynomial as in F1.
- **SC and FCY are modelled independently**, though an FCY can in reality
  escalate into an SC — the same caveat F1 states for its own SC/VSC pair.
- **No rivals, no track position, no driver-stint regulatory constraints**
  (WEC mandates 3 drivers minimum) in the simulator.
- Imola's anomalous negative degradation slope and its wider RMSE are
  reported as measured, not smoothed away.

---

## IMSA

FastF1 covers only Formula 1, so the IMSA WeatherTech SportsCar Championship
needed a new ingestion path and its own models, brought to the same depth as
F1's and WEC's: verified data availability, a fitted and cross-validated
degradation model, a Bayesian neutralisation model, and a Monte Carlo
simulator. IMSA shares its loader and model modules with WEC
(`src/data/endurance_loader.py`, `src/degradation/endurance.py`,
`src/safety_car/endurance.py`, `src/simulator/endurance.py`) — the same
pit-visit / tyre-change / driver-stint distinction applies to both series —
but every number below is fitted on IMSA's own data, never pooled with WEC's.

### Data scope

**4 GTP races, 2023 season**, chosen to span sprint- and endurance-length
formats and a spread of circuit types:

| Circuit | Race length | Why it is in the set |
|---|---|---|
| Watkins Glen | 364 min | Mid-length road course; the reference case for the whole build |
| Sebring | 723 min (12h) | The longest of the four scoped formats |
| Mosport | 162 min | Short sprint format |
| Road America | 163 min | Short sprint format; surfaces the degradation anomaly discussed below |

96 GTP-class races are available across IMSA 2021-2026 in total; all were used
for the neutralisation model, which needs the largest sample it can get. The 4
above were selected for degradation/simulator work.

**Verified availability, and what the verification caught:** see
[`reports/imsa/data_availability_phase0.md`](reports/imsa/data_availability_phase0.md).
It documents the source (shared with WEC — one DuckDB view covering IMSA, WEC,
ELMS and ALMS), the two traps caught before any model was built (mixed
practice/race sessions; `stint_number` is the **driver** stint, not the tyre
stint — the #01 GTP car made 13 pit visits across only 4 driver stints), and a
coverage gap found and *corrected after seeing more races*: an early version of
this report claimed IMSA "ships no weather" as a series-wide fact from a single
race; with four races materialised, two circuits have full weather coverage
and two have none — a measured, race-specific fact, not a series-wide one.

### System overview

| Layer | Module | Key finding |
|---|---|---|
| 0. Data | `src/data/` (shared with WEC) | Normalised multi-series lap schema; `pit visit` / `tyre change` / `driver stint` kept as three separate signals |
| 1. Tyre degradation | `src/degradation/endurance.py` | Net slope covers zero at 3 of 4 circuits (fuel gain cancels tyre loss); Road America is significantly negative (−0.036) |
| 2. Neutralisations | `src/safety_car/endurance.py` | Full Course Yellow in 90-93% of races at every scoped circuit; **zero** Safety Car events in 63 races — a genuinely different procedure from WEC's |
| 3. Strategy simulator | `src/simulator/endurance.py` | Recommendation confidence tracks the underlying degradation signal directly: decisive at Road America, honestly flat (1.3s spread) at Mosport |

Reports: [data availability](reports/imsa/data_availability_phase0.md) ·
[degradation](reports/imsa/degradation_phase1.md) ·
[neutralisations](reports/imsa/safety_car_phase2.md) ·
[simulator](reports/imsa/simulator_phase3.md)

### Key results

- **Degradation slopes do not transfer across circuits.** Leave-one-race-out
  across the 4 scoped circuits gives a mean within-stint R² of +0.002 — a
  slope pooled from three circuits predicts a fourth's pace evolution no
  better than a flat line. Independent confirmation, in a second series, of
  the F1 project's central finding.
- **A fuel/degradation split was attempted and rejected on the evidence.**
  85-100% of pit visits also change tyres, leaving the fuel and tyre-age
  regressors correlated +0.98 to +1.00 after fixed effects at every circuit.
  Only the identified *net* slope is reported, behind a `separable` flag.
- **IMSA and WEC are not interchangeable.** An IMSA race is near-certain to
  see a Full Course Yellow (P = 0.96 series-wide, confirmed circuit-by-circuit
  at 90-93%); IMSA has never shown a Safety Car in 63 races, while WEC prefers
  the Safety Car over FCY at every one of its scoped circuits.
- **The simulator's confidence is honest, not uniform.** Road America — the
  one circuit with a statistically significant degradation slope — gives the
  most decisive recommendation of the four; Mosport, whose slope covers zero,
  spreads only 1.3s across all candidate pit laps.

### IMSA phase plan & Definition of Done

| Phase | Deliverable | Definition of Done |
|---|---|---|
| 0. Data availability | [`reports/imsa/data_availability_phase0.md`](reports/imsa/data_availability_phase0.md) | Source verified by direct query, not assumed; scope frozen (4 circuits, 2023); both verification traps documented and regression-tested |
| 1. Degradation | [`reports/imsa/degradation_phase1.md`](reports/imsa/degradation_phase1.md) + `src/degradation/endurance_validation.py` + tests | Net slope fitted per circuit with CIs; leave-one-race-out across all 4 circuits; separability diagnostic reported, never a fabricated fuel/degradation split |
| 2. Neutralisations | [`reports/imsa/safety_car_phase2.md`](reports/imsa/safety_car_phase2.md) + tests | Per-circuit AND series-wide Beta-Binomial/Gamma-Poisson posteriors with Jeffreys priors, on 63 races; the zero-Safety-Car case handled by the Jeffreys prior, not hard-coded |
| 3. Simulator | [`reports/imsa/simulator_phase3.md`](reports/imsa/simulator_phase3.md) + tests | Fuel-range constraint enforced; demo scenario per circuit; reproducible and seeded |

### IMSA known limitations (stated up front)

- **Per-race, not per-season**, for degradation and the simulator: each
  circuit's model is fitted on one 2023 race. The LORO result above is
  cross-*circuit*; cross-season stability has not yet been tested.
- **No tyre compound in the source** — degradation is a single net slope, not
  a per-compound polynomial as in F1.
- **No rivals, no track position, no driver-stint regulatory constraints** in
  the simulator; IMSA is heavily multi-class (GTP/GTD/GTDPRO/LMP2/LMP3), which
  a two-car rival abstraction would not represent honestly.
- Road America's anomalous negative degradation slope is reported as
  measured, not smoothed away — a genuine open question for future work.

---

## Engineering rules (all three series)

- **No fabricated data.** If a source does not provide something, it is
  documented as unavailable, never estimated silently.
- **No data leakage.** The decision models only use information that was
  knowable at the simulated moment of the race. Race outcomes never leak into
  features.
- **Uncertainty is first-class.** Every probability and every recommendation
  ships with an interval or a distribution, never a bare point estimate.
- **Reproducibility.** Fixed seeds for all stochastic code (Monte Carlo),
  pinned dependency versions (`requirements.lock`), FastF1 cache enabled for
  F1; WEC/IMSA races are committed as derived CSVs so their tests run offline.
- **Tested.** `pytest` covers ingestion parsing/cleaning, degradation model
  non-regression, and simulator physical-consistency invariants — for all
  three series.
- **Typed and documented.** Docstrings and type hints everywhere in `src/`.
- **Nothing is pooled across series.** F1, WEC and IMSA each get their own
  fitted coefficients, posteriors and simulator constants; only the estimator
  *code* (and, for WEC/IMSA, the data schema) is shared.

## Repository structure

```
motorsport-strategy-lab/
  data/
    cache/              # FastF1 cache (gitignored)
    derived/
      f1/               # F1 derived laps, track status, sessions, model coefficients
      imsa/             # IMSA derived laps (4 committed races)
      wec/              # WEC derived laps (4 committed races)
      endurance/         # cross-series neutralisation flags (96 races, both series)
  src/
    ingestion/          # FastF1 loading, cleaning, validation (F1 only)
    data/               # multi-series loader interface + IMSA/WEC loader (shared)
    degradation/        # model.py (F1, OLS + LORO CV), gp_model.py, kalman.py;
                        #   endurance.py + endurance_validation.py (WEC/IMSA, shared)
    safety_car/         # model.py (F1 SC/VSC); endurance.py (WEC FCY+SC, IMSA FCY)
    simulator/          # engine.py (F1, vectorised + optional Sobol QMC),
                        #   recommend.py (Pareto front); endurance.py (WEC/IMSA)
    audit/              # F1 retrospective audit scripts
  notebooks/            # exploration only — never the source of truth
  scripts/              # run_ingestion.py, run_degradation.py, run_safety_car.py,
                        #   run_simulator_demo.py (F1); run_endurance_flags.py
                        #   (WEC/IMSA neutralisation data pull); demo_extensions.py
  tests/                # pytest: all three series, ~130 tests
  reports/
    f1/                 # phase 0-4 reports, audit cases, figures
    imsa/               # phase 0-3 reports
    wec/                # phase 0-3 reports
    methodology.md      # F1 mini-paper
  README.md
  pyproject.toml
  requirements.txt      # top-level deps; requirements.lock pins exact versions
```

## Setup

```bash
git clone <repo-url>
cd motorsport-strategy-lab
python -m venv .venv
.venv/Scripts/activate          # Windows; use .venv/bin/activate on Unix
pip install -r requirements.txt # or requirements.lock for exact pins
python scripts/check_data_availability.py   # populates the FastF1 cache (F1 only)
pytest
```

The first F1 data run downloads several hundred MB into `data/cache/`
(gitignored) and is served from cache afterwards. WEC and IMSA races are
already committed as derived CSVs (`data/derived/wec/`, `data/derived/imsa/`),
so their tests run fully offline with no extra setup; `scripts/run_endurance_flags.py`
re-pulls the neutralisation dataset only if you want to refresh it.

## License & attribution

F1 data accessed through [FastF1](https://github.com/theOehrly/Fast-F1), which
sources official F1 live timing; this project is unaffiliated with Formula 1.
WEC/IMSA data accessed through a community-maintained DuckDB
(`hf://datasets/tobil/imsa/imsa.duckdb`); this project is unaffiliated with
IMSA or the FIA World Endurance Championship. Code license to be chosen before
public release (MIT planned).
