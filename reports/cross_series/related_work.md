# Related work

Seventeen papers, each checked against a real publication record rather than
against memory — Crossref for the journal articles, the arXiv API for the
preprints, the Zenodo API for the one entry deposited there. Author lists,
venues, volumes and DOIs below are what those records return.

One of the seventeen has not been peer-reviewed by anyone, and its row says so.
It is included because it is directly relevant, not because it carries the same
weight as the rest.

The first version of this table had eleven of its twelve entries in Formula 1,
which is an odd shape for a review supporting a project whose whole claim is
that it works across four championships. Rows 13–16 are a second pass aimed at
endurance and GT, and the shape of what came back is itself a finding: endurance
strategy research is almost entirely about *electric* endurance racing, where
the binding constraint is charge rather than fuel, and one group at Eindhoven
accounts for most of it. GT racing has essentially one paper.

This matters more than it sounds. Earlier notes for this project carried five
candidate references presented as established fact, and only two of them
survived being looked up. A citation to a paper that does not exist as described
does more damage than a missing literature review, so anything that could not be
confirmed is simply absent from this table.

## What the field actually looks like

Race-strategy research is mostly about **building the optimiser**. Discrete-event
simulation, Monte Carlo, dynamic programming, mixed-integer programming,
reinforcement learning, game theory — the methods vary, the goal is consistent:
compute a better plan than the one a team would otherwise choose.

Two things are rare across all of it.

The first is **out-of-sample validation of the fitted parameters**. A tyre model
gets fitted, and its fit quality is reported on the data it was fitted to. Very
little of this literature asks whether a slope fitted on past races predicts a
race it has not seen. Cappello and Hoegh do ask it, and are the only ones who
do: their journal version holds out 19 race sessions of the 2025 season by
rolling-origin cross-validation. What separates that from this project is the
axis the held-out data varies along — one season, one driver, one championship,
held out forward in time, against whole seasons of a circuit-class held out
across four championships.

The second is **comparison against what teams actually did**. Optimisers are
compared to other optimisers, to baselines the authors construct, or to the
optimum under the model's own assumptions. Bekker and Lotz compare to real 2005
races; Aguad and Thraves compare strategic against non-strategic agents inside
their own game. Nobody, as far as I have found, replays a large sample of real
pit-stop decisions and reports where the optimiser and the pit wall part company.

One paper does offer an explanation for this project's own late-stop gap, and
it deserves stating before the table rather than after it. Salminen's
equilibrium stop is not the time-optimal one. A driver stops at the earliest lap
on which the opponent can no longer answer, which lands *before* the fastest
clean-air strategy, because waiting for the time optimum hands the opponent a
window. In his one worked example the equilibrium stop is lap 16 against a
time-optimal lap 20, on a 40-lap race: a fifth of the distance early. The
calendar-wide audit here finds the simulator stays out a median of 12 laps
longer than Formula 1 teams did, which on these race lengths is a comparable
fraction. The direction matches. That is all it is: one worked example is not a
distribution, the two quantities are not computed the same way, and the
comparison has not been run on the 357 decisions. What makes it hard to run is
covered in the row itself.

That is the gap this project sits in, and it is worth being precise about how
narrow it is. The modelling here is not more sophisticated than Heilmeier's or
Aguad's — in places it is deliberately simpler. What is different is that it is
applied identically across four championships and then confronted with 1,280
real decisions, and that two of its three results are negative.

## The table

| # | Work | What it does that this project does not | What this project does that it does not |
|---|---|---|---|
| 1 | **Bekker & Lotz (2009)**, *Journal of the Operational Research Society* 60(7):952–961. [10.1057/palgrave.jors.2602626](https://doi.org/10.1057/palgrave.jors.2602626) | Discrete-event simulation of a full race with overtaking, traffic and refuelling under the rules of the era. Validated against real 2005 races. The earliest serious OR treatment of F1 strategy. | Four championships instead of one, out-of-sample transfer measured, and a decision audit at scale. Their refuelling assumptions no longer hold in F1. |
| 2 | **Heilmeier, Graf & Lienkamp (2018)**, *IEEE ITSC*, 2986–2993. [10.1109/ITSC.2018.8570012](https://doi.org/10.1109/ITSC.2018.8570012) | The lap-time model this whole line of work rests on: fuel mass, tyre degradation and driver effects combined into a race simulation, with open code (TUMFTM/race-simulation). | Cluster-robust intervals on every coefficient, leave-one-race-out transfer, and endurance series with a hard fuel constraint. |
| 3 | **Heilmeier, Graf, Betz & Lienkamp (2020)**, *Applied Sciences* 10(12):4229. [10.3390/app10124229](https://doi.org/10.3390/app10124229) | Probabilistic race simulation done properly — accidents, safety cars, lap-time variability, all sampled. Richer than this project's engine on driver interaction and overtaking. | Their neutralisation probabilities are modelled; here they are fitted per circuit from measured deployments with credible intervals, and the three endurance regimes are kept separate rather than pooled. |
| 4 | **Heilmeier, Thomaser, Graf & Betz (2020)**, *Applied Sciences* 10(21):7805. [10.3390/app10217805](https://doi.org/10.3390/app10217805) | Trains neural networks on simulation output to make strategy calls in real time — a virtual strategy engineer. Answers a question this project does not ask. | This project stays interpretable on purpose, because the object of study is whether the *inputs* transfer. A network trained on simulation output inherits whatever the simulation assumed. |
| 5 | **Carrasco Heine & Thraves (2022)**, *Central European Journal of Operations Research* 31(1):239–268. [10.1007/s10100-022-00806-4](https://doi.org/10.1007/s10100-022-00806-4) | Exact dynamic program for stop laps and compound choice, extended to a stochastic version with yellow flags and rain. The cleanest formulation of the deterministic problem. | The same DP idea applied under an endurance fuel cap across 205 race-seasons, plus the finding that its recommendations sit further from practice than a fixed-interval rule. |
| 6 | **van Kampen, Herrmann & Salazar (2022)**, *European Journal of Control* 68:100679. [10.1016/j.ejcon.2022.100679](https://doi.org/10.1016/j.ejcon.2022.100679) | Bi-level mixed-integer convex optimisation for electric endurance racing: stint lengths, charge times and powertrain operation jointly, under thermal limits. Far deeper on energy than anything here. | Combustion endurance with measured tyre degradation and real pit losses, on committed timing from 205 real race-seasons rather than a vehicle model. |
| 7 | **Aguad & Thraves (2024)**, *European Journal of Operational Research* 319(3):908–919. [10.1016/j.ejor.2024.07.011](https://doi.org/10.1016/j.ejor.2024.07.011) | Zero-sum feedback Stackelberg game between two drivers, solved by DP, with three compounds and stochastic yellow flags. Reports that a strategic agent gains over 15% in winning odds. | The adversarial component here reuses this framing and then tests it: modelling the cover moves the recommendation *away* from what teams did, which their setting has no occasion to check. |
| 8 | **Todd, Jiang, Russo, Winkler, Sale, McMillan & Rago (2025)**, arXiv:2501.04067 | Deep learning and XGBoost on Mercedes-AMG PETRONAS team telemetry to forecast tyre energy, with feature-importance and counterfactual explanations. Uses data no public project can obtain. | Public timing only, which is a limitation on accuracy and an advantage on reproducibility — anybody can rerun this. And transfer across seasons, which telemetry-fitted models are not tested on here. |
| 9 | **Thomas, Jiang, Kori, Russo, Winkler, Sale, McMillan, Belardinelli & Rago (2025)**, arXiv:2501.04068 | Reinforcement learning over compound choice and stop timing, with explainability, tested on the 2023 Bahrain Grand Prix and extendable to multiple tracks. | Learns nothing; fits and measures. The RL agent optimises inside a simulator, so its quality is bounded by parameters whose stability nobody has measured — which is exactly what this project measures. |
| 10 | **Fieni, Wüthrich, Neumann, Moradi & Onder (2025)**, arXiv:2512.21570 | Mixed-integer program and an RL agent that jointly optimise energy deployment, tyre wear and pit timing, benchmarked against the optimum. Handles energy management this project ignores entirely. | Cross-championship scope and a confrontation with real decisions. Their benchmark is the optimal solution under their model; this one's benchmark is what happened. |
| 11 | **Cappello & Hoegh (2026)**, *Journal of Sports Analytics* 12. [10.1177/22150218261446170](https://doi.org/10.1177/22150218261446170) (preprint arXiv:2512.00640) | Bayesian state-space tyre degradation from FastF1: lap time as fuel mass plus a latent tyre-pace state, pit stops as resets, skewed-t observations. Statistically more careful per race than the fixed-effects model here, and **the only paper in this table that validates its tyre model out of sample** — 19 race sessions of the 2025 season, rolling-origin cross-validation, against an AR(1) benchmark. | The axis the held-out data varies along. Their 19 sessions are one season, one driver and one championship, held out forward in time; this project holds out a whole season of a circuit-class and asks whether a slope fitted on its other seasons predicts it, across 51 circuit-classes and four championships. Both are out-of-sample. Only one changes season, circuit and class. They also find compound-specific degradation differences not statistically distinct, which independently echoes the instability found here at scale. |
| 12 | **Santillana (2026)**, arXiv:2607.06495 | A calibrated real-time Monte Carlo engine feeding trilingual natural-language strategy briefings, calibrated on 126 races (2018–2024), validated on held-out seasons and deployed live at two Grands Prix. Operationally far ahead of anything here. | Multi-championship transfer, and the audit. A live-deployed engine is validated on whether its briefings are faithful to its own model state, which is a different question from whether the model's parameters generalise. |

| 13 | **Boettinger & Klotz (2023)**, arXiv:2306.16088 | The only study in this table on **GT racing rather than single-seaters**: a Nordschleife race simulation wrapped in an OpenAI Gym environment, with an RL agent learning stop timing from fuel mass and race position, validated on 2020 Nürburgring Langstrecken Serie data. | Transfer, and real decisions. Their policy is learned and evaluated inside their own simulator; nothing measures whether its inputs hold on a season it never saw. |
| 14 | **van Kampen, Moriggi, Braghin & Salazar (2024)**, arXiv:2403.06885 | Model predictive control for electric endurance cars that prices a competitor's likely response probabilistically, over pit stops, charge duration and driving tactics. A 21 s gain over a fixed-overtake tactic in a simulated one-hour race at Zandvoort. | The same gap as the rest of this group: a control law validated in simulation, not a fitted parameter validated on a held-out season, and no confrontation with real decisions. |
| 15 | **de Vries, van den Eshof, van Kampen & Salazar (2026)**, arXiv:2603.28286, accepted at IEEE ITSC 2026 | The closest existing work to this project's adversarial component, and it is endurance rather than F1: a bi-level framework pairing a multi-agent game-theoretic optimal control problem per lap with RL agents allocating energy and scheduling stops over a 45-lap race. Finds that exploiting aerodynamic interaction decides the race, and that position-seeking strategies differ fundamentally from minimum-time ones. | Real races. Their two agents are simulated; this project's rivals are the plans teams actually ran. Their finding that competitive play departs from the single-car optimum is, however, the nearest published thing to this project's own late-stop gap. |
| 16 | **Fieni, Wüthrich, Neumann & Onder (2026)**, arXiv:2602.23056 | Extends row 10 to multi-agent self-play: an interaction module on top of a pre-trained single-agent policy, with agents ranked on relative performance and adapting pit timing, tyre choice and energy allocation to opponents. | Cross-championship scope and the audit. Self-play produces agents that beat each other; it does not say whether the tyre model underneath transfers to a season it was not fitted on. |
| 17 | **Salminen (2026)**, *Game-Theoretic Framework for Pit Stop Strategy Optimisation in Circuit Auto Racing*. Zenodo preprint, deposited 11 July 2026, CC BY 4.0. [10.5281/zenodo.21306419](https://doi.org/10.5281/zenodo.21306419). **Single author, not peer-reviewed, not submitted to a venue that the record names.** | Solves the two-car one-stop game analytically instead of numerically, and gets further on *why* a strategy wins than any simulation does. Defines the earliest undefendable undercut — the first lap on which an opponent has neither a position-keeping defence nor a tyre-advantage one — and proves it is a subgame-perfect Nash equilibrium of that model. It positions itself explicitly against row 7, which it names as the only prior exact game-theoretic solution. | Measured parameters. Every quantity in that model is a free parameter there and a fitted one here, except the overtaking threshold in seconds, which this project does not hold in any form. Its predictions are also untested against a real race: the paper carries one worked numeric example and no data. Its overcut defence turns on dividing by the degradation rate, and at the rates measured here it is unreachable on 16 of 73 Formula 1 circuit-compounds — measured in [`../f1/overcut_feasibility.md`](../f1/overcut_feasibility.md). |

## Where this leaves the positioning

The README used to compare this project to "public notebooks". That was wrong
twice over: it understated the field, which contains a decade of serious OR and
control work, and it overstated this project, which is simpler in its modelling
than most of the papers above.

The honest positioning is narrower and easier to defend. This work adds two
things the literature does not currently have:

**Cross-championship measurement of whether the fitted parameters transfer.**
Everything above fits a degradation model. Only one of them evaluates on data
it did not fit, and on one race. Fifty-one circuit-classes measured under one
leave-one-race-out protocol is new, and the answer — that transfer is rare and
tracks the circuit-class rather than the championship — is one nobody has been
in a position to give.

**A retrospective audit against real decisions at scale.** 1,280 replayed first
stops, four championships, one criterion. The finding that an exact optimiser
sits systematically later than the pit wall, and that three rules of thumb sit
closer than it does in 5 of the 7 classes, is not a result any of
these papers could produce, because none of them asks that question.

Both are cheap to state and neither requires the modelling to be sophisticated.
That is the point: the contribution is the validation, not the machinery.

## Left out

Earlier notes named a "Frontiers in Artificial Intelligence 2025" deep-learning
paper and a driver-versus-car paper attributed to Menon et al. Neither could be
confirmed against a publication record. They are not cited anywhere in this
project and should not be added without a verified DOI.
