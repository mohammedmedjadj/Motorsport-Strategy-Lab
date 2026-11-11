"""Does a compound's baseline pace change the reading of the implied ratio?

The degradation model (Equation 1) gives each compound its own wear slope but
no baseline of its own: a soft and a hard tyre at age zero are assumed equally
fast once the driver-race intercept is removed. Felipe Carrasco Heine pointed
this out (11 November 2026): baseline differences between compounds matter
whenever two strategies use different compounds.

This script refits every linear circuit behind the implied-ratio decisions
with one intercept per compound (driver-race fixed effects, lap number,
compound x tyre age, compound dummies) and asks three things:

1. Do the slopes refitted with offsets order the compounds by hardness, where
   the published slopes did no better than chance?
2. Which way do the offsets point (is the harder compound slower when new)?
3. With offsets in the time-optimal single stop, where does the planner's lap
   fall relative to the team's? A slower new compound makes it optimal to stay
   out *longer*, so offsets can only explain the teams' shorter first stints if
   the harder compound is *faster* when new.

Same decisions as the implied ratio: lookback five, top five, two different
compounds, linear circuits. Intervals resample races.

Writes ``data/derived/f1/compound_offsets_summary.json`` and
``reports/f1/compound_offsets.md``.

    python scripts/run_compound_offsets.py
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

from src.degradation.dataset import build_modelling_frame, load_circuit_laps  # noqa: E402
from src.ingestion.config import F1_DERIVED_DIR, PRE_ERA_SEASONS, REPORTS_DIR  # noqa: E402

DECISIONS = F1_DERIVED_DIR / "audit_design_checks.csv"
OUT_JSON = F1_DERIVED_DIR / "compound_offsets_summary.json"
OUT_MD = REPORTS_DIR / "f1" / "compound_offsets.md"
HARDNESS = {"SOFT": 0, "MEDIUM": 1, "HARD": 2}
BOOT_SEED = 20261111
BOOT_DRAWS = 4_000

warnings.filterwarnings("ignore", message=".*not ingested yet.*")


def _fit(frame: pd.DataFrame, offsets: bool) -> tuple[dict, dict]:
    """Linear slopes (and compound offsets) by within-driver-race OLS."""
    compounds = sorted(frame["Compound"].unique())
    cols, names = [frame["LapNumber"].to_numpy(float)], ["lap"]
    for c in compounds:
        cols.append((frame["Compound"] == c).to_numpy(float) * frame["TyreLife"].to_numpy(float))
        names.append(f"slope::{c}")
    if offsets:
        for c in compounds[1:]:
            cols.append((frame["Compound"] == c).to_numpy(float))
            names.append(f"offset::{c}")
    X = pd.DataFrame(np.column_stack(cols))
    g = frame["driver_race"].to_numpy()
    y = frame["lap_time_s"].to_numpy(float)
    Xd = (X - X.groupby(g).transform("mean")).to_numpy()
    yd = y - pd.Series(y).groupby(g).transform("mean").to_numpy()
    beta = np.linalg.lstsq(Xd, yd, rcond=None)[0]
    slopes = {n.split("::")[1]: float(b) for n, b in zip(names, beta) if n.startswith("slope::")}
    off = {compounds[0]: 0.0}
    off.update({n.split("::")[1]: float(b) for n, b in zip(names, beta) if n.startswith("offset::")})
    return slopes, off


def _best_k(a0: float, w: int, b_old: float, b_new: float, d_old: float, d_new: float) -> int:
    ks = np.arange(1, w)
    old = ks * d_old + b_old * (ks * a0 + ks * (ks + 1) / 2)
    rest = w - ks
    new = rest * d_new + b_new * rest * (rest + 1) / 2
    return int(ks[np.argmin(old + new)])


def decisions() -> pd.DataFrame:
    d = pd.read_csv(DECISIONS)
    d = d[(d["lookback"] == 5) & d["top"]]
    d = d.dropna(subset=["implied_ratio", "fitted_ratio"])
    d = d[d["ratio_class"] != "same compound"].copy()
    d["direction"] = np.where(d["target"].map(HARDNESS) > d["compound"].map(HARDNESS),
                              "to harder", "to softer")
    d["race"] = d["season"].astype(str) + "_" + d["circuit"]
    return d


def _race_ci(part: pd.DataFrame, column: str, rng) -> list[float]:
    groups = {k: g[column].to_numpy() for k, g in part.groupby("race")}
    keys = list(groups)
    reps = [np.median(np.concatenate([groups[keys[i]] for i in rng.choice(len(keys), len(keys))]))
            for _ in range(BOOT_DRAWS)]
    return [float(np.percentile(reps, 2.5)), float(np.percentile(reps, 97.5))]


def main() -> int:
    d = decisions()
    fits = {}
    for circuit in sorted(d["circuit"].unique()):
        frame, _ = build_modelling_frame(load_circuit_laps(circuit, seasons=PRE_ERA_SEASONS), circuit)
        fits[circuit] = {"plain": _fit(frame, offsets=False), "offsets": _fit(frame, offsets=True)}
    rows = []
    for r in d.itertuples():
        sp, _ = fits[r.circuit]["plain"]
        so, oo = fits[r.circuit]["offsets"]
        k_real = r.real_pit_lap - r.decision_lap
        w = r.horizon - r.decision_lap
        rows.append({
            "race": r.race, "direction": r.direction,
            "fitted_plain": sp[r.target] / sp[r.compound],
            "fitted_offsets": so[r.target] / so[r.compound]
            if so[r.compound] > 0 and so[r.target] > 0 else np.nan,
            "offset_gap": oo[r.target] - oo[r.compound],
            "gap_plain": _best_k(r.tyre_age, w, sp[r.compound], sp[r.target], 0, 0) - k_real,
            "gap_offsets": _best_k(r.tyre_age, w, max(so[r.compound], 1e-6), max(so[r.target], 1e-6),
                                   oo[r.compound], oo[r.target]) - k_real,
        })
    t = pd.DataFrame(rows)
    rng = np.random.default_rng(BOOT_SEED)
    out = {"n": int(len(t)), "circuits": int(d["circuit"].nunique()), "directions": {}}
    expect_below = t["direction"] == "to harder"
    for col in ("fitted_plain", "fitted_offsets"):
        v = t[col]
        side = np.where(expect_below, v < 1, v > 1)
        out[f"{col}_expected_side"] = float(np.mean(side[v.notna()]))
    for label, part in t.groupby("direction"):
        out["directions"][label] = {
            "n": int(len(part)),
            "fitted_offsets": float(part["fitted_offsets"].median()),
            "offset_gap": float(part["offset_gap"].median()),
            "offset_gap_ci": _race_ci(part, "offset_gap", rng),
            "gap_plain": float(part["gap_plain"].median()),
            "gap_offsets": float(part["gap_offsets"].median()),
            "gap_offsets_ci": _race_ci(part, "gap_offsets", rng),
        }
    out["gap_plain"] = float(t["gap_plain"].median())
    out["gap_offsets"] = float(t["gap_offsets"].median())
    out["gap_offsets_ci"] = _race_ci(t, "gap_offsets", rng)

    def clean(v):
        if isinstance(v, dict):
            return {k: clean(x) for k, x in v.items()}
        if isinstance(v, list):
            return [clean(x) for x in v]
        return round(v, 6) if isinstance(v, float) else v

    OUT_JSON.write_text(json.dumps(clean(out), indent=1, sort_keys=True) + "\n", encoding="utf-8")
    h, s = out["directions"]["to harder"], out["directions"]["to softer"]
    md = "\n".join([
        "# Compound baseline offsets and the implied ratio", "",
        "Generated by `scripts/run_compound_offsets.py`.", "",
        f"- {out['n']} decisions at {out['circuits']} linear circuits.",
        f"- Fitted ratio on the side of one hardness predicts: "
        f"{100 * out['fitted_plain_expected_side']:.0f}% with the published model, "
        f"{100 * out['fitted_offsets_expected_side']:.0f}% with compound offsets.",
        f"- New compound's baseline minus old compound's, to a harder compound: "
        f"{h['offset_gap']:+.3f} s [{h['offset_gap_ci'][0]:+.3f}, {h['offset_gap_ci'][1]:+.3f}]; "
        f"to a softer one: {s['offset_gap']:+.3f} s [{s['offset_gap_ci'][0]:+.3f}, "
        f"{s['offset_gap_ci'][1]:+.3f}].",
        f"- Time-optimal single stop minus the team's lap: {out['gap_plain']:+.1f} laps without "
        f"offsets, {out['gap_offsets']:+.1f} [{out['gap_offsets_ci'][0]:+.1f}, "
        f"{out['gap_offsets_ci'][1]:+.1f}] with them; to a harder compound "
        f"{h['gap_plain']:+.1f} -> {h['gap_offsets']:+.1f}, to a softer one "
        f"{s['gap_plain']:+.1f} -> {s['gap_offsets']:+.1f}.", ""])
    OUT_MD.write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
