"""Three design checks on the committed-strategy audit.

The committed replay asks the planner for the first stop five laps before the
real one, for the top five finishers, with the team's next stop (or the flag)
as the horizon. Each of those choices can manufacture part of the answer, and
this script measures how much.

1. **Censoring.** Asked ``L`` laps before the real stop, the planner can be at
   most ``L - 1`` laps early and arbitrarily late. The share of decisions at
   that bound is reported, and the replay is rerun with ``L`` = 5, 10 and 15.
2. **Selection.** The top five finishers are the cars whose strategy worked and
   that most often ran in clean air. The replay is rerun on every car running
   at the flag, and both are reported.
3. **The slope ratio.** With one stop before a fixed endpoint and a linear
   slope, the time-optimal stop lap solves
   ``beta_old * (a0 + k) = beta_new * (W - k)``: it depends on the two slopes
   only through their ratio, and fuel and any cost paid once per stop cancel.
   So the gap is split by how precisely that ratio is measured, and the ratio
   each team's real stop implies is set against the fitted one. Both use only
   linear circuits, where the slope is one number.

Rivals, Safety Car risk and the engine itself are as in the committed replay;
the closed form of check 3 leaves rivals and neutralisations out, and its
agreement with the engine is reported so that the reader can see how much that
matters.

Writes ``data/derived/f1/audit_design_checks.csv``,
``audit_design_checks_summary.json`` and ``reports/f1/audit_design_checks.md``.

    python scripts/run_audit_design_checks.py
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO))

from run_committed_strategy import committed_lap  # noqa: E402
from src.audit.state import compound_after, load_race_laps, pit_stops, state_at  # noqa: E402
from src.audit.systematic import MIN_FIRST_STOP_LAP  # noqa: E402
from src.ingestion.config import F1_DERIVED_DIR, F1_REPORTS_DIR  # noqa: E402
from src.simulator.artifacts import load_circuit_models  # noqa: E402

LOOKBACKS = (5, 10, 15)
TOP = 5
BOOT_SEED = 20261108
BOOT_DRAWS = 5_000

AUDIT = F1_DERIVED_DIR / "systematic_audit.csv"
COEFS = F1_DERIVED_DIR / "degradation_coefficients.csv"
OUT_CSV = F1_DERIVED_DIR / "audit_design_checks.csv"
OUT_JSON = F1_DERIVED_DIR / "audit_design_checks_summary.json"
OUT_MD = F1_REPORTS_DIR / "audit_design_checks.md"


def running_at_flag(laps: pd.DataFrame) -> list[tuple[str, int, int]]:
    """Every car that took the flag: (driver, position, last lap), by position.

    Lapped cars count; their horizon is their own last lap.
    """
    last = laps.sort_values("LapNumber").groupby("Driver").tail(1)
    leader_laps = int(laps["LapNumber"].max())
    # A car more than three laps down at the end was not running a strategy.
    kept = last[(last["LapNumber"] >= leader_laps - 3) & last["Position"].notna()]
    kept = kept.sort_values("Position")
    return [(str(r.Driver), int(r.Position), int(r.LapNumber)) for r in kept.itertuples()]


def build() -> pd.DataFrame:
    races = sorted(pd.read_csv(AUDIT)[["season", "circuit"]].drop_duplicates().itertuples(index=False))
    models = load_circuit_models()
    rows = []
    for season, circuit in races:
        laps = load_race_laps(f"{season}_{circuit}")
        model = models[circuit]
        for rank, (driver, position, last_lap) in enumerate(running_at_flag(laps), 1):
            stops = pit_stops(laps, driver)
            if not stops or stops[0] < MIN_FIRST_STOP_LAP:
                continue
            real = stops[0]
            horizon = stops[1] if len(stops) >= 2 else last_lap
            for lookback in LOOKBACKS:
                decision = real - lookback
                if decision < 2:
                    continue
                try:
                    state = state_at(laps, driver, decision)
                    target = compound_after(laps, driver, real)
                except (LookupError, ValueError):
                    continue
                if state.compound not in model.degradation or target not in model.degradation:
                    continue  # wet or intermediate tyres: the published audit skips them too
                row = SimpleNamespace(circuit=circuit, driver=driver,
                                      decision_lap=decision, real_pit_lap=real)
                result = committed_lap(row, laps, model, int(horizon))
                if result is None:
                    continue
                lap, _ = result
                rows.append({
                    "season": season, "circuit": circuit, "driver": driver,
                    "rank": rank, "top": rank <= TOP, "lookback": lookback,
                    "n_stops": len(stops), "decision_lap": decision,
                    "real_pit_lap": real, "horizon": int(horizon),
                    "tyre_age": int(state.tyre_age), "compound": state.compound,
                    "target": target, "planner_pit_lap": lap,
                    "delta_laps": lap - real,
                    "at_bound": lap == decision + 1,
                })
    return pd.DataFrame(rows)


def add_ratio(frame: pd.DataFrame) -> pd.DataFrame:
    coefs = pd.read_csv(COEFS).set_index(["circuit", "compound"])
    out = frame.copy()
    cls, fitted, implied, closed = [], [], [], []
    for r in out.itertuples():
        old = coefs.loc[(r.circuit, r.compound)] if (r.circuit, r.compound) in coefs.index else None
        new = coefs.loc[(r.circuit, r.target)] if (r.circuit, r.target) in coefs.index else None
        k = r.real_pit_lap - r.decision_lap
        w = r.horizon - r.decision_lap
        ratio = imp = form = np.nan
        if old is None or new is None or int(old["degree"]) != 1:
            label = "quadratic circuit"
        elif r.compound == r.target:
            label = "same compound"
            ratio = 1.0
        else:
            b_old, b_new = float(old["deg_p1"]), float(new["deg_p1"])
            if b_old <= 0 or b_new <= 0:
                label = "unresolved"
            else:
                ratio = b_new / b_old
                se = np.hypot(old["deg_p1_se"] / b_old, new["deg_p1_se"] / b_new)
                label = "resolved" if abs(np.log(ratio)) > 1.96 * se else "unresolved"
        if np.isfinite(ratio) and w - k > 0 and r.tyre_age + k > 0:
            imp = (r.tyre_age + k) / (w - k)
            form = r.decision_lap + (ratio * w - r.tyre_age) / (1 + ratio)
        cls.append(label)
        fitted.append(ratio)
        implied.append(imp)
        closed.append(form)
    out["ratio_class"] = cls
    out["fitted_ratio"] = fitted
    out["implied_ratio"] = implied
    out["closed_form_lap"] = closed
    return out


def race_ci(part: pd.DataFrame, column: str, rng, stat=np.median) -> tuple[float, float]:
    key = part["season"].astype(str) + "_" + part["circuit"]
    groups = [g[column].to_numpy(dtype=float) for _, g in part.groupby(key)]
    n = len(groups)
    draws = np.empty(BOOT_DRAWS)
    for i in range(BOOT_DRAWS):
        picked = rng.integers(0, n, size=n)
        draws[i] = stat(np.concatenate([groups[j] for j in picked]))
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return float(lo), float(hi)


def hodges_lehmann(x: np.ndarray) -> float:
    """Median of the Walsh averages: a location estimate that does not step
    in whole laps the way a median of whole-lap gaps does."""
    x = np.asarray(x, dtype=float)
    i, j = np.triu_indices(len(x))
    return float(np.median((x[i] + x[j]) / 2))


def summarise(frame: pd.DataFrame) -> dict:
    rng = np.random.default_rng(BOOT_SEED)
    out: dict = {"grid": {}}
    for (lookback, field), part in (
        [((lb, "top"), frame[(frame["lookback"] == lb) & frame["top"]]) for lb in LOOKBACKS]
        + [((lb, "all"), frame[frame["lookback"] == lb]) for lb in LOOKBACKS]
    ):
        one = part[part["n_stops"] == 1]
        lo, hi = race_ci(part, "delta_laps", rng)
        olo, ohi = race_ci(one, "delta_laps", rng)
        out["grid"][f"{field}_{lookback}"] = {
            "n": int(len(part)), "n_races": int(part[["season", "circuit"]].drop_duplicates().shape[0]),
            "median": float(part["delta_laps"].median()), "ci_low": lo, "ci_high": hi,
            "hl": hodges_lehmann(part["delta_laps"].to_numpy()),
            "one_n": int(len(one)), "one_median": float(one["delta_laps"].median()),
            "one_ci_low": olo, "one_ci_high": ohi,
            "one_hl": hodges_lehmann(one["delta_laps"].to_numpy()),
            "at_bound": float(part["at_bound"].mean()),
            "later": float((part["delta_laps"] > 0).mean()),
        }
    base = frame[(frame["lookback"] == 5) & frame["top"]]
    out["ratio"] = {}
    for label, part in base.groupby("ratio_class"):
        one = part[part["n_stops"] == 1]
        out["ratio"][label] = {
            "n": int(len(part)), "median": float(part["delta_laps"].median()),
            "abs_median": float(part["delta_laps"].abs().median()),
            "one_n": int(len(one)),
            "one_median": float(one["delta_laps"].median()) if len(one) else float("nan"),
        }
    usable = base.dropna(subset=["implied_ratio", "fitted_ratio"])
    usable = usable[usable["ratio_class"] != "same compound"]
    log_gap = np.log(usable["implied_ratio"]) - np.log(usable["fitted_ratio"])
    usable = usable.assign(below=(log_gap < 0).astype(float), log_gap=log_gap)
    share_lo, share_hi = race_ci(usable, "below", rng, stat=np.mean)
    imp_lo, imp_hi = race_ci(usable, "implied_ratio", rng)
    out["implied"] = {
        "share_below_ci": [share_lo, share_hi],
        "median_implied_ci": [imp_lo, imp_hi],
        "n": int(len(usable)),
        "median_fitted": float(usable["fitted_ratio"].median()),
        "median_implied": float(usable["implied_ratio"].median()),
        "median_factor": float(np.exp(log_gap.median())),
        "share_below": float((log_gap < 0).mean()),
    }
    lin = base.dropna(subset=["closed_form_lap"])
    out["closed_form"] = {
        "n": int(len(lin)),
        "median_abs_vs_engine": float((lin["closed_form_lap"] - lin["planner_pit_lap"]).abs().median()),
    }
    return out


def _json(stats: dict) -> str:
    def clean(v):
        if isinstance(v, dict):
            return {k: clean(x) for k, x in v.items()}
        return round(v, 6) if isinstance(v, float) else v
    return json.dumps(clean(stats), indent=1, sort_keys=True) + "\n"


def report(s: dict) -> str:
    lines = [
        "<!-- GENERATED by scripts/run_audit_design_checks.py — do not edit by hand. -->",
        "",
        "# Design checks on the committed-strategy audit",
        "",
        "## Censoring and selection",
        "",
        "Median of planner lap minus real lap, horizon at the team's next stop "
        "or the flag. Intervals resample races. HL is the Hodges-Lehmann "
        "estimate. 'At bound' is the share the planner put on the earliest lap "
        "it was allowed.",
        "",
        "| cars | asked laps before | decisions | median | 95% interval | HL | one-stop median | one-stop interval | at bound |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for key, g in s["grid"].items():
        field, lb = key.split("_")
        lines.append(
            f"| {'top five' if field == 'top' else 'all at the flag'} | {lb} | {g['n']} | "
            f"{g['median']:+.0f} | [{g['ci_low']:+.1f}, {g['ci_high']:+.1f}] | {g['hl']:+.1f} | "
            f"{g['one_median']:+.0f} | [{g['one_ci_low']:+.1f}, {g['one_ci_high']:+.1f}] | "
            f"{100 * g['at_bound']:.0f}% |"
        )
    lines += [
        "",
        "## The slope ratio",
        "",
        "Top five, asked five laps before. 'Resolved' means the 95% interval of the",
        "log ratio of the new compound's slope to the old one's excludes zero.",
        "",
        "| ratio | decisions | median gap | median absolute gap | one-stop decisions | one-stop median |",
        "|---|---|---|---|---|---|",
    ]
    for label, g in s["ratio"].items():
        lines.append(
            f"| {label} | {g['n']} | {g['median']:+.0f} | {g['abs_median']:.0f} | "
            f"{g['one_n']} | {g['one_median']:+.0f} |"
        )
    i, c = s["implied"], s["closed_form"]
    lines += [
        "",
        f"On {i['n']} decisions between two different compounds at linear circuits, "
        f"the fitted ratio has median {i['median_fitted']:.2f} and the ratio the "
        f"team's real stop implies has median {i['median_implied']:.2f}; the "
        f"implied ratio is the smaller in {100 * i['share_below']:.0f}% of them "
        f"[{100 * i['share_below_ci'][0]:.0f}%, {100 * i['share_below_ci'][1]:.0f}%], "
        f"median implied ratio interval [{i['median_implied_ci'][0]:.2f}, "
        f"{i['median_implied_ci'][1]:.2f}] (median factor {i['median_factor']:.2f}).",
        "",
        f"The closed form lands a median of {c['median_abs_vs_engine']:.1f} laps from "
        f"the engine's own lap on {c['n']} linear-circuit decisions.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    warnings.filterwarnings("ignore")
    frame = add_ratio(build())
    stats = summarise(frame)
    frame.to_csv(OUT_CSV, index=False)
    OUT_JSON.write_text(_json(stats), encoding="utf-8")
    OUT_MD.write_text(report(stats), encoding="utf-8")
    print(report(stats))
    return 0


if __name__ == "__main__":
    sys.exit(main())
