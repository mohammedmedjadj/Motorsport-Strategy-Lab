"""Does the between-race slope variance survive three objections?

Section 4.2 estimates, for each Formula 1 circuit and relative compound label,
the between-race variance tau² of the season slopes (DerSimonian--Laird). Three
objections, each tested here:

1. **Compound labels.** Pirelli nominates three of its compounds for each race,
   so a circuit's Medium can be a different rubber in different seasons, and
   part of tau² could be a change of compound. Two answers: recompute on the
   real compound each lap ran on (C0--C6, the 2022 C1 coded C0), and keep only
   the circuits whose nomination never changed.
2. **Net slope.** Fitted season by season, the wear slope beta and the
   lap-number term phi trade off against each other: they are separated only by
   stints that start at different laps. The within-stint score measures the net
   slope beta + phi, so its variance is the one that bears on Result 1. It is
   estimated directly by reparametrising the same model:
   phi * lap + beta * age = phi * (lap - age) + (beta + phi) * age.
3. **Estimator.** With three or four seasons, DerSimonian--Laird is biased
   downwards when heterogeneity is large. Each set is re-estimated by REML,
   per circuit-compound and as one tau common to all of them (a hierarchical
   model with one mean per circuit-compound), with an interval from resampling
   circuits.

Writes ``data/derived/f1/tau_robustness_summary.json`` and
``reports/f1/tau_robustness.md``.

    python scripts/run_tau_robustness.py
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import optimize

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from run_compound_identity import load_allocation, recode  # noqa: E402
from run_identification_checks import MIN_CLUSTERS, MIN_SEASONS, random_effects  # noqa: E402
from src.degradation.dataset import build_modelling_frame, circuits_with_laps, load_circuit_laps  # noqa: E402
from src.degradation.model import fit_circuit  # noqa: E402
from src.ingestion.config import F1_DERIVED_DIR, PRE_ERA_SEASONS, REPORTS_DIR  # noqa: E402

PUBLISHED = F1_DERIVED_DIR / "season_slopes.csv"
IDENTITY = F1_DERIVED_DIR / "compound_identity.csv"
OUT_JSON = F1_DERIVED_DIR / "tau_robustness_summary.json"
OUT_MD = REPORTS_DIR / "f1" / "tau_robustness.md"
BOOT_SEED = 20261111
BOOT_DRAWS = 2_000

warnings.filterwarnings("ignore", message=".*not ingested yet.*")


def season_slopes(mode: str) -> pd.DataFrame:
    """Season slopes under ``mode``: 'real' compound coding or the 'net' slope."""
    allocation = load_allocation()
    rows = []
    for circuit in circuits_with_laps(seasons=PRE_ERA_SEASONS):
        frame, _ = build_modelling_frame(load_circuit_laps(circuit, seasons=PRE_ERA_SEASONS), circuit)
        if mode == "real":
            frame = recode(frame, allocation, circuit)
        elif mode == "net":
            frame = frame.assign(LapNumber=frame["LapNumber"] - frame["TyreLife"])
        for season, part in frame.groupby("season"):
            if part["driver_race"].nunique() < MIN_CLUSTERS:
                continue
            fit = fit_circuit(part, circuit, degree=1)
            for compound, coefs in fit.deg_coefs.items():
                c = coefs[0]
                n_dr = part.loc[part["Compound"] == compound, "driver_race"].nunique()
                if n_dr < MIN_CLUSTERS or not np.isfinite(c.se) or c.se <= 0:
                    continue
                rows.append({"circuit": circuit, "compound": compound, "season": int(season),
                             "slope": c.value, "se": c.se})
    return pd.DataFrame(rows)


def _reml_tau2(y: np.ndarray, v: np.ndarray, groups: np.ndarray) -> float:
    """REML tau² for a model with one mean per group and a common tau²."""
    X = pd.get_dummies(groups).to_numpy(dtype=float)

    def neg_ll(log_t2: float) -> float:
        t2 = np.exp(log_t2)
        w = 1.0 / (v + t2)
        xtwx = X.T @ (X * w[:, None])
        b = np.linalg.solve(xtwx, X.T @ (w * y))
        r = y - X @ b
        return 0.5 * (np.sum(np.log(v + t2)) + np.linalg.slogdet(xtwx)[1] + np.sum(w * r**2))

    grid = np.linspace(np.log(1e-10), np.log(10 * np.var(y) + 1e-8), 200)
    vals = [neg_ll(g) for g in grid]
    start = grid[int(np.argmin(vals))]
    res = optimize.minimize_scalar(neg_ll, bounds=(start - 1.0, start + 1.0), method="bounded")
    t2 = float(np.exp(res.x))
    return t2 if t2 > 1e-9 else 0.0


def components(slopes: pd.DataFrame, keep: set | None = None) -> tuple[pd.DataFrame, dict]:
    rows = []
    for (circuit, compound), g in slopes.groupby(["circuit", "compound"]):
        if len(g) < MIN_SEASONS or (keep is not None and circuit not in keep):
            continue
        y, v = g["slope"].to_numpy(), g["se"].to_numpy() ** 2
        re = random_effects(y, v)
        t2_reml = _reml_tau2(y, v, np.zeros(len(y), dtype=int))
        rows.append({"circuit": circuit, "compound": compound, "k": re["k"], "q_p": re["q_p"],
                     "i2": re["i2"], "mu": re["mu"], "mu_se": re["mu_se_re"],
                     "tau_dl": float(np.sqrt(re["tau2"])), "tau_reml": float(np.sqrt(t2_reml))})
    vc = pd.DataFrame(rows)
    vc["share_dl"] = vc["tau_dl"] / vc["mu"].abs()
    vc["share_reml"] = vc["tau_reml"] / vc["mu"].abs()
    # One tau common to every circuit-compound, on the scale of each one's own
    # mean (slopes differ several-fold between circuits, so an absolute common
    # tau would be set by the largest of them). Only means resolved from zero
    # can serve as a scale.
    resolved = vc[vc["mu"].abs() > 2 * vc["mu_se"]][["circuit", "compound", "mu"]]
    used = slopes.merge(resolved, on=["circuit", "compound"])
    used = used.assign(rel=used["slope"] / used["mu"].abs(), rel_v=(used["se"] / used["mu"].abs()) ** 2)
    group = (used["circuit"] + "|" + used["compound"]).to_numpy()
    common = float(np.sqrt(_reml_tau2(used["rel"].to_numpy(), used["rel_v"].to_numpy(), group)))
    rng = np.random.default_rng(BOOT_SEED)
    circuits = vc["circuit"].unique()
    by_circuit = {c: used[used["circuit"] == c] for c in circuits if (used["circuit"] == c).any()}
    draws, share_draws = [], []
    for _ in range(BOOT_DRAWS):
        pick = rng.choice(circuits, len(circuits))
        parts = [by_circuit[c].assign(circuit=f"{c}#{j}") for j, c in enumerate(pick) if c in by_circuit]
        sample = pd.concat(parts) if parts else used.iloc[:0]
        g = (sample["circuit"] + "|" + sample["compound"]).to_numpy()
        if len(sample):
            draws.append(np.sqrt(_reml_tau2(sample["rel"].to_numpy(), sample["rel_v"].to_numpy(), g)))
        share_draws.append(np.median(pd.concat([vc[vc["circuit"] == c] for c in pick])["share_reml"]))
    summary = {
        "n": int(len(vc)), "n_circuits": int(len(circuits)),
        "n_heterogeneous": int((vc["q_p"] < 0.05).sum()),
        "i2_median": float(vc["i2"].median()),
        "share_dl_median": float(vc["share_dl"].median()),
        "share_reml_median": float(vc["share_reml"].median()),
        "share_reml_ci": [float(np.percentile(share_draws, 2.5)), float(np.percentile(share_draws, 97.5))],
        "n_resolved_means": int(len(resolved)),
        "common_tau_share": common,
        "common_tau_share_ci": [float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))],
    }
    return vc, summary


def main() -> int:
    published = pd.read_csv(PUBLISHED)
    identity = pd.read_csv(IDENTITY)
    unchanged = set(identity.loc[~identity["allocation_changed"].astype(bool), "circuit"])
    sets = {
        "published": components(published)[1],
        "unchanged_allocation": components(published, keep=unchanged)[1],
        "real_compound": components(season_slopes("real"))[1],
        "net_slope": components(season_slopes("net"))[1],
    }

    def clean(o):
        if isinstance(o, dict):
            return {str(k): clean(x) for k, x in o.items()}
        if isinstance(o, list):
            return [clean(x) for x in o]
        return round(o, 6) if isinstance(o, float) else o

    OUT_JSON.write_text(json.dumps(clean(sets), indent=1, sort_keys=True) + "\n", encoding="utf-8")
    lines = ["# Between-race slope variance: three objections", "",
             "Generated by `scripts/run_tau_robustness.py`.", "",
             "| set | circuit-compounds | circuits | Q rejects | median I² | tau/mean (DL) | "
             "tau/mean (REML) | common relative tau, REML (resolved means) |",
             "|---|---|---|---|---|---|---|---|"]
    for name, s in sets.items():
        lines.append(
            f"| {name} | {s['n']} | {s['n_circuits']} | {s['n_heterogeneous']} | {s['i2_median']:.2f} | "
            f"{s['share_dl_median']:.2f} | {s['share_reml_median']:.2f} "
            f"[{s['share_reml_ci'][0]:.2f}, {s['share_reml_ci'][1]:.2f}] | "
            f"{s['common_tau_share']:.2f} [{s['common_tau_share_ci'][0]:.2f}, "
            f"{s['common_tau_share_ci'][1]:.2f}] ({s['n_resolved_means']}) |")
    lines.append("")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
