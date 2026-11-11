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
admitted (the audit's minimum) to the real stop. Intervals resample races, and
each replicate refits every circuit's slopes on the races it drew: inside one
stint ``age_t + (W - t)`` is constant, so the two weights are told apart only by
how the slopes and ``W`` vary between stints, and the slopes' own noise is part
of what identifies the ratio, not a detail of its variance. ``W`` is the team's
next stop, known only after the fact, as in the committed replay.

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
from src.degradation.dataset import build_modelling_frame, load_circuit_laps  # noqa: E402
from src.ingestion.config import PRE_ERA_SEASONS  # noqa: E402
from src.audit.systematic import MIN_FIRST_STOP_LAP  # noqa: E402
from src.ingestion.config import F1_DERIVED_DIR, REPORTS_DIR  # noqa: E402

DECISIONS = F1_DERIVED_DIR / "audit_design_checks.csv"
COEFS = F1_DERIVED_DIR / "degradation_coefficients.csv"
OUT_JSON = F1_DERIVED_DIR / "stop_hazard_summary.json"
OUT_MD = REPORTS_DIR / "f1" / "stop_hazard.md"
BOOT_SEED = 20261110
BOOT_DRAWS = 1_000
HARDNESS = {"SOFT": 0, "MEDIUM": 1, "HARD": 2}

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
                "race": slug, "circuit": r.circuit, "driver": r.driver, "lap": t,
                "compound": r.compound, "target": r.target,
                "stop": int(t == r.real_pit_lap),
                "age": float(car.loc[t, "TyreLife"]), "remaining": float(horizon - t),
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


def _linear_slopes(frame: pd.DataFrame) -> dict[str, float]:
    """The published linear model's compound slopes, fitted by within-driver-race OLS.

    Same design as ``src.degradation.model.fit_circuit`` at degree one (driver-race
    fixed effects, lap number, compound x tyre age), with the fixed effects swept
    out by demeaning, which gives identical slopes and is fast enough to refit in
    every bootstrap replicate.
    """
    compounds = sorted(frame["Compound"].unique())
    cols = [frame["LapNumber"].to_numpy(dtype=float)]
    for c in compounds:
        cols.append(((frame["Compound"] == c).to_numpy(dtype=float)
                     * frame["TyreLife"].to_numpy(dtype=float)))
    X = pd.DataFrame(np.column_stack(cols))
    y = frame["lap_time_s"].to_numpy(dtype=float)
    g = frame["driver_race"].to_numpy()
    Xd = (X - X.groupby(g).transform("mean")).to_numpy()
    yd = y - pd.Series(y).groupby(g).transform("mean").to_numpy()
    beta = np.linalg.lstsq(Xd, yd, rcond=None)[0]
    return {c: float(beta[1 + i]) for i, c in enumerate(compounds)}


def _modelling_frames(circuits) -> dict[str, pd.DataFrame]:
    out = {}
    for circuit in circuits:
        frame, _ = build_modelling_frame(load_circuit_laps(circuit, seasons=PRE_ERA_SEASONS),
                                         circuit)
        out[circuit] = frame
    return out


def _with_slopes(risk: pd.DataFrame, slopes: dict) -> pd.DataFrame | None:
    old = np.array([slopes.get(c, {}).get(k, np.nan) for c, k in zip(risk["circuit"], risk["compound"])])
    new = np.array([slopes.get(c, {}).get(k, np.nan) for c, k in zip(risk["circuit"], risk["target"])])
    keep = np.isfinite(old) & np.isfinite(new) & (old > 0) & (new > 0)
    out = risk[keep].copy()
    out["old_term"] = old[keep] * out["age"].to_numpy()
    out["new_term"] = new[keep] * out["remaining"].to_numpy()
    return out


def main() -> int:
    frame = risk_set()
    g_old, g_new, ratio, caution = fit(frame)
    frames = _modelling_frames(sorted(frame["circuit"].unique()))
    published = {c: _linear_slopes(f) for c, f in frames.items()}
    check = _with_slopes(frame, published)
    # The fast refit reproduces the published slopes, so the replicates below
    # differ from the point estimate only by the races they drew.
    assert len(check) == len(frame) and np.allclose(check["old_term"], frame["old_term"], atol=1e-6)
    races = {c: sorted(f["race"].unique()) for c, f in frames.items()}
    by_race = {c: {r: g for r, g in f.groupby("race")} for c, f in frames.items()}
    risk_by_race = {k: v for k, v in frame.groupby("race")}
    all_races = [(c, r) for c in races for r in races[c]]
    rng = np.random.default_rng(BOOT_SEED)
    draws, fixed_draws = [], []
    dir_draws = {"to harder": [], "to softer": []}
    for b in range(BOOT_DRAWS):
        pick = [all_races[i] for i in rng.integers(0, len(all_races), len(all_races))]
        slopes, parts = {}, []
        for c in races:
            mine = [r for cc, r in pick if cc == c]
            if not mine:
                continue
            fit_frame = pd.concat([
                by_race[c][r].assign(driver_race=by_race[c][r]["driver_race"] + f"#{j}")
                for j, r in enumerate(mine)])
            slopes[c] = _linear_slopes(fit_frame)
        for j, (c, r) in enumerate(pick):
            if r in risk_by_race:
                parts.append(risk_by_race[r].assign(race=f"{r}#{j}"))
        if not parts:
            continue
        sample = pd.concat(parts)
        try:
            fixed_draws.append(fit(sample)[2])
            refit = _with_slopes(sample, slopes)
            draws.append(fit(refit)[2])
            harder = refit["target"].map(HARDNESS) > refit["compound"].map(HARDNESS)
            for label, part in (("to harder", refit[harder]), ("to softer", refit[~harder])):
                try:
                    dir_draws[label].append(fit(part)[2])
                except Exception:  # noqa: BLE001
                    pass
        except Exception:  # noqa: BLE001 -- a degenerate resample is skipped and counted
            continue
    draws = np.array([d for d in draws if np.isfinite(d)])
    fixed_draws = np.array([d for d in fixed_draws if np.isfinite(d)])
    directions = {}
    to_harder = frame["target"].map(HARDNESS) > frame["compound"].map(HARDNESS)
    for label, part in (("to harder", frame[to_harder]), ("to softer", frame[~to_harder])):
        try:
            d = np.array([x for x in dir_draws[label] if np.isfinite(x)])
            directions[label] = {"n_stints": int(part.groupby(["race", "driver"]).ngroups),
                                 "ratio": fit(part)[2],
                                 "ratio_ci": [float(np.percentile(d, 2.5)),
                                              float(np.percentile(d, 97.5))]}
        except Exception:  # noqa: BLE001
            directions[label] = {"n_stints": int(part.groupby(["race", "driver"]).ngroups),
                                 "ratio": float("nan")}
    s = {
        "n_stints": int(frame.groupby(["race", "driver"]).ngroups),
        "n_laps": int(len(frame)), "n_races": int(frame["race"].nunique()),
        "g_old": g_old, "g_new": g_new, "ratio": ratio,
        "ratio_ci": [float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))],
        "ratio_ci_fixed_slopes": [float(np.percentile(fixed_draws, 2.5)),
                                  float(np.percentile(fixed_draws, 97.5))],
        "directions": directions,
        "caution_coef": caution, "n_boot_kept": int(len(draws)),
        "both_positive": bool(g_old > 0 and g_new > 0),
    }
    def clean(v):
        if isinstance(v, dict):
            return {k: clean(x) for k, x in v.items()}
        if isinstance(v, list):
            return [clean(x) for x in v]
        return round(v, 6) if isinstance(v, float) else v
    OUT_JSON.write_text(json.dumps(clean(s), indent=1, sort_keys=True) + "\n", encoding="utf-8")
    md = "\n".join([
        "# Stop hazard", "", "Generated by `scripts/run_stop_hazard.py`.", "",
        f"- {s['n_stints']} first stints in {s['n_races']} races, {s['n_laps']} laps at risk.",
        f"- Weight on the old tyre's next-lap loss {g_old:.3f}, on the new tyre's remaining loss "
        f"{g_new:.3f}: ratio {ratio:.2f} [{s['ratio_ci'][0]:.2f}, {s['ratio_ci'][1]:.2f}] "
        f"(races resampled and every circuit's slopes refitted on the races drawn, "
        f"{s['n_boot_kept']} replicates; with the slopes held fixed the interval would be "
        f"[{s['ratio_ci_fixed_slopes'][0]:.2f}, {s['ratio_ci_fixed_slopes'][1]:.2f}]). One would "
        "mean teams weigh the two tyres as the fit does.",
        "- By direction of the change: " + "; ".join(
            f"{k} {v['ratio']:.2f} [{v.get('ratio_ci', [np.nan, np.nan])[0]:.2f}, "
            f"{v.get('ratio_ci', [np.nan, np.nan])[1]:.2f}] ({v['n_stints']} stints)"
            for k, v in directions.items()) + ".",
        f"- Caution coefficient {caution:+.2f} (log-odds of stopping on a neutralised lap).", ""])
    OUT_MD.write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
