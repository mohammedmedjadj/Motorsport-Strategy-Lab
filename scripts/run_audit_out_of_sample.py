"""Replay the committed-strategy audit with slopes the decision's race never saw.

The published audit replays decisions from the seasons the circuit models were
fitted on, so the slope a decision is judged with has already seen that race.
Result 1 says slopes move between seasons; if the audit only agreed with
practice because it was fitted in sample, the two halves of the paper would
contradict each other. Two replays of the same decisions, same engine, same
seed, same committed horizon (the team's next stop, or the flag):

* **Out of sample.** Fuel and degradation coefficients refitted on every
  pre-2026 season except the decision's own, at the published degree.
* **Wider uncertainty.** The published means, with each degradation standard
  error widened to the random-effects one of
  ``scripts/run_identification_checks.py`` -- sampling plus between-race
  variance -- where that circuit-compound has enough seasons. The engine then
  draws slopes that move between races as much as the data say they do.

The other circuit constants (pit loss, neutralisation rates, pace ratios) stay
as published; they are not what Result 1 calls into question.

Writes ``data/derived/f1/audit_out_of_sample.csv``,
``data/derived/f1/audit_out_of_sample_summary.json`` and
``reports/f1/audit_out_of_sample.md``.

    python scripts/run_audit_out_of_sample.py
"""

from __future__ import annotations

import dataclasses
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from run_committed_strategy import committed_lap  # noqa: E402
from src.audit.state import load_race_laps, pit_stops  # noqa: E402
from src.degradation.dataset import build_modelling_frame, load_circuit_laps  # noqa: E402
from src.degradation.model import fit_circuit  # noqa: E402
from src.ingestion.config import F1_DERIVED_DIR, PRE_ERA_SEASONS, REPORTS_DIR  # noqa: E402
from src.simulator.artifacts import CoefPosterior, _posterior, load_circuit_models  # noqa: E402

COMMITTED = F1_DERIVED_DIR / "committed_strategy.csv"
COEFS = F1_DERIVED_DIR / "degradation_coefficients.csv"
COMPONENTS = F1_DERIVED_DIR / "variance_components.csv"
OUT_CSV = F1_DERIVED_DIR / "audit_out_of_sample.csv"
OUT_JSON = F1_DERIVED_DIR / "audit_out_of_sample_summary.json"
OUT_MD = REPORTS_DIR / "f1" / "audit_out_of_sample.md"
BOOT_SEED = 20261110
BOOT_DRAWS = 10_000

warnings.filterwarnings("ignore", message=".*not ingested yet.*")
warnings.filterwarnings("ignore", message=".*missing a fitted layer.*")


def loso_model(model, circuit: str, season: int, degree: int):
    """The published circuit model with fuel and degradation refitted without ``season``."""
    seasons = tuple(s for s in PRE_ERA_SEASONS if s != season)
    frame, _ = build_modelling_frame(load_circuit_laps(circuit, seasons=seasons), circuit)
    fit = fit_circuit(frame, circuit, degree=degree)
    deg = {c: tuple(_posterior(k.value, k.se, k.n_clusters) for k in coefs)
           for c, coefs in fit.deg_coefs.items()}
    fuel = _posterior(fit.fuel_slope.value, fit.fuel_slope.se, fit.fuel_slope.n_clusters)
    return dataclasses.replace(model, degradation=deg, fuel_slope=fuel)


def widened_model(model, inflation: dict[str, float]):
    deg = {}
    for c, coefs in model.degradation.items():
        f = max(1.0, inflation.get(c, 1.0))
        deg[c] = tuple(CoefPosterior(k.mean, k.sd * f, k.df) for k in coefs)
    return dataclasses.replace(model, degradation=deg)


def build() -> pd.DataFrame:
    committed = pd.read_csv(COMMITTED).dropna(subset=["committed_pit_lap"])
    degrees = pd.read_csv(COEFS).groupby("circuit")["degree"].first()
    vc = pd.read_csv(COMPONENTS)
    inflation = {(r.circuit, r.compound): float(r.se_inflation) for r in vc.itertuples()
                 if np.isfinite(r.se_inflation)}
    models = load_circuit_models()
    laps_cache: dict[str, pd.DataFrame] = {}
    loso_cache: dict[tuple[str, int], object] = {}
    rows = []
    for i, row in enumerate(committed.itertuples(), 1):
        slug = f"{row.season}_{row.circuit}"
        if slug not in laps_cache:
            laps_cache[slug] = load_race_laps(slug)
        laps = laps_cache[slug]
        stops = pit_stops(laps, row.driver)
        horizon = int(stops[1]) if len(stops) >= 2 else int(laps["LapNumber"].max())
        base = models[row.circuit]
        key = (row.circuit, int(row.season))
        if key not in loso_cache:
            try:
                loso_cache[key] = loso_model(base, row.circuit, int(row.season),
                                             int(degrees[row.circuit]))
            except ValueError:
                # A circuit raced in one pre-2026 season only has nothing to
                # fit out of sample; the decision is counted, not replayed.
                loso_cache[key] = None
        out = {"season": row.season, "circuit": row.circuit, "driver": row.driver,
               "n_stops": row.n_stops, "decision_lap": row.decision_lap,
               "real_pit_lap": row.real_pit_lap, "committed_pit_lap": int(row.committed_pit_lap)}
        for name, model in (
            ("reproduced", base),
            ("out_of_sample", loso_cache[key]),
            ("widened", widened_model(base, {c: inflation.get((row.circuit, c), 1.0)
                                             for c in base.degradation})),
        ):
            try:
                result = None if model is None else committed_lap(row, laps, model, horizon)
            except (KeyError, ValueError):
                result = None
            out[f"{name}_pit_lap"] = None if result is None else result[0]
        rows.append(out)
        if i % 25 == 0:
            print(f"[{i}/{len(committed)}]", flush=True)
    frame = pd.DataFrame(rows)
    for name in ("reproduced", "out_of_sample", "widened"):
        frame[f"{name}_pit_lap"] = frame[f"{name}_pit_lap"].astype("Int64")
        frame[f"{name}_delta"] = frame[f"{name}_pit_lap"] - frame["real_pit_lap"]
    frame["committed_delta"] = frame["committed_pit_lap"] - frame["real_pit_lap"]
    return frame


def summarise(frame: pd.DataFrame) -> dict:
    rng = np.random.default_rng(BOOT_SEED)
    out = {"n": int(len(frame)),
           "reproduced_share": float((frame["reproduced_pit_lap"] == frame["committed_pit_lap"]).mean())}
    for name in ("out_of_sample", "widened"):
        f = frame.dropna(subset=[f"{name}_delta"])
        races = f["season"].astype(str) + "_" + f["circuit"]
        groups = {r: g for r, g in f.groupby(races)}
        keys = list(groups)

        def med(col: str, part: pd.DataFrame) -> float:
            return float(part[col].astype(float).median())

        def ci(col: str, one: bool) -> list[float]:
            draws = []
            for _ in range(BOOT_DRAWS):
                pick = pd.concat([groups[k] for k in rng.choice(keys, len(keys))])
                if one:
                    pick = pick[pick["n_stops"] == 1]
                draws.append(med(col, pick))
            return [float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))]

        one = f[f["n_stops"] == 1]
        moved = (f[f"{name}_pit_lap"] != f["committed_pit_lap"])
        out[name] = {
            "n": int(len(f)), "n_one": int(len(one)),
            "median": med(f"{name}_delta", f), "ci": ci(f"{name}_delta", False),
            "published_median": med("committed_delta", f),
            "one_median": med(f"{name}_delta", one), "one_ci": ci(f"{name}_delta", True),
            "one_published_median": med("committed_delta", one),
            "pct_moved": float(100 * moved.mean()),
            "median_abs_shift": float((f[f"{name}_pit_lap"] - f["committed_pit_lap"]).abs().astype(float).median()),
        }
    return out


def report(s: dict) -> str:
    lines = ["# The committed audit, out of sample", "",
             "Generated by `scripts/run_audit_out_of_sample.py`.", "",
             f"- {s['n']} committed decisions; the published engine reproduces "
             f"{100 * s['reproduced_share']:.1f}% of the published laps exactly.", ""]
    for name, label in (("out_of_sample", "Slopes fitted without the decision's season"),
                        ("widened", "Slope uncertainty widened to the random-effects error")):
        g = s[name]
        lines += [f"## {label}", "",
                  f"- {g['n']} decisions: median gap {g['median']:+.1f} laps "
                  f"[{g['ci'][0]:+.1f}, {g['ci'][1]:+.1f}] (races resampled), against "
                  f"{g['published_median']:+.1f} published on the same decisions.",
                  f"- One-stop ({g['n_one']}): {g['one_median']:+.1f} [{g['one_ci'][0]:+.1f}, "
                  f"{g['one_ci'][1]:+.1f}], against {g['one_published_median']:+.1f}.",
                  f"- The recommended lap moves for {g['pct_moved']:.0f}% of decisions; median "
                  f"absolute shift {g['median_abs_shift']:.0f} laps.", ""]
    return "\n".join(lines)


def main() -> int:
    frame = build()
    s = summarise(frame)
    frame.to_csv(OUT_CSV, index=False)
    OUT_JSON.write_text(json.dumps(s, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    OUT_MD.write_text(report(s), encoding="utf-8")
    print(report(s))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
