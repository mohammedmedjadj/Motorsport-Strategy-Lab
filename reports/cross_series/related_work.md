# Related work

Twelve papers, each checked against a real publication record rather than
against memory — Crossref for the journal articles, the arXiv API for the
preprints. Author lists, venues, volumes and DOIs below are what those records
return.

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
race it has not seen. Cappello and Hoegh come closest and say so explicitly:
their evaluation is one race, and generalisation is named as future work with no
empirical evidence offered.

The second is **comparison against what teams actually did**. Optimisers are
compared to other optimisers, to baselines the authors construct, or to the
optimum under the model's own assumptions. Bekker and Lotz compare to real 2005
races; Aguad and Thraves compare strategic against non-strategic agents inside
their own game. Nobody, as far as I have found, replays a large sample of real
pit-stop decisions and reports where the optimiser and the pit wall part company.

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
| 11 | **Cappello & Hoegh (2025)**, arXiv:2512.00640 | Bayesian state-space tyre degradation from FastF1: lap time as fuel mass plus a latent tyre-pace state, pit stops as resets, skewed-t observations. Statistically more careful per race than the fixed-effects model here. | **Their evaluation is one race — Hamilton at the 2025 Austrian Grand Prix — and they state that generalising across races or circuits is future work with no evidence offered. That sentence is this project's entire premise.** They also find compound-specific degradation differences not statistically distinct, which independently echoes the instability found here at scale. |
| 12 | **Santillana (2026)**, arXiv:2607.06495 | A calibrated real-time Monte Carlo engine feeding trilingual natural-language strategy briefings, calibrated on 126 races (2018–2024), validated on held-out seasons and deployed live at two Grands Prix. Operationally far ahead of anything here. | Multi-championship transfer, and the audit. A live-deployed engine is validated on whether its briefings are faithful to its own model state, which is a different question from whether the model's parameters generalise. |

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
closer than it does in three championships out of four, is not a result any of
these papers could produce, because none of them asks that question.

Both are cheap to state and neither requires the modelling to be sophisticated.
That is the point: the contribution is the validation, not the machinery.

## Not cited, and why

Earlier notes named a "Frontiers in Artificial Intelligence 2025" deep-learning
paper and a driver-versus-car paper attributed to Menon et al. Neither could be
confirmed against a publication record. They are not cited anywhere in this
project and should not be added without a verified DOI.
