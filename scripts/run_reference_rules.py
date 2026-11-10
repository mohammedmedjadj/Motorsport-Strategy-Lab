"""Two reference points for the committed audit that need no simulation.

**The closed form at a ratio of one.** With one stop before a fixed endpoint and
linear slopes, the time-optimal stop balances tyre age either side of it; when
the two tyres wear alike (ratio one), that is the lap where the old tyre's age
at the stop equals the new tyre's age at the endpoint. It uses no fitted
quantity at all, only the tyre's age at the decision and the endpoint the
committed replay already gives the optimiser (the team's next stop, or the
flag). If it lands as close to the real stop as the engine, the Monte Carlo
contributes nothing to the agreement, and that should be said.

**Green-flag stops only.** A stop taken under a Safety Car or full-course yellow
is a reaction to the flag, not a timing decision the tyre model could have made.
The committed gap is reported again on the decisions whose real stop was taken
under green, with the share of stops that were not.

Writes ``data/derived/cross_series/reference_rules.csv`` and
``reports/cross_series/reference_rules.md``.

    python scripts/run_reference_rules.py
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

from src.data.endurance_loader import EnduranceLoader  # noqa: E402
from src.ingestion.config import DERIVED_DIR, F1_DERIVED_DIR, REPORTS_DIR  # noqa: E402

OUT_CSV = DERIVED_DIR / "cross_series" / "reference_rules.csv"
OUT_JSON = DERIVED_DIR / "cross_series" / "reference_rules_summary.json"
OUT_MD = REPORTS_DIR / "cross_series" / "reference_rules.md"
BOOT_SEED = 20261110
BOOT_DRAWS = 10_000

warnings.filterwarnings("ignore")


def ratio_one_lap(decision: int, tyre_age: float, horizon: int) -> int:
    """Stop lap at which the old tyre's age equals the new tyre's age at the endpoint."""
    lap = round((horizon + decision - tyre_age) / 2)
    return int(min(max(lap, decision + 1), horizon - 1))


def f1_rows() -> pd.DataFrame:
    dec = pd.read_csv(F1_DERIVED_DIR / "audit_design_checks.csv")
    dec = dec[(dec["lookback"] == 5) & dec["top"]]
    com = pd.read_csv(F1_DERIVED_DIR / "committed_strategy.csv")
    audit = pd.read_csv(F1_DERIVED_DIR / "systematic_audit.csv")
    keys = ["season", "circuit", "driver", "real_pit_lap"]
    m = com.merge(dec[keys + ["tyre_age", "horizon"]], on=keys).merge(
        audit[keys + ["real_stop_neutralised"]], on=keys)
    m = m.dropna(subset=["committed_pit_lap"])
    m["ratio_one_lap"] = [ratio_one_lap(int(r.decision_lap), float(r.tyre_age), int(r.horizon))
                          for r in m.itertuples()]
    return pd.DataFrame({
        "series": "f1", "car_class": "", "race": m["season"].astype(str) + "_" + m["circuit"],
        "n_stops": m["n_stops"], "real_pit_lap": m["real_pit_lap"],
        "committed_pit_lap": m["committed_pit_lap"], "ratio_one_lap": m["ratio_one_lap"],
        "neutralised": m["real_stop_neutralised"].astype(bool),
    })


def endurance_rows() -> pd.DataFrame:
    com = pd.read_csv(DERIVED_DIR / "endurance" / "committed_strategy.csv")
    audit = pd.read_csv(DERIVED_DIR / "endurance" / "systematic_audit.csv")
    keys = ["series", "year", "event", "car_class", "car", "decision_lap", "real_pit_lap"]
    com["car"], audit["car"] = com["car"].astype(str), audit["car"].astype(str)
    m = com.merge(audit[keys + ["real_stop_neutralised"]], on=keys, how="left")
    m = m.dropna(subset=["committed_pit_lap"])
    rows = []
    cache: dict[tuple, pd.DataFrame] = {}
    for r in m.itertuples():
        key = (r.series, int(r.year), r.event, r.car_class)
        if key not in cache:
            cache[key] = EnduranceLoader(r.series).load_laps(int(r.year), r.event, r.car_class)
        laps = cache[key]
        car = laps[laps["car"].astype(str) == str(r.car)]
        at = car.loc[car["lap"] == r.decision_lap, "tyre_age"]
        if at.empty or not np.isfinite(at.iloc[0]):
            continue
        horizon = int(r.second_pit_lap) if pd.notna(r.second_pit_lap) else int(car["lap"].max())
        rows.append({
            "series": r.series, "car_class": r.car_class, "race": f"{r.year}_{r.event}",
            "n_stops": r.n_stops, "real_pit_lap": r.real_pit_lap,
            "committed_pit_lap": r.committed_pit_lap,
            "ratio_one_lap": ratio_one_lap(int(r.decision_lap), float(at.iloc[0]), horizon),
            "neutralised": bool(r.real_stop_neutralised) if pd.notna(r.real_stop_neutralised) else False,
        })
    return pd.DataFrame(rows)


def summarise(frame: pd.DataFrame) -> dict:
    rng = np.random.default_rng(BOOT_SEED)
    out = {}
    for (series, car_class), g in frame.groupby(["series", "car_class"]):
        g = g.assign(committed=g["committed_pit_lap"] - g["real_pit_lap"],
                     ratio_one=g["ratio_one_lap"] - g["real_pit_lap"])
        green = g[~g["neutralised"]]
        groups = {k: v for k, v in green.groupby("race")}
        keys = list(groups)
        draws = []
        for _ in range(BOOT_DRAWS):
            pick = pd.concat([groups[k] for k in rng.choice(keys, len(keys))])
            draws.append(float(pick["committed"].median()))
        out[f"{series}|{car_class}"] = {
            "n": int(len(g)),
            "committed_abs": float(g["committed"].abs().median()),
            "ratio_one_abs": float(g["ratio_one"].abs().median()),
            "ratio_one_median": float(g["ratio_one"].median()),
            "pct_neutralised": float(100 * g["neutralised"].mean()),
            "green_n": int(len(green)),
            "green_committed_median": float(green["committed"].median()),
            "green_committed_ci": [float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))],
            "green_committed_abs": float(green["committed"].abs().median()),
            "all_committed_median": float(g["committed"].median()),
        }
    return out


def report(s: dict) -> str:
    lines = ["# Reference rules for the committed audit", "",
             "Generated by `scripts/run_reference_rules.py`. Medians of lap gaps against the real stop,",
             "over the decisions the committed replay can make.", "",
             "| class | n | committed abs | ratio-one abs | ratio-one signed | stops under caution | "
             "green n | green committed signed [95%] | green committed abs |",
             "|---|---:|---:|---:|---:|---:|---:|---|---:|"]
    for k, g in s.items():
        lines.append(
            f"| {k} | {g['n']} | {g['committed_abs']:.0f} | {g['ratio_one_abs']:.0f} | "
            f"{g['ratio_one_median']:+.0f} | {g['pct_neutralised']:.0f}% | {g['green_n']} | "
            f"{g['green_committed_median']:+.1f} [{g['green_committed_ci'][0]:+.1f}, "
            f"{g['green_committed_ci'][1]:+.1f}] | {g['green_committed_abs']:.0f} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    frame = pd.concat([f1_rows(), endurance_rows()], ignore_index=True)
    s = summarise(frame)
    frame.to_csv(OUT_CSV, index=False)
    OUT_JSON.write_text(json.dumps(s, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    OUT_MD.write_text(report(s), encoding="utf-8")
    print(report(s))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
