"""End-to-end demo of the modelling extensions on real artifacts.

Exercises, on committed derived data (no network):

1. Vectorised Monte Carlo with optional Sobol' QMC sampling.
2. Multi-objective Pareto front over candidate pit laps (time vs position).
3. GP degradation curve vs OLS on leave-one-race-out CV (one circuit).
4. Online Kalman degradation tracking on one real stint.

Usage (from the repo root)::

    python scripts/demo_extensions.py

Prints a concise human-readable summary; writes nothing.
"""

from __future__ import annotations

import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.degradation.dataset import build_modelling_frame  # noqa: E402
from src.degradation.gp_model import fit_circuit_gp, predict_shape_gp  # noqa: E402
from src.degradation.kalman import filter_stint  # noqa: E402
from src.degradation.model import fit_circuit, predict_shape  # noqa: E402
from src.simulator.artifacts import load_circuit_models  # noqa: E402
from src.simulator.engine import RivalSpec, Scenario, simulate  # noqa: E402
from src.simulator.recommend import pareto_front, summarise  # noqa: E402

RACE_LAPS = {"monaco": 78, "singapore": 62, "barcelona": 66, "suzuka": 53}


def _scenario(circuit: str, total_laps: int) -> Scenario:
    current = total_laps // 3
    return Scenario(
        circuit=circuit, current_lap=current, total_laps=total_laps,
        compound="MEDIUM", tyre_age=current, target_compound="HARD",
        rivals=(
            RivalSpec("car_ahead", 2.5, "MEDIUM", current, current + 8, "HARD"),
            RivalSpec("car_behind", -3.0, "MEDIUM", current, current + 5, "HARD"),
        ),
    )


def demo_monte_carlo(circuit: str = "barcelona", n_draws: int = 4000) -> list[str]:
    model = load_circuit_models()[circuit]
    scenario = _scenario(circuit, RACE_LAPS[circuit])
    mc = simulate(scenario, model, n_draws=n_draws, seed=20260712, sampler="mc")
    qmc = simulate(scenario, model, n_draws=n_draws, seed=20260712, sampler="qmc")
    return [
        f"[1] Monte Carlo ({circuit}, {n_draws} draws)",
        f"    MC  best lap {summarise(scenario, mc).best_lap}, "
        f"P(best)={mc.p_best.max():.3f}",
        f"    QMC best lap {summarise(scenario, qmc).best_lap}, "
        f"P(best)={qmc.p_best.max():.3f}  (Sobol' subspace; unbiased)",
    ]


def demo_pareto(circuit: str = "barcelona", n_draws: int = 4000) -> list[str]:
    model = load_circuit_models()[circuit]
    scenario = _scenario(circuit, RACE_LAPS[circuit])
    rec = summarise(scenario, simulate(scenario, model, n_draws=n_draws, seed=11))
    front = pareto_front(rec, {"mean_s": "min", "p_ahead_car_ahead": "max"})
    laps = ", ".join(str(int(l)) for l in front["pit_lap"])
    return [
        f"[2] Pareto front - time vs position ({circuit})",
        f"    fastest-time lap : {int(rec.table.loc[rec.table['mean_s'].idxmin(), 'pit_lap'])}",
        f"    non-dominated laps: [{laps}]  ({len(front)} of {len(rec.table)})",
    ]


def _circuit_frame(circuit: str) -> pd.DataFrame:
    files = sorted(glob.glob(f"data/derived/laps_*_{circuit}.csv"))
    raw = pd.concat(
        [pd.read_csv(f).assign(race=f.split("laps_")[1].split("_")[0] + f"_{circuit}")
         for f in files],
        ignore_index=True,
    )
    frame, _ = build_modelling_frame(raw, circuit)
    return frame


def demo_gp_vs_ols(circuit: str = "suzuka") -> list[str]:
    frame = _circuit_frame(circuit)

    def demean(v: pd.Series, s: pd.Series) -> pd.Series:
        return v - v.groupby(s).transform("mean")

    ols_rmse, gp_rmse = [], []
    for test_race in sorted(frame["race"].unique()):
        tr, te = frame[frame["race"] != test_race], frame[frame["race"] == test_race]
        for store, sh in [
            (ols_rmse, predict_shape(fit_circuit(tr, circuit, degree=1), te)),
            (gp_rmse, predict_shape_gp(fit_circuit_gp(tr, circuit), te)),
        ]:
            v = sh.notna()
            err = demean(te.loc[v, "lap_time_s"], te.loc[v, "stint_id"]) - demean(sh[v], te.loc[v, "stint_id"])
            store.append(float(np.sqrt((err**2).mean())))
    return [
        f"[3] GP vs OLS degradation - leave-one-race-out ({circuit})",
        f"    OLS mean CV RMSE: {np.mean(ols_rmse):.3f} s/lap",
        f"    GP  mean CV RMSE: {np.mean(gp_rmse):.3f} s/lap  (per-circuit)",
        "    Across all 4 circuits the two tie out-of-sample (0.838 vs 0.844);",
        "    see reports/degradation_phase2.md.",
    ]


def demo_kalman(circuit: str = "suzuka") -> list[str]:
    df = pd.read_csv(sorted(glob.glob(f"data/derived/laps_2023_{circuit}.csv"))[0])
    df = df[df["is_pace_lap"]]
    groups = df.groupby(["Driver", "Stint"])
    key = max(groups.groups, key=lambda k: len(groups.get_group(k)))
    stint = groups.get_group(key).sort_values("TyreLife")
    lt = stint["lap_time_s"].to_numpy()
    states = filter_stint(lt - lt[0], meas_var=0.64**2, slope_process_var=1e-5)
    ols = float(np.polyfit(stint["TyreLife"].to_numpy(float), lt, 1)[0])
    return [
        f"[4] Online Kalman degradation - {key[0]} stint {int(key[1])} ({circuit}, {len(stint)} laps)",
        f"    slope after  5 laps: {states[4].slope:+.3f} +/- {states[4].slope_sd:.3f} s/lap",
        f"    slope final        : {states[-1].slope:+.3f} +/- {states[-1].slope_sd:.3f} s/lap",
        f"    whole-stint OLS    : {ols:+.3f} s/lap  (online estimate converges to it)",
    ]


def main() -> int:
    blocks = [
        demo_monte_carlo(),
        demo_pareto(),
        demo_gp_vs_ols(),
        demo_kalman(),
    ]
    print("Modelling-extensions demo (real artifacts, offline)\n")
    for block in blocks:
        print("\n".join(block))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
