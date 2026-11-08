"""The noise ceiling for the endurance circuit-classes.

Result 1 counts how many endurance circuit-classes clear a within-stint R² of
0.2, and reads three things from the endurance scores: that Balance of
Performance is not needed for the instability (the near-specification ELMS
LMP2 field fails too), that GT3 classes transfer better than prototypes, and
the argument against a model-based reading. For Formula 1 the paper showed that
a low score can be a lack of signal rather than a moving slope, using a noise
ceiling. Until the endurance classes have the same ceiling, those three
readings rest on the raw threshold. This builds it, with the same construction
as ``run_transfer_ceiling.py``:

- **Clean signal.** Inside a stint, the pooled net slope over all seasons of the
  circuit-class times tyre age: one slope for every season, stable by
  construction. Car-driver levels do not matter, because the score demeans
  every stint.
- **Noise.** Residuals from a fit that gives every season its own slope (unit
  fixed effects plus that season's slope), resampled in whole car-driver stints
  so their within-stint correlation is kept.
- **The protocol unchanged.** ``leave_one_race_out_endurance`` on the synthetic
  seasons, averaged over replicates.

Verdicts use the Formula 1 thresholds. The GT3-prototype comparison is then
repeated on the share of the ceiling each circuit-class reaches, which is the
comparison that separates "transfers better" from "carries more signal".

Writes ``data/derived/endurance/endurance_ceiling.csv``,
``endurance_ceiling_summary.json`` and
``reports/cross_series/endurance_ceiling.md``.

    python scripts/run_endurance_ceiling.py
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

from run_endurance_models import _frames  # noqa: E402
from run_formal_tests import GT3_CLASSES  # noqa: E402
from run_transfer_ceiling import STABLE_GAP, UNMEASURABLE, UNSTABLE_GAP  # noqa: E402
from src.data.endurance_scope import ENDURANCE_SCOPE  # noqa: E402
from src.degradation.endurance_validation import (  # noqa: E402
    _fit_net_slope,
    leave_one_race_out_endurance,
    mean_r2,
)
from src.ingestion.config import ENDURANCE_DERIVED_DIR, REPORTS_DIR  # noqa: E402

LORO = ENDURANCE_DERIVED_DIR / "endurance_degradation_loro.csv"
OUT_CSV = ENDURANCE_DERIVED_DIR / "endurance_ceiling.csv"
OUT_JSON = ENDURANCE_DERIVED_DIR / "endurance_ceiling_summary.json"
OUT_MD = REPORTS_DIR / "cross_series" / "endurance_ceiling.md"
REPLICATES = 20
SEED = 20261108
THRESHOLD = 0.2
BOOT_DRAWS = 10_000


def _season_residuals(frame: pd.DataFrame) -> np.ndarray:
    """Residuals from unit fixed effects plus this season's own net slope."""
    fe = pd.get_dummies(frame["unit"]).to_numpy(dtype=float)
    age = frame["tyre_age"].to_numpy(dtype=float)
    y = frame["lap_time_s"].to_numpy(dtype=float)
    design = np.hstack([fe, age[:, None]])
    beta, *_ = np.linalg.lstsq(design, y, rcond=None)
    return y - design @ beta


def _synthetic(frames: dict, slope: float, rng) -> dict:
    out = {}
    for key, frame in frames.items():
        frame = frame.reset_index(drop=True)
        resid = _season_residuals(frame)
        stint = frame["car"].astype(str) + "|" + frame["driver_stint"].astype(str)
        positions = list(frame.groupby(stint.values).indices.values())
        blocks = [resid[np.asarray(p)] for p in positions]
        drawn = np.empty_like(resid)
        for p in positions:
            p = np.asarray(p)
            donor = blocks[rng.integers(len(blocks))]
            take = (rng.integers(0, len(donor), size=len(p)) if len(donor) < len(p)
                    else np.arange(len(p)))
            drawn[p] = donor[take]
        syn = frame.copy()
        syn["lap_time_s"] = slope * frame["tyre_age"].to_numpy(dtype=float) + drawn
        out[key] = syn
    return out


def verdict(ceiling: float, measured: float) -> str:
    if abs(ceiling) >= 1 or abs(measured) >= 1:
        return "degenerate fit, excluded"
    if ceiling < UNMEASURABLE:
        return "no signal to recover"
    gap = ceiling - measured
    if gap < STABLE_GAP:
        return "slope stable"
    if gap > UNSTABLE_GAP:
        return "slope unstable"
    return "borderline"


def build() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    loro = pd.read_csv(LORO)
    measured = loro[loro["held_out_season"].astype(str) == "MEAN"].set_index(
        ["series", "event", "car_class"])["r2_within"]
    rows = []
    for series, circuits in ENDURANCE_SCOPE.items():
        for cs in circuits:
            key = (series, cs.event, cs.car_class)
            if key not in measured.index or not np.isfinite(measured[key]):
                continue
            frames = _frames(series, cs.event, cs.car_class, cs.seasons)
            if len(frames) < 2:
                continue
            slope = _fit_net_slope(frames).value
            scores = []
            for _ in range(REPLICATES):
                scores.append(mean_r2(leave_one_race_out_endurance(_synthetic(frames, slope, rng))))
            ceiling = float(np.mean(scores))
            m = float(measured[key])
            rows.append({
                "series": series, "event": cs.event, "car_class": cs.car_class,
                "gt3": cs.car_class in GT3_CLASSES, "seasons": len(frames),
                "measured_r2": m, "ceiling_mean": ceiling, "gap": ceiling - m,
                "share_of_ceiling": m / ceiling if ceiling > UNMEASURABLE else np.nan,
                "verdict": verdict(ceiling, m),
            })
            print(f"  {series:5s} {cs.event[:28]:28s} {cs.car_class:12s} ceiling {ceiling:+.3f}  measured {m:+.3f}", flush=True)
    return pd.DataFrame(rows)


def _boot_diff(a: np.ndarray, b: np.ndarray, rng) -> tuple[float, float]:
    draws = [rng.choice(a, len(a)).mean() - rng.choice(b, len(b)).mean() for _ in range(BOOT_DRAWS)]
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return float(lo), float(hi)


def summarise(frame: pd.DataFrame) -> dict:
    rng = np.random.default_rng(SEED)
    sane = frame[frame["verdict"] != "degenerate fit, excluded"]
    out = {
        "n": int(len(sane)),
        "n_excluded": int(len(frame) - len(sane)),
        "n_ceiling_below_threshold": int((sane["ceiling_mean"] < THRESHOLD).sum()),
        "verdicts": {k: int(v) for k, v in sane["verdict"].value_counts().items()},
    }
    for name, part in (("gt3", sane[sane["gt3"]]), ("proto", sane[~sane["gt3"]])):
        out[name] = {
            "n": int(len(part)),
            "mean_ceiling": float(part["ceiling_mean"].mean()),
            "mean_measured": float(part["measured_r2"].mean()),
            "verdicts": {k: int(v) for k, v in part["verdict"].value_counts().items()},
        }
    measurable = sane.dropna(subset=["share_of_ceiling"])
    g = measurable[measurable["gt3"]]["share_of_ceiling"].to_numpy()
    p = measurable[~measurable["gt3"]]["share_of_ceiling"].to_numpy()
    out["share"] = {"n_gt3": int(len(g)), "n_proto": int(len(p))}
    if len(g) and len(p):
        lo, hi = _boot_diff(g, p, rng)
        out["share"].update({"gt3_mean": float(g.mean()), "proto_mean": float(p.mean()),
                             "diff": float(g.mean() - p.mean()), "ci": [lo, hi]})
    lo, hi = _boot_diff(sane[sane["gt3"]]["ceiling_mean"].to_numpy(),
                        sane[~sane["gt3"]]["ceiling_mean"].to_numpy(), rng)
    out["ceiling_diff"] = {
        "diff": float(sane[sane["gt3"]]["ceiling_mean"].mean() - sane[~sane["gt3"]]["ceiling_mean"].mean()),
        "ci": [lo, hi]}
    lmp2 = sane[(sane["series"] == "elms") & (sane["car_class"] == "LMP2")]
    out["elms_lmp2"] = {k: int(v) for k, v in lmp2["verdict"].value_counts().items()}
    return out


def report(frame: pd.DataFrame, s: dict) -> str:
    lines = [
        "<!-- GENERATED by scripts/run_endurance_ceiling.py — do not edit by hand. -->",
        "",
        "# The noise ceiling for the endurance circuit-classes",
        "",
        f"{s['n']} circuit-classes ({s['n_excluded']} degenerate excluded). With a slope "
        f"stable by construction, {s['n_ceiling_below_threshold']} of them could not "
        f"reach a within-stint R² of {THRESHOLD}.",
        "",
        "Verdicts: " + ", ".join(f"{k} {v}" for k, v in s["verdicts"].items()) + ".",
        "",
        f"GT3 ({s['gt3']['n']}): mean ceiling {s['gt3']['mean_ceiling']:+.3f}, mean "
        f"measured {s['gt3']['mean_measured']:+.3f}. Prototype ({s['proto']['n']}): "
        f"mean ceiling {s['proto']['mean_ceiling']:+.3f}, mean measured "
        f"{s['proto']['mean_measured']:+.3f}. Ceiling difference GT3 minus prototype "
        f"{s['ceiling_diff']['diff']:+.3f} [{s['ceiling_diff']['ci'][0]:+.3f}, "
        f"{s['ceiling_diff']['ci'][1]:+.3f}].",
        "",
    ]
    sh = s["share"]
    if "diff" in sh:
        lines += [
            f"Share of the ceiling where it exceeds {UNMEASURABLE}: GT3 {sh['gt3_mean']:.2f} "
            f"({sh['n_gt3']}), prototype {sh['proto_mean']:.2f} ({sh['n_proto']}), "
            f"difference {sh['diff']:+.2f} [{sh['ci'][0]:+.2f}, {sh['ci'][1]:+.2f}].",
            "",
        ]
    lines += [f"ELMS LMP2 verdicts: {s['elms_lmp2']}.", "",
              "| series | event | class | seasons | measured | ceiling | verdict |",
              "|---|---|---|---|---|---|---|"]
    for r in frame.sort_values("ceiling_mean", ascending=False).itertuples():
        lines.append(f"| {r.series} | {r.event} | {r.car_class} | {r.seasons} | "
                     f"{r.measured_r2:+.3f} | {r.ceiling_mean:+.3f} | {r.verdict} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    warnings.filterwarnings("ignore")
    frame = build()
    s = summarise(frame)
    frame.to_csv(OUT_CSV, index=False)
    clean = json.loads(json.dumps(s), parse_float=lambda x: round(float(x), 6))
    OUT_JSON.write_text(json.dumps(clean, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    OUT_MD.write_text(report(frame, s), encoding="utf-8")
    print(report(frame, s)[:1500])
    return 0


if __name__ == "__main__":
    sys.exit(main())
