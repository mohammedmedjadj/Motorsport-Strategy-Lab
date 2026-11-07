"""Does Friday's long run predict Sunday's degradation better than last season?

Result 1 asks a slope fitted on other seasons of a circuit to predict the season
it was not shown, and it mostly fails. A team does not have to rely on other
seasons: on Friday every car runs race-fuel long runs on the weekend's own
tyres, on the weekend's own asphalt. If degradation moves from season to season,
the obvious repair is to measure it that weekend, and this script tests whether
that repair works.

For every race from 2023 to 2025 with practice laps:

- **Friday.** Long runs from the second practice session (the only practice
  session on a sprint weekend) are cut to stints of at least ``MIN_LAPS`` timed
  laps after dropping the out-lap, the in-lap and any lap more than
  ``TRIM`` above the stint median (cool-down and traffic laps). One slope per
  compound is fitted on lap time against tyre age with a stint fixed effect.
  Inside a stint, tyre age and fuel burn advance together on Friday as on
  Sunday, so this slope is the same quantity the race model predicts inside a
  stint: degradation net of the fuel the car burns, and no fuel correction is
  needed to compare them.
- **Other seasons.** The Result 1 prediction: the linear model fitted on every
  other season of that circuit.
- **Friday, corrected.** Friday long runs turn out to degrade faster than the
  race does on the same compound, so the Friday slope is also scored after
  subtracting its median gap to Sunday, learned on every other circuit.
- **Both.** The average of the other-seasons shape and the corrected Friday
  shape, the simplest combination and one that needs no tuning on the held-out
  race.

All three are scored with the Result 1 within-stint R² on the same race laps:
those on a compound that both Friday and the other seasons have a slope for.

Writes ``data/derived/f1/practice_long_runs.csv``, ``practice_long_runs_summary.json`` and
``reports/f1/practice_long_runs.md``.

    python scripts/run_practice_long_runs.py
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.degradation.dataset import build_modelling_frame, load_circuit_laps  # noqa: E402
from src.degradation.model import fit_circuit, predict_shape  # noqa: E402
from src.ingestion.config import F1_DERIVED_DIR, PRE_ERA_SEASONS, REPORTS_DIR  # noqa: E402

PRACTICE = F1_DERIVED_DIR / "practice_laps.csv"
OUT_CSV = F1_DERIVED_DIR / "practice_long_runs.csv"
OUT_SUMMARY = F1_DERIVED_DIR / "practice_long_runs_summary.json"
OUT_MD = REPORTS_DIR / "f1" / "practice_long_runs.md"

MIN_LAPS = 6
#: A compound's Friday slope is used only when at least this many cars ran a
#: long run on it; one car's run is one driver's fuel and engine programme.
MIN_RUNS = 3
TRIM = 1.03
DRY = ("SOFT", "MEDIUM", "HARD")
BOOT_SEED = 20261107
BOOT_DRAWS = 10_000


def long_run_slopes(practice: pd.DataFrame) -> dict[str, tuple[float, int]]:
    """Per compound: the pooled within-stint slope and the number of long runs."""
    laps = practice[practice["compound"].isin(DRY) & practice["lap_time_s"].notna()]
    laps = laps[~laps["is_pit_out_lap"]].copy()
    laps["stint_id"] = laps["driver_number"].astype(str) + "_" + laps["stint"].astype(str)
    # The last timed lap of a stint is the in-lap.
    last = laps.groupby("stint_id")["lap_number"].transform("max")
    laps = laps[laps["lap_number"] < last]
    median = laps.groupby("stint_id")["lap_time_s"].transform("median")
    laps = laps[laps["lap_time_s"] <= TRIM * median]
    size = laps.groupby("stint_id")["lap_time_s"].transform("size")
    laps = laps[size >= MIN_LAPS]
    out = {}
    for compound, part in laps.groupby("compound"):
        x = part["tyre_age"] - part.groupby("stint_id")["tyre_age"].transform("mean")
        y = part["lap_time_s"] - part.groupby("stint_id")["lap_time_s"].transform("mean")
        if float((x**2).sum()) > 0 and part["stint_id"].nunique() >= MIN_RUNS:
            out[compound] = (float((x * y).sum() / (x**2).sum()), int(part["stint_id"].nunique()))
    return out


def race_slopes(test: pd.DataFrame) -> dict[str, float]:
    """The slope each compound actually showed inside the race's stints."""
    out = {}
    for compound, part in test.groupby("Compound"):
        x = part["TyreLife"] - part.groupby("stint_id")["TyreLife"].transform("mean")
        y = part["lap_time_s"] - part.groupby("stint_id")["lap_time_s"].transform("mean")
        if float((x**2).sum()) > 0:
            out[compound] = float((x * y).sum() / (x**2).sum())
    return out


def _demean(values: pd.Series, stints: pd.Series) -> pd.Series:
    return values - values.groupby(stints).transform("mean")


def _r2(actual: pd.Series, shape: pd.Series, stints: pd.Series) -> float:
    a = _demean(actual, stints)
    p = _demean(shape, stints)
    ss_tot = float((a**2).sum())
    return 1.0 - float(((a - p) ** 2).sum()) / ss_tot if ss_tot > 0 else float("nan")


def score_race(
    frame: pd.DataFrame, circuit: str, season: int, friday: dict, offset: float
) -> dict | None:
    race = f"{season}_{circuit}"
    test = frame[frame["race"] == race]
    train = frame[frame["race"] != race]
    if test.empty or train.empty:
        return None
    prior = predict_shape(fit_circuit(train, circuit, degree=1), test)
    friday_slope = test["Compound"].map({c: s for c, (s, _) in friday.items()})
    keep = prior.notna() & friday_slope.notna()
    if keep.sum() == 0:
        return None
    test = test[keep]
    stints = test["stint_id"]
    shape_prior = prior[keep]
    shape_friday = friday_slope[keep] * test["TyreLife"]
    shape_corrected = (friday_slope[keep] - offset) * test["TyreLife"]
    shape_both = (_demean(shape_prior, stints) + _demean(shape_corrected, stints)) / 2
    actual = test["lap_time_s"]
    return {
        "season": season,
        "circuit": circuit,
        "compounds": int(test["Compound"].nunique()),
        "long_runs": int(sum(n for c, (_, n) in friday.items() if c in set(test["Compound"]))),
        "race_laps": int(len(test)),
        "r2_other_seasons": _r2(actual, shape_prior, stints),
        "r2_friday": _r2(actual, shape_friday, stints),
        "r2_friday_corrected": _r2(actual, shape_corrected, stints),
        "offset": offset,
        "r2_both": _r2(actual, shape_both, stints),
    }


def build() -> pd.DataFrame:
    practice = pd.read_csv(PRACTICE)
    frames, fridays, gaps = {}, {}, []
    for circuit, by_circuit in practice.groupby("circuit"):
        try:
            laps = load_circuit_laps(circuit, seasons=PRE_ERA_SEASONS)
        except ValueError:
            continue
        frames[circuit], _ = build_modelling_frame(laps, circuit)
        for season, part in by_circuit.groupby("season"):
            friday = long_run_slopes(part)
            if not friday:
                continue
            fridays[(circuit, int(season))] = (friday, part["session"].iloc[0])
            test = frames[circuit][frames[circuit]["race"] == f"{season}_{circuit}"]
            for compound, actual in race_slopes(test).items():
                if compound in friday:
                    gaps.append((circuit, friday[compound][0] - actual))
    gaps = pd.DataFrame(gaps, columns=["circuit", "gap"])
    rows = []
    for (circuit, season), (friday, session) in sorted(fridays.items()):
        # Friday's systematic gap to Sunday, learned without this circuit.
        offset = float(gaps.loc[gaps["circuit"] != circuit, "gap"].median())
        row = score_race(frames[circuit], circuit, season, friday, offset)
        if row is not None:
            row["session"] = session
            rows.append(row)
    frame = pd.DataFrame(rows).sort_values(["season", "circuit"]).reset_index(drop=True)
    frame["friday_minus_other"] = frame["r2_friday"] - frame["r2_other_seasons"]
    frame["corrected_minus_other"] = frame["r2_friday_corrected"] - frame["r2_other_seasons"]
    frame["both_minus_other"] = frame["r2_both"] - frame["r2_other_seasons"]
    return frame


def _clustered_median_ci(frame: pd.DataFrame, column: str, rng) -> tuple[float, float]:
    """Resample whole circuits: the other-seasons fits of one circuit share data."""
    groups = [g[column].to_numpy() for _, g in frame.groupby("circuit")]
    n = len(groups)
    draws = np.empty(BOOT_DRAWS)
    for i in range(BOOT_DRAWS):
        picked = rng.integers(0, n, size=n)
        draws[i] = np.median(np.concatenate([groups[j] for j in picked]))
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return float(lo), float(hi)


def summarise(frame: pd.DataFrame) -> dict:
    rng = np.random.default_rng(BOOT_SEED)
    out = {"n_races": int(len(frame)), "n_circuits": int(frame["circuit"].nunique()),
           "n_fp1": int((frame["session"] == "Practice 1").sum())}
    for col in ("r2_other_seasons", "r2_friday", "r2_friday_corrected", "r2_both"):
        out[col] = float(frame[col].median())
    out["offset"] = float(frame["offset"].median())
    for col in ("friday_minus_other", "corrected_minus_other", "both_minus_other"):
        diff = frame[col].to_numpy()
        lo, hi = _clustered_median_ci(frame, col, rng)
        better, worse = int((diff > 0).sum()), int((diff < 0).sum())
        out[col] = {"median": float(np.median(diff)), "ci_low": lo, "ci_high": hi,
                    "n_better": better, "n_worse": worse,
                    "sign_p": float(binomtest(better, better + worse).pvalue)}
    out["n_friday_above"] = int((frame["r2_friday"] > 0.2).sum())
    out["n_other_above"] = int((frame["r2_other_seasons"] > 0.2).sum())
    out["n_both_above"] = int((frame["r2_both"] > 0.2).sum())
    out["n_corrected_above"] = int((frame["r2_friday_corrected"] > 0.2).sum())
    return out


def report(frame: pd.DataFrame, s: dict) -> str:
    f, c, b = s["friday_minus_other"], s["corrected_minus_other"], s["both_minus_other"]
    lines = [
        "<!-- GENERATED by scripts/run_practice_long_runs.py — do not edit by hand. -->",
        "",
        "# Friday long runs against other seasons as the slope for Sunday",
        "",
        f"{s['n_races']} races at {s['n_circuits']} circuits, 2023-2025 "
        f"({s['n_fp1']} sprint weekends, where the only practice session is used). "
        "Within-stint R² on the same race laps for each predictor.",
        "",
        "| predictor | median R² | races above 0.2 |",
        "|---|---|---|",
        f"| other seasons (Result 1) | {s['r2_other_seasons']:.3f} | {s['n_other_above']} |",
        f"| Friday long runs | {s['r2_friday']:.3f} | {s['n_friday_above']} |",
        f"| Friday, less its usual gap to Sunday | {s['r2_friday_corrected']:.3f} | {s['n_corrected_above']} |",
        f"| average of other seasons and corrected Friday | {s['r2_both']:.3f} | {s['n_both_above']} |",
        "",
        f"Friday long runs degrade faster than the same compound in the race: the "
        f"median gap is {s['offset']:+.3f} s per lap. The corrected row subtracts "
        "that gap, learned on every other circuit so the held-out race never "
        "informs its own correction.",
        "",
        f"Friday minus other seasons: median {f['median']:+.3f}, 95% interval "
        f"resampling circuits [{f['ci_low']:+.3f}, {f['ci_high']:+.3f}]; better in "
        f"{f['n_better']} races, worse in {f['n_worse']} (sign test p = {f['sign_p']:.3f}).",
        "",
        f"Corrected Friday minus other seasons: median {c['median']:+.3f} "
        f"[{c['ci_low']:+.3f}, {c['ci_high']:+.3f}]; better in {c['n_better']}, worse "
        f"in {c['n_worse']} (p = {c['sign_p']:.3f}).",
        "",
        f"Both minus other seasons: median {b['median']:+.3f} "
        f"[{b['ci_low']:+.3f}, {b['ci_high']:+.3f}]; better in {b['n_better']}, worse "
        f"in {b['n_worse']} (p = {b['sign_p']:.3f}).",
        "",
        "| season | circuit | session | compounds | long runs | R², other seasons | R², Friday | R², Friday corrected | R², both |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in frame.itertuples():
        lines.append(
            f"| {r.season} | {r.circuit} | {r.session} | {r.compounds} | {r.long_runs} | "
            f"{r.r2_other_seasons:.3f} | {r.r2_friday:.3f} | {r.r2_friday_corrected:.3f} | "
            f"{r.r2_both:.3f} |"
        )
    lines.append("")
    return "\n".join(lines)


def _json(stats: dict) -> str:
    """Rounded so the committed file does not churn on the last float digit."""
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
    OUT_SUMMARY.write_text(_json(stats), encoding="utf-8")
    OUT_MD.write_text(report(frame, stats), encoding="utf-8")
    print(frame.to_string())
    print(stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())
