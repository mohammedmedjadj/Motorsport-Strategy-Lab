"""What teams' stop timing reveals, estimated without a lookback window.

The audit asks the planner a fixed number of laps before the team's stop, so
its gap is censored by that window, and the implied ratio inverts the closed
form at one lap per decision. Treating the stop as an optimal-replacement
decision (Rust, 1987) gives a third route that uses every lap of the stint:
a discrete-time hazard of stopping, lap by lap, on the two quantities the closed
form trades off.

With one stop before a fixed endpoint and linear slopes, stopping now beats
waiting a lap when the old tyre's next lap costs more than the new tyre would
have to carry to the endpoint, i.e. when

    beta_old * age_t  >  beta_new * (W - t)

So the hazard is fitted as

    logit P(stop at t | still out) = c + g_old * beta_old * age_t
                                       - g_new * beta_new * (W - t)
                                       + d * caution_t

with the fitted slopes plugged in. If teams weighed the two tyres exactly as the
fit does, g_new / g_old would be one; below one, they act as if the new tyre
wears more slowly, relative to the old, than the fit says -- the same reading as
the implied ratio, now from every lap of the stint rather than from the stop
alone. ``W`` is the team's next stop, or the flag, as in the committed replay.

The risk set is each audited first stint from the first lap a strategic stop is
admitted (the audit's minimum) to the real stop. Intervals resample races.

Writes ``data/derived/f1/stop_hazard_summary.json`` and
``reports/f1/stop_hazard.md``.

    python scripts/run_stop_hazard.py
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.audit.state import load_race_laps, pit_stops  # noqa: E402
from src.audit.systematic import MIN_FIRST_STOP_LAP  # noqa: E402
from src.ingestion.config import F1_DERIVED_DIR, REPORTS_DIR  # noqa: E402

DECISIONS = F1_DERIVED_DIR / "audit_design_checks.csv"
COEFS = F1_DERIVED_DIR / "degradation_coefficients.csv"
OUT_JSON = F1_DERIVED_DIR / "stop_hazard_summary.json"
OUT_MD = REPORTS_DIR / "f1" / "stop_hazard.md"
BOOT_SEED = 20261110
BOOT_DRAWS = 2_000

warnings.filterwarnings("ignore")


def risk_set() -> pd.DataFrame:
    coefs = pd.read_csv(COEFS)
    linear = coefs[coefs["degree"] == 1].set_index(["circuit", "compound"])["deg_p1"]
    dec = pd.read_csv(DECISIONS)
    dec = dec[(dec["lookback"] == 5) & dec["top"] & (dec["compound"] != dec["target"])]
    rows = []
    cache: dict[str, pd.DataFrame] = {}
    for r in dec.itertuples():
        if (r.circuit, r.compound) not in linear.index or (r.circuit, r.target) not in linear.index:
            continue
        b_old, b_new = float(linear[(r.circuit, r.compound)]), float(linear[(r.circuit, r.target)])
        if b_old <= 0 or b_new <= 0:
            continue
        slug = f"{r.season}_{r.circuit}"
        if slug not in cache:
            cache[slug] = load_race_laps(slug)
        laps = cache[slug]
        car = laps[laps["Driver"] == r.driver].set_index("LapNumber")
        stops = pit_stops(laps, r.driver)
        if not stops or stops[0] != r.real_pit_lap:
            continue
        horizon = int(r.horizon)
        for t in range(MIN_FIRST_STOP_LAP, int(r.real_pit_lap) + 1):
            if t not in car.index or pd.isna(car.loc[t, "TyreLife"]):
                continue
            rows.append({
                "race": slug, "driver": r.driver, "lap": t,
                "stop": int(t == r.real_pit_lap),
                "old_term": b_old * float(car.loc[t, "TyreLife"]),
                "new_term": b_new * float(horizon - t),
                "caution": float(bool(car.loc[t, "is_non_green"])) if "is_non_green" in car else 0.0,
            })
    return pd.DataFrame(rows)


def _logit(X: np.ndarray, y: np.ndarray, iters: int = 100) -> np.ndarray:
    """Maximum-likelihood logistic regression by Newton--Raphson."""
    beta = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1.0 / (1.0 + np.exp(-(X @ beta)))
        grad = X.T @ (y - p)
        hess = X.T @ (X * (p * (1 - p))[:, None])
        step = np.linalg.solve(hess + 1e-9 * np.eye(len(beta)), grad)
        beta += step
        if np.max(np.abs(step)) < 1e-10:
            break
    return beta


def fit(frame: pd.DataFrame) -> tuple[float, float, float, float]:
    X = np.column_stack([np.ones(len(frame)), frame["old_term"], frame["new_term"],
                         frame["caution"]])
    b = _logit(X, frame["stop"].to_numpy(dtype=float))
    g_old, g_new = float(b[1]), -float(b[2])
    return g_old, g_new, g_new / g_old if g_old else np.nan, float(b[3])


def main() -> int:
    frame = risk_set()
    g_old, g_new, ratio, caution = fit(frame)
    rng = np.random.default_rng(BOOT_SEED)
    groups = {k: v for k, v in frame.groupby("race")}
    keys = list(groups)
    draws = []
    for _ in range(BOOT_DRAWS):
        pick = pd.concat([groups[k] for k in rng.choice(keys, len(keys))])
        try:
            draws.append(fit(pick)[2])
        except Exception:  # noqa: BLE001 -- a degenerate resample is skipped and counted
            continue
    draws = np.array([d for d in draws if np.isfinite(d)])
    s = {
        "n_stints": int(frame.groupby(["race", "driver"]).ngroups),
        "n_laps": int(len(frame)), "n_races": int(frame["race"].nunique()),
        "g_old": g_old, "g_new": g_new, "ratio": ratio,
        "ratio_ci": [float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))],
        "caution_coef": caution, "n_boot_kept": int(len(draws)),
        "both_positive": bool(g_old > 0 and g_new > 0),
    }
    OUT_JSON.write_text(json.dumps({k: (round(v, 6) if isinstance(v, float) else v)
                                    for k, v in s.items()}, indent=1, sort_keys=True) + "\n",
                        encoding="utf-8")
    md = "\n".join([
        "# Stop hazard", "", "Generated by `scripts/run_stop_hazard.py`.", "",
        f"- {s['n_stints']} first stints in {s['n_races']} races, {s['n_laps']} laps at risk.",
        f"- Weight on the old tyre's next-lap loss {g_old:.3f}, on the new tyre's remaining loss "
        f"{g_new:.3f}: ratio {ratio:.2f} [{s['ratio_ci'][0]:.2f}, {s['ratio_ci'][1]:.2f}] "
        f"(races resampled, {s['n_boot_kept']} replicates). One would mean teams weigh the two "
        "tyres as the fit does.",
        f"- Caution coefficient {caution:+.2f} (log-odds of stopping on a neutralised lap).", ""])
    OUT_MD.write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
