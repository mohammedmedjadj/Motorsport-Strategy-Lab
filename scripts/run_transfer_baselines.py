"""Two comparisons Result 1 needs beyond leave-one-season-out.

Result 1 scores a circuit's slope on a season it was not fitted on, training on
every other season, earlier or later. That is not the question a team faces,
and a flat slope is a weak reference. For the Formula 1 circuits this asks:

- **Past only.** Each season predicted from the seasons before it, never after,
  the forward-chaining version a team could actually run. A season with no
  earlier season at that circuit is not scored.
- **Circuit against category.** The same held-out seasons predicted by one
  slope per compound common to the category: the median, over every *other*
  circuit, of that circuit's linear fit, with the median fuel slope. If the
  circuit-specific slope does not beat a slope that knows nothing about the
  circuit, the circuit is not what the slope carries.
- **Against the noise ceiling.** Each circuit's score is also reported as a
  share of what a perfectly stable slope could have scored there
  (``transfer_ceiling.csv``), the comparison that separates instability from
  a lack of signal.

A fourth check answers a worry about the frame rather than the predictor: the
traffic trim drops laps slower than a multiple of the driver's race median,
which truncates the response itself and could flatten late-stint slopes. The
linear slopes and leave-one-season-out scores are refitted with the multiple
at 1.05, 1.10 (the published value) and 1.20.

All of them use the linear model, so the comparisons are between predictors and
not between degrees, and the Result 1 within-stint R².

Writes ``data/derived/f1/transfer_baselines.csv``,
``transfer_baselines_summary.json`` and ``reports/f1/transfer_baselines.md``.

    python scripts/run_transfer_baselines.py
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
sys.path.insert(0, str(REPO / "scripts"))

from src.degradation.dataset import (  # noqa: E402
    build_modelling_frame,
    circuits_with_laps,
    load_circuit_laps,
)
from src.degradation.model import fit_circuit, predict_shape  # noqa: E402
from run_transfer_ceiling import UNMEASURABLE  # noqa: E402
from src.ingestion.config import F1_DERIVED_DIR, PRE_ERA_SEASONS, REPORTS_DIR  # noqa: E402

CEILING = F1_DERIVED_DIR / "transfer_ceiling.csv"
OUT_CSV = F1_DERIVED_DIR / "transfer_baselines.csv"
OUT_JSON = F1_DERIVED_DIR / "transfer_baselines_summary.json"
OUT_MD = REPORTS_DIR / "f1" / "transfer_baselines.md"
BOOT_SEED = 20261108
BOOT_DRAWS = 10_000


def _demean(values: pd.Series, groups: pd.Series) -> pd.Series:
    return values - values.groupby(groups).transform("mean")


def _r2(test: pd.DataFrame, shape: pd.Series) -> float | None:
    valid = shape.notna()
    if not valid.any():
        return None
    actual = _demean(test.loc[valid, "lap_time_s"], test.loc[valid, "stint_id"])
    predicted = _demean(shape[valid], test.loc[valid, "stint_id"])
    ss = float((actual**2).sum())
    return 1.0 - float(((actual - predicted) ** 2).sum()) / ss if ss > 0 else None


def build() -> pd.DataFrame:
    frames = {}
    for circuit in circuits_with_laps(seasons=PRE_ERA_SEASONS):
        laps = load_circuit_laps(circuit, seasons=PRE_ERA_SEASONS)
        frame, _ = build_modelling_frame(laps, circuit)
        if frame["race"].nunique() >= 2:
            frames[circuit] = frame
    # Each circuit's linear fit on all its seasons, for the category slope.
    fits = {c: fit_circuit(f, c, degree=1) for c, f in frames.items()}

    rows = []
    for circuit, frame in frames.items():
        others = [f for c, f in fits.items() if c != circuit]
        fuel = float(np.median([f.fuel_slope.value for f in others]))
        category = {
            comp: float(np.median([f.deg_coefs[comp][0].value for f in others if comp in f.deg_coefs]))
            for comp in ("SOFT", "MEDIUM", "HARD")
        }
        loro, past, pooled = [], [], []
        seasons = sorted(frame["season"].unique())
        for race in sorted(frame["race"].unique()):
            test = frame[frame["race"] == race]
            season = int(test["season"].iloc[0])
            train = frame[frame["race"] != race]
            score = _r2(test, predict_shape(fit_circuit(train, circuit, degree=1), test))
            if score is not None:
                loro.append(score)
            earlier = frame[frame["season"] < season]
            if season != seasons[0] and not earlier.empty:
                score = _r2(test, predict_shape(fit_circuit(earlier, circuit, degree=1), test))
                if score is not None:
                    past.append(score)
            slope = test["Compound"].map(category)
            shape = fuel * test["LapNumber"] + slope * test["TyreLife"]
            score = _r2(test, shape)
            if score is not None:
                pooled.append(score)
        rows.append({
            "circuit": circuit,
            "seasons": len(seasons),
            "r2_loro": float(np.mean(loro)) if loro else np.nan,
            "r2_past_only": float(np.mean(past)) if past else np.nan,
            "r2_category": float(np.mean(pooled)) if pooled else np.nan,
        })
    out = pd.DataFrame(rows)
    ceiling = pd.read_csv(CEILING)[["circuit", "ceiling_mean", "sane", "verdict"]]
    out = out.merge(ceiling, on="circuit", how="left")
    out["share_of_ceiling"] = out["r2_loro"] / out["ceiling_mean"]
    out["category_share_of_ceiling"] = out["r2_category"] / out["ceiling_mean"]
    return out


TRIMS = (1.05, 1.10, 1.20)


def trim_sensitivity() -> dict:
    import src.degradation.dataset as dataset

    published = dataset.TRAFFIC_TRIM_FACTOR
    slopes: dict[float, dict] = {}
    scores: dict[float, list] = {}
    try:
        for trim in TRIMS:
            dataset.TRAFFIC_TRIM_FACTOR = trim
            slopes[trim], scores[trim] = {}, []
            for circuit in circuits_with_laps(seasons=PRE_ERA_SEASONS):
                laps = load_circuit_laps(circuit, seasons=PRE_ERA_SEASONS)
                frame, _ = build_modelling_frame(laps, circuit)
                if frame["race"].nunique() < 2:
                    continue
                fit = fit_circuit(frame, circuit, degree=1)
                for comp, coefs in fit.deg_coefs.items():
                    slopes[trim][(circuit, comp)] = coefs[0].value
                folds = []
                for race in sorted(frame["race"].unique()):
                    test = frame[frame["race"] == race]
                    train = frame[frame["race"] != race]
                    score = _r2(test, predict_shape(fit_circuit(train, circuit, degree=1), test))
                    if score is not None:
                        folds.append(score)
                scores[trim].append(float(np.mean(folds)))
    finally:
        dataset.TRAFFIC_TRIM_FACTOR = published
    out = {}
    for trim in TRIMS:
        common = [k for k in slopes[published] if k in slopes[trim] and slopes[published][k] > 0]
        change = [slopes[trim][k] / slopes[published][k] - 1 for k in common]
        out[f"{trim:.2f}"] = {
            "median_slope_change": float(np.median(change)),
            "median_abs_slope_change": float(np.median(np.abs(change))),
            "share_moved_10pct": float(np.mean(np.abs(change) > 0.10)),
            "median_loro": float(np.median(scores[trim])),
        }
    return out


def _median_ci(x: np.ndarray, rng) -> tuple[float, float]:
    draws = np.median(rng.choice(x, size=(BOOT_DRAWS, len(x)), replace=True), axis=1)
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return float(lo), float(hi)


def summarise(frame: pd.DataFrame) -> dict:
    rng = np.random.default_rng(BOOT_SEED)
    sane = frame[frame["sane"].astype(bool)].copy()
    out = {"n_circuits": int(len(sane)), "n_excluded": int(len(frame) - len(sane))}
    for name, col in (("past", "r2_past_only"), ("category", "r2_category")):
        part = sane.dropna(subset=[col, "r2_loro"])
        diff = (part[col] - part["r2_loro"]).to_numpy()
        lo, hi = _median_ci(diff, rng)
        out[name] = {
            "n": int(len(part)),
            "median": float(part[col].median()),
            "median_loro": float(part["r2_loro"].median()),
            "median_diff": float(np.median(diff)), "ci_low": lo, "ci_high": hi,
            "n_better": int((diff > 0).sum()), "n_worse": int((diff < 0).sum()),
        }
    measurable = sane[sane["ceiling_mean"] > UNMEASURABLE]
    out["trim"] = trim_sensitivity()
    out["ceiling"] = {
        "threshold": UNMEASURABLE,
        "n": int(len(measurable)),
        "median_share": float(measurable["share_of_ceiling"].median()),
        "median_share_category": float(measurable["category_share_of_ceiling"].median()),
        "n_above_half_category": int((measurable["category_share_of_ceiling"] >= 0.5).sum()),
        "category_minus_own": float(np.median(measurable["r2_category"] - measurable["r2_loro"])),
        "category_minus_own_ci": list(_median_ci(
            (measurable["r2_category"] - measurable["r2_loro"]).to_numpy(), rng)),
        "n_category_better": int((measurable["r2_category"] > measurable["r2_loro"]).sum()),
        "n_category_worse": int((measurable["r2_category"] < measurable["r2_loro"]).sum()),
        "n_above_half": int((measurable["share_of_ceiling"] >= 0.5).sum()),
    }
    return out


def report(frame: pd.DataFrame, s: dict) -> str:
    p, c, k = s["past"], s["category"], s["ceiling"]
    lines = [
        "<!-- GENERATED by scripts/run_transfer_baselines.py — do not edit by hand. -->",
        "",
        "# Result 1 against past-only prediction, a category slope and the ceiling",
        "",
        f"{s['n_circuits']} Formula 1 circuits (degenerate fits excluded, as in "
        "Result 1), linear model, within-stint R².",
        "",
        f"- Past only: median {p['median']:.3f} against {p['median_loro']:.3f} for "
        f"leave-one-season-out on the same circuits; median difference "
        f"{p['median_diff']:+.3f} [{p['ci_low']:+.3f}, {p['ci_high']:+.3f}], "
        f"better at {p['n_better']}, worse at {p['n_worse']}.",
        f"- Category slope: median {c['median']:.3f} against {c['median_loro']:.3f}; "
        f"median difference {c['median_diff']:+.3f} [{c['ci_low']:+.3f}, "
        f"{c['ci_high']:+.3f}], better at {c['n_better']}, worse at {c['n_worse']}.",
        f"- Share of the noise ceiling, at the {k['n']} circuits where it exceeds "
        f"{k['threshold']}: median {k['median_share']:.2f}; {k['n_above_half']} reach half. "
        f"The category slope on the same circuits: median {k['median_share_category']:.2f}; "
        f"{k['n_above_half_category']} reach half. There the category slope minus "
        f"the circuit's own: median {k['category_minus_own']:+.3f} "
        f"[{k['category_minus_own_ci'][0]:+.3f}, {k['category_minus_own_ci'][1]:+.3f}], "
        f"better at {k['n_category_better']}, worse at {k['n_category_worse']}.",
        "- Traffic trim: " + "; ".join(
            f"at {t}, slopes move by a median of {100 * v['median_slope_change']:+.1f}% "
            f"(absolute {100 * v['median_abs_slope_change']:.1f}%, "
            f"{100 * v['share_moved_10pct']:.0f}% move by over a tenth) "
            f"and the median score is {v['median_loro']:.3f}"
            for t, v in s["trim"].items()
        ) + ".",
        "",
        "| circuit | Result 1 verdict | seasons | R², other seasons | R², past only | R², category slope | share of ceiling |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in frame.sort_values("r2_loro", ascending=False).itertuples():
        lines.append(
            f"| {r.circuit} | {r.verdict} | {r.seasons} | {r.r2_loro:.3f} | "
            f"{r.r2_past_only:.3f} | {r.r2_category:.3f} | {r.share_of_ceiling:.2f} |"
        )
    lines.append("")
    return "\n".join(lines)


def _json(stats: dict) -> str:
    def clean(v):
        if isinstance(v, dict):
            return {k: clean(x) for k, x in v.items()}
        return round(v, 6) if isinstance(v, float) else v
    return json.dumps(clean(stats), indent=1, sort_keys=True) + "\n"


def main() -> int:
    warnings.filterwarnings("ignore")
    frame = build()
    stats = summarise(frame)
    frame.to_csv(OUT_CSV, index=False)
    OUT_JSON.write_text(_json(stats), encoding="utf-8")
    OUT_MD.write_text(report(frame, stats), encoding="utf-8")
    print(report(frame, stats))
    return 0


if __name__ == "__main__":
    sys.exit(main())
