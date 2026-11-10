"""Do the two rejected mechanisms stay rejected on the gap that is left?

Section "Testing the two candidate explanations" rejects an unmodelled undercut
(the cover-aware engine), and Section "A third explanation" rejects the
earliest undefendable undercut of Salminen (2026). Both were measured on the
first-run audit, whose median gap of about ten laps turned out to be mostly the
audit's question rather than the teams' choice. The gap that survives the
committed-strategy replay is the one in one-stop races, where the replay and the
first run coincide because the team's next stop is the flag.

So the honest retest is on those decisions only: the same per-decision outputs,
restricted to the one-stop first stops that the committed replay keeps. A
mechanism that is too weak for ten laps could still explain four.

Writes ``data/derived/f1/one_stop_retest_summary.json`` and
``reports/f1/one_stop_retest.md``.

    python scripts/run_one_stop_retest.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.ingestion.config import F1_DERIVED_DIR, F1_REPORTS_DIR  # noqa: E402

KEY = ["season", "circuit", "driver", "real_pit_lap"]
OUT_JSON = F1_DERIVED_DIR / "one_stop_retest_summary.json"
OUT_MD = F1_REPORTS_DIR / "one_stop_retest.md"
RULE_LABELS = {
    "position": "nearest car on track (published)",
    "thraves": "standalone time",
    "pi_window": "pit-window overlap",
    "d1": "nearest car ahead within one lap",
}


def one_stop() -> pd.DataFrame:
    committed = pd.read_csv(F1_DERIVED_DIR / "committed_strategy.csv")
    keep = (committed["n_stops"] == 1) & committed["committed_delta_laps"].notna()
    return committed.loc[keep, KEY + ["committed_delta_laps"]]


def build() -> dict:
    base = one_stop()
    out: dict = {
        "n_one_stop": int(len(base)),
        "committed_median": float(base["committed_delta_laps"].median()),
    }
    rivals = pd.read_csv(F1_DERIVED_DIR / "rival_selection.csv").merge(base, on=KEY)
    out["rules"] = {}
    for method, part in rivals.groupby("method"):
        better = int((part["closed"] > 0).sum())
        worse = int((part["closed"] < 0).sum())
        out["rules"][method] = {
            "n": int(len(part)),
            "closed_median": float(part["closed"].median()),
            "single_error": float(part["single_car_error"].median()),
            "cover_error": float(part["adversarial_error"].median()),
            "better": better,
            "worse": worse,
            "sign_p": float(binomtest(better, better + worse).pvalue),
        }
    defence = pd.read_csv(F1_DERIVED_DIR / "d1_defence.csv").merge(base, on=KEY)
    predicted = defence[defence["euu_error"].notna()]
    closer = int((predicted["euu_error"].abs() < predicted["single_car_error"].abs()).sum())
    further = int((predicted["euu_error"].abs() > predicted["single_car_error"].abs()).sum())
    # A predicted lap after the chequered flag means "no undefendable undercut in
    # this race", not an error of that many laps; count those apart.
    laps = {
        (season, circuit): int(
            pd.read_csv(F1_DERIVED_DIR / f"laps_{season}_{circuit}.csv", usecols=["LapNumber"])[
                "LapNumber"
            ].max()
        )
        for season, circuit in predicted[["season", "circuit"]].drop_duplicates().itertuples(index=False)
    }
    race_laps = [laps[(a, b)] for a, b in zip(predicted["season"], predicted["circuit"])]
    inside = predicted[predicted["euu_lap"].to_numpy() <= np.array(race_laps)]
    in_closer = int((inside["euu_error"].abs() < inside["single_car_error"].abs()).sum())
    in_further = int((inside["euu_error"].abs() > inside["single_car_error"].abs()).sum())
    rng = np.random.default_rng(20261110)
    races = inside[["season", "circuit"]].drop_duplicates().to_numpy()
    groups = {tuple(r): g for r, g in inside.groupby(["season", "circuit"])}
    diffs, euus = [], []
    for _ in range(4000):
        pick = races[rng.integers(0, len(races), len(races))]
        g = pd.concat([groups[tuple(r)] for r in pick])
        euus.append(g["euu_error"].median())
        diffs.append((g["euu_error"].abs() - g["single_car_error"].abs()).median())
    out["salminen_inside"] = {
        "after_flag": int(len(predicted) - len(inside)),
        "n": int(len(inside)),
        "races": int(len(races)),
        "euu_error": float(inside["euu_error"].median()),
        "euu_ci": [float(np.percentile(euus, 2.5)), float(np.percentile(euus, 97.5))],
        "single_error": float(inside["single_car_error"].median()),
        "abs_diff": float((inside["euu_error"].abs() - inside["single_car_error"].abs()).median()),
        "abs_diff_ci": [float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))],
        "closer": in_closer,
        "further": in_further,
        "sign_p": float(binomtest(in_closer, in_closer + in_further).pvalue),
    }
    out["salminen"] = {
        "n": int(len(defence)),
        "leaders": int((defence["role"] == "race leader").sum()),
        "predicted": int(len(predicted)),
        "euu_error": float(predicted["euu_error"].median()),
        "single_error": float(predicted["single_car_error"].median()),
        "closer": closer,
        "further": further,
    }
    return out


def report(s: dict) -> str:
    lines = [
        "<!-- GENERATED by scripts/run_one_stop_retest.py — do not edit by hand. -->",
        "",
        "# The rejected mechanisms, retested on the one-stop gap",
        "",
        f"{s['n_one_stop']} one-stop first stops kept by the committed replay; "
        f"median gap {s['committed_median']:+.0f} laps.",
        "",
        "## Cover-aware engine (unmodelled undercut)",
        "",
        "| rival rule | decisions | median laps closed | closer | further | sign test p |",
        "|---|---|---|---|---|---|",
    ]
    for method, r in s["rules"].items():
        lines.append(
            f"| {RULE_LABELS.get(method, method)} | {r['n']} | {r['closed_median']:+.0f} | "
            f"{r['better']} | {r['worse']} | {r['sign_p']:.4f} |"
        )
    d = s["salminen"]
    lines += [
        "",
        "## Earliest undefendable undercut (Salminen 2026)",
        "",
        f"{d['leaders']} of {d['n']} decisions belong to the race leader and carry no "
        f"prediction. On the {d['predicted']} that do, the median error is "
        f"{d['euu_error']:+.0f} laps against {d['single_error']:+.0f} for the "
        f"single-car optimiser; closer on {d['closer']}, further on {d['further']}.",
        "",
    ]
    i = s["salminen_inside"]
    lines += [
        f"On {i['after_flag']} of those {d['predicted']} the predicted lap falls after the "
        "chequered flag: the mechanism predicts no undefendable undercut in that race. "
        f"On the {i['n']} decisions ({i['races']} races) where it falls inside the race, "
        f"the median error is {i['euu_error']:+.1f} laps [{i['euu_ci'][0]:+.1f}, {i['euu_ci'][1]:+.1f}] "
        f"against {i['single_error']:+.0f} for the single-car optimiser; median difference in "
        f"absolute error {i['abs_diff']:+.1f} [{i['abs_diff_ci'][0]:+.1f}, {i['abs_diff_ci'][1]:+.1f}], "
        f"closer on {i['closer']}, further on {i['further']} (sign test p = {i['sign_p']:.4f}). "
        "This subset is selected by the mechanism's own prediction, so it is a description, "
        "not a test.",
        "",
    ]
    return "\n".join(lines)


def _json(stats: dict) -> str:
    def clean(v):
        if isinstance(v, dict):
            return {k: clean(x) for k, x in v.items()}
        return round(v, 6) if isinstance(v, float) else v
    return json.dumps(clean(stats), indent=1, sort_keys=True) + "\n"


def main() -> int:
    stats = build()
    OUT_JSON.write_text(_json(stats), encoding="utf-8")
    OUT_MD.write_text(report(stats), encoding="utf-8")
    print(report(stats))
    return 0


if __name__ == "__main__":
    sys.exit(main())
