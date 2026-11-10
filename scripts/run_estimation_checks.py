"""Three checks on how the Formula 1 slopes are estimated and used.

1. **Clustering by race.** The published intervals cluster on the driver-race.
   Drivers in one race share the track's evolution, the weather and the
   allocation, so their residuals may be correlated across drivers, which
   driver-race clusters do not allow for. Clustering on the race instead allows
   for it, at the price of very few clusters (three or four seasons per
   circuit, referred to t with G-1 degrees of freedom). Both are reported: how
   many published slopes still exclude zero when the race is the cluster.
2. **Fuel load times tyre age.** The model has fuel and tyre age as additive
   terms. If a heavier car wears its tyres faster, the old tyre (run on more
   fuel) degrades faster than the new one at the same age, which is what the
   implied slope ratio of Result 3 says teams act as if. Each linear circuit is
   refitted with one extra term, tyre age times lap number, and the closed-form
   planner of Result 3 is rerun with it: if the interaction explains the
   one-stop residual, the planner's gap to the real stop shrinks.
3. **Refuelling time in the stop cost.** An endurance stop's measured loss
   includes refuelling, and the total fuel put in over a race does not depend on
   how many stops it is split across, so the cost of one more stop is the loss
   less its refuelling share. The refuelling time per lap of fuel is estimated
   per class from the stops themselves (loss on the laps run since the last
   stop, with race fixed effects and controls for driver and tyre changes), and
   the multi-stop optimum of Result 2 is recomputed with the marginal cost.

Writes ``data/derived/f1/estimation_checks_summary.json`` and
``reports/f1/estimation_checks.md``.

    python scripts/run_estimation_checks.py
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.degradation.dataset import build_modelling_frame, circuits_with_laps, load_circuit_laps  # noqa: E402
from src.degradation.model import _design_matrix  # noqa: E402
from src.degradation.robust import cluster_robust_se  # noqa: E402
from src.ingestion.config import DERIVED_DIR, F1_DERIVED_DIR, PRE_ERA_SEASONS, REPORTS_DIR  # noqa: E402
from src.simulator.multistop import optimal_stop_plan  # noqa: E402

COEFS = F1_DERIVED_DIR / "degradation_coefficients.csv"
DECISIONS = F1_DERIVED_DIR / "audit_design_checks.csv"
STOPS = DERIVED_DIR / "cross_series" / "pit_loss_stop_events.csv"
PLANS = DERIVED_DIR / "endurance" / "multistop_plans.csv"
OUT_JSON = F1_DERIVED_DIR / "estimation_checks_summary.json"
OUT_MD = REPORTS_DIR / "f1" / "estimation_checks.md"


def _ols(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return beta


def race_clustering() -> dict:
    degrees = pd.read_csv(COEFS).groupby("circuit")["degree"].first()
    n = zero_dr = zero_race = 0
    for circuit in circuits_with_laps(seasons=PRE_ERA_SEASONS):
        if circuit not in degrees.index:
            continue
        frame, _ = build_modelling_frame(load_circuit_laps(circuit, seasons=PRE_ERA_SEASONS), circuit)
        compounds = tuple(sorted(frame["Compound"].unique()))
        X, names = _design_matrix(frame, compounds, int(degrees[circuit]))
        y = frame["lap_time_s"].to_numpy(dtype=float)
        beta = _ols(X, y)
        se_dr, g_dr = cluster_robust_se(X, y, beta, frame["driver_race"].to_numpy())
        se_r, g_r = cluster_robust_se(X, y, beta, frame["race"].to_numpy())
        t_dr, t_r = stats.t.ppf(0.975, g_dr - 1), stats.t.ppf(0.975, max(g_r - 1, 1))
        for j, name in enumerate(names):
            if name.startswith("deg::") and name.endswith("p1"):
                n += 1
                zero_dr += abs(beta[j]) <= t_dr * se_dr[j]
                zero_race += abs(beta[j]) <= t_r * se_r[j]
    return {"n_slopes": n, "zero_driver_race": int(zero_dr), "zero_race": int(zero_race)}


def interaction() -> dict:
    degrees = pd.read_csv(COEFS).groupby("circuit")["degree"].first()
    fits = {}
    gammas = []
    for circuit in circuits_with_laps(seasons=PRE_ERA_SEASONS):
        if circuit not in degrees.index or int(degrees[circuit]) != 1:
            continue
        frame, _ = build_modelling_frame(load_circuit_laps(circuit, seasons=PRE_ERA_SEASONS), circuit)
        compounds = tuple(sorted(frame["Compound"].unique()))
        X, names = _design_matrix(frame, compounds, 1)
        inter = (frame["TyreLife"] * frame["LapNumber"]).to_numpy(dtype=float)[:, None]
        X2 = np.hstack([X, inter])
        y = frame["lap_time_s"].to_numpy(dtype=float)
        beta = _ols(X2, y)
        se, g = cluster_robust_se(X2, y, beta, frame["driver_race"].to_numpy())
        gamma, gse = beta[-1], se[-1]
        gammas.append((gamma, abs(gamma) > stats.t.ppf(0.975, g - 1) * gse))
        # The baseline is the published model, refitted without the interaction:
        # the interaction model's own slopes with gamma set to zero are slopes at
        # lap zero, not the published ones.
        pooled = _ols(X, y)
        fits[circuit] = {
            "gamma": gamma,
            "beta": {n.split("::")[1]: beta[j] for j, n in enumerate(names) if n.startswith("deg::")},
            "pooled": {n.split("::")[1]: pooled[j] for j, n in enumerate(names) if n.startswith("deg::")},
        }
    dec = pd.read_csv(DECISIONS)
    dec = dec[(dec["lookback"] == 5) & dec["top"] & (dec["compound"] != dec["target"])]
    rows = []
    for r in dec.itertuples():
        f = fits.get(r.circuit)
        if f is None or r.compound not in f["beta"] or r.target not in f["beta"]:
            continue
        w = r.horizon - r.decision_lap
        if w < 4:
            continue

        def best(beta: dict, gamma: float) -> int:
            costs = []
            for k in range(1, w):
                laps1 = r.decision_lap + np.arange(1, k + 1)
                laps2 = r.decision_lap + np.arange(k + 1, w + 1)
                c1 = np.sum((beta[r.compound] + gamma * laps1) * (r.tyre_age + np.arange(1, k + 1)))
                c2 = np.sum((beta[r.target] + gamma * laps2) * np.arange(1, w - k + 1))
                costs.append(c1 + c2)
            return int(np.argmin(costs)) + 1

        real_k = r.real_pit_lap - r.decision_lap
        rows.append({"one_stop": r.n_stops == 1, "without": best(f["pooled"], 0.0) - real_k,
                     "with": best(f["beta"], f["gamma"]) - real_k})
    d = pd.DataFrame(rows)
    one = d[d["one_stop"]]
    g = np.array([x for x, _ in gammas])
    return {
        "n_circuits": len(gammas), "gamma_median": float(np.median(g)),
        "n_gamma_positive": int((g > 0).sum()), "n_gamma_significant": int(sum(s for _, s in gammas)),
        "n_decisions": int(len(d)),
        "gap_without": float(d["without"].median()), "gap_with": float(d["with"].median()),
        "one_n": int(len(one)),
        "one_gap_without": float(one["without"].median()), "one_gap_with": float(one["with"].median()),
    }


def refuelling() -> dict:
    e = pd.read_csv(STOPS)
    e["race"] = e["series"] + "_" + e["circuit"] + "_" + e["year"].astype(str) + "_" + e["car_class"]
    per_lap = {}
    for (series, car_class), g in e.groupby(["series", "car_class"]):
        g = g[g["loss_s"] < g["loss_s"].quantile(0.98)]
        X = pd.DataFrame({"laps": g["stint_laps"].astype(float), "dc": g["driver_change"].astype(float),
                          "tc": g["is_tyre_change"].astype(float), "y": g["loss_s"].astype(float)})
        d = X - X.groupby(g["race"].to_numpy()).transform("mean")
        b = _ols(d[["laps", "dc", "tc"]].to_numpy(), d["y"].to_numpy())
        per_lap[(series, car_class)] = (max(float(b[0]), 0.0), float(g["stint_laps"].median()))
    plans = pd.read_csv(PLANS)
    base = changed = new_total = 0
    shares = []
    for r in plans.itertuples():
        b, stint = per_lap[(r.series, r.car_class)]
        fuel_time = b * stint
        shares.append(fuel_time / r.pit_loss_s)
        marginal = max(r.pit_loss_s - fuel_time, 0.1)
        n = optimal_stop_plan(int(r.race_laps), r.green_pace_s, r.net_slope_s, marginal,
                              int(r.fuel_range_laps)).n_stops
        was, now = r.optimal_stops != r.min_stops, n != r.min_stops
        base += was
        new_total += now
        changed += was != now
    return {
        "per_lap": {f"{s} {c}": round(v[0], 3) for (s, c), v in per_lap.items()},
        "median_fuel_share": float(np.median(shares)), "max_fuel_share": float(np.max(shares)),
        "tyre_limited_published": int(base), "tyre_limited_marginal": int(new_total),
        "n_changed": int(changed),
    }


def main() -> int:
    warnings.filterwarnings("ignore")
    out = {"race_clustering": race_clustering(), "interaction": interaction(), "refuelling": refuelling()}
    clean = json.loads(json.dumps(out), parse_float=lambda x: round(float(x), 6))
    OUT_JSON.write_text(json.dumps(clean, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    rc, it, rf = out["race_clustering"], out["interaction"], out["refuelling"]
    OUT_MD.write_text("\n".join([
        "<!-- GENERATED by scripts/run_estimation_checks.py — do not edit by hand. -->",
        "", "# Three checks on how the slopes are estimated and used", "",
        f"**Clustering by race.** Of {rc['n_slopes']} published linear slope terms, "
        f"{rc['zero_driver_race']} have an interval containing zero with driver-race "
        f"clusters and {rc['zero_race']} with race clusters.", "",
        f"**Fuel times tyre age.** On {it['n_circuits']} linear circuits the interaction "
        f"has median {it['gamma_median']:+.5f} s per lap of age per race lap, positive at "
        f"{it['n_gamma_positive']}, significant at {it['n_gamma_significant']}. The closed-form "
        f"planner's median gap to the real stop over {it['n_decisions']} decisions is "
        f"{it['gap_without']:+.1f} laps without it and {it['gap_with']:+.1f} with it; over the "
        f"{it['one_n']} one-stop decisions {it['one_gap_without']:+.1f} and {it['one_gap_with']:+.1f}.", "",
        f"**Refuelling time.** Seconds of stop loss per lap of fuel, by class: {rf['per_lap']}. "
        f"Refuelling is a median {100 * rf['median_fuel_share']:.0f}% of the measured stop loss "
        f"(at most {100 * rf['max_fuel_share']:.0f}%). With the marginal stop cost, "
        f"{rf['tyre_limited_marginal']} race-seasons are tyre-limited instead of "
        f"{rf['tyre_limited_published']}; {rf['n_changed']} change regime.", ""]), encoding="utf-8")
    print(json.dumps(clean, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
