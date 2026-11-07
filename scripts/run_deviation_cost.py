"""What did stopping on a different lap from the planner actually cost?

Result 3 measures how far the teams' first stops sit from the planner's lap. It
does not say what the distance cost, and the planner's own answer to that is a
model output: the simulated median race time at the team's lap minus at its own.
This asks the races instead.

The committed-strategy replay gives, for every first stop, the planner's lap
with the team's next stop held fixed and the time the planner predicts the
team's lap cost. Over the same stretch of the real race -- from the decision lap
to the team's next stop, or to the flag for a one-stop car -- each car's elapsed
time is measured and compared with what its own race pace predicts for that
many laps. Cars in the same race share the track, the weather and the tyre
allocation, so the comparison is made within races: a race fixed effect absorbs
everything common to the field, and what remains is whether the cars the
planner says lost more time did lose more time.

- **Excess time.** Elapsed time over the window minus the number of laps times
  the car's median green-flag race lap. It carries the pit stop, the out-lap and
  the tyre phase, which every car in the window shares in kind.
- **Neutralisations are excluded.** A window that contains a safety car, a
  virtual safety car or a red flag for that car is dropped: a stop under neutralisation is
  cheaper by an amount the planner's cost does not describe.
- **This is association, not a controlled experiment.** Teams leave the
  planner's lap for reasons the planner cannot see -- traffic, a rival's stop, a
  car problem -- and those reasons have their own cost. A slope near one says the
  planner's costs show up in the clock; a slope near zero says they do not, or
  that the reasons teams deviate pay for the deviation.

Writes ``data/derived/f1/deviation_cost.csv``, ``deviation_cost_summary.json`` and
``reports/f1/deviation_cost.md``.

    python scripts/run_deviation_cost.py
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

from src.audit.state import load_race_laps  # noqa: E402
from src.ingestion.config import F1_DERIVED_DIR, F1_REPORTS_DIR  # noqa: E402

COMMITTED = F1_DERIVED_DIR / "committed_strategy.csv"
OUT_CSV = F1_DERIVED_DIR / "deviation_cost.csv"
OUT_SUMMARY = F1_DERIVED_DIR / "deviation_cost_summary.json"
OUT_MD = F1_REPORTS_DIR / "deviation_cost.md"

BOOT_SEED = 20261107
BOOT_DRAWS = 10_000
#: Track-status codes for a safety car (4), red flag (5) and virtual safety car
#: (6, 7). A local yellow (2) slows one sector for a few laps and is left in.
NEUTRALISED = "[4567]"
#: A race needs at least this many usable cars for a within-race comparison.
MIN_CARS = 3


def window_excess(laps: pd.DataFrame, driver: str, start: int, end: int) -> dict | None:
    car = laps[laps["Driver"] == driver].set_index("LapNumber")
    if start not in car.index or end not in car.index:
        return None
    window = car.loc[start + 1:end]
    if len(window) != end - start or window["time_s"].isna().any():
        return None
    status = window["TrackStatus"].fillna("").astype(str).str.replace(".0", "", regex=False)
    if status.str.contains(NEUTRALISED).any():
        return None
    pace = car.loc[car["is_pace_lap"].fillna(False).astype(bool), "lap_time_s"].median()
    if not np.isfinite(pace):
        return None
    elapsed = float(car.loc[end, "time_s"] - car.loc[start, "time_s"])
    return {"window_laps": end - start, "elapsed_s": elapsed,
            "pace_s": float(pace), "excess_s": elapsed - (end - start) * float(pace)}


def build() -> pd.DataFrame:
    committed = pd.read_csv(COMMITTED).dropna(subset=["committed_pit_lap", "committed_cost_s"])
    rows = []
    for (season, circuit), part in committed.groupby(["season", "circuit"]):
        laps = load_race_laps(f"{season}_{circuit}")
        last = int(laps["LapNumber"].max())
        for r in part.itertuples():
            end = int(r.second_pit_lap) if pd.notna(r.second_pit_lap) else last
            measured = window_excess(laps, r.driver, int(r.decision_lap), end)
            if measured is None:
                continue
            rows.append({
                "season": season, "circuit": circuit, "driver": r.driver,
                "n_stops": r.n_stops, "decision_lap": r.decision_lap,
                "real_pit_lap": r.real_pit_lap, "planner_pit_lap": int(r.committed_pit_lap),
                "deviation_laps": int(r.real_pit_lap) - int(r.committed_pit_lap),
                "predicted_cost_s": float(r.committed_cost_s), **measured,
            })
    frame = pd.DataFrame(rows)
    frame["race"] = frame["season"].astype(str) + "_" + frame["circuit"]
    size = frame.groupby("race")["driver"].transform("size")
    return frame[size >= MIN_CARS].reset_index(drop=True)


def within(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    return frame[columns] - frame.groupby("race")[columns].transform("mean")


def slope(frame: pd.DataFrame, x: str) -> float:
    """OLS slope of excess time on ``x`` with race fixed effects and window length."""
    d = within(frame, ["excess_s", x, "window_laps"])
    X = d[[x, "window_laps"]].to_numpy()
    beta, *_ = np.linalg.lstsq(X, d["excess_s"].to_numpy(), rcond=None)
    return float(beta[0])


def clustered(frame: pd.DataFrame, x: str, rng) -> tuple[float, float]:
    races = [g for _, g in frame.groupby("race")]
    n = len(races)
    draws = np.empty(BOOT_DRAWS)
    for i in range(BOOT_DRAWS):
        picked = rng.integers(0, n, size=n)
        sample = pd.concat(
            [races[j].assign(race=f"{k}") for k, j in enumerate(picked)], ignore_index=True
        )
        draws[i] = slope(sample, x)
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return float(lo), float(hi)


def summarise(frame: pd.DataFrame) -> dict:
    rng = np.random.default_rng(BOOT_SEED)
    frame = frame.assign(abs_deviation=frame["deviation_laps"].abs())
    out = {"n_cars": int(len(frame)), "n_races": int(frame["race"].nunique()),
           "median_predicted_s": float(frame["predicted_cost_s"].median()),
           "median_abs_deviation": float(frame["abs_deviation"].median())}
    for x in ("predicted_cost_s", "abs_deviation"):
        lo, hi = clustered(frame, x, rng)
        out[x] = {"slope": slope(frame, x), "ci_low": lo, "ci_high": hi}
    out["within_race_sd_s"] = float(frame.groupby("race")["excess_s"].std().median())
    # What the planner itself says one lap of deviation costs, for comparison.
    off = frame[frame["abs_deviation"] > 0]
    out["planner_per_lap_s"] = float((off["predicted_cost_s"] / off["abs_deviation"]).median())
    return out


def report(frame: pd.DataFrame, s: dict) -> str:
    p, d = s["predicted_cost_s"], s["abs_deviation"]
    return "\n".join([
        "<!-- GENERATED by scripts/run_deviation_cost.py — do not edit by hand. -->",
        "",
        "# What leaving the planner's lap cost, measured in the races",
        "",
        f"{s['n_cars']} first stops in {s['n_races']} races, each with a green "
        "window from the decision lap to the team's next stop (or the flag), "
        f"and at least {MIN_CARS} such cars in its race. Median distance from the "
        f"planner's lap: {s['median_abs_deviation']:.0f} laps; median cost the "
        f"planner predicts for it: {s['median_predicted_s']:.2f} s.",
        "",
        "Excess time over the window (elapsed minus laps times the car's own "
        "median green lap), regressed within races on each measure, with the "
        "window's length as a control. Intervals resample whole races.",
        "",
        "| regressor | slope | 95% interval | reads as |",
        "|---|---|---|---|",
        f"| planner's predicted cost (s) | {p['slope']:+.2f} | "
        f"[{p['ci_low']:+.2f}, {p['ci_high']:+.2f}] | seconds of real excess per "
        "predicted second; 1 means the model's costs appear in the clock |",
        f"| laps from the planner's lap | {d['slope']:+.2f} | "
        f"[{d['ci_low']:+.2f}, {d['ci_high']:+.2f}] | real seconds per lap of "
        f"deviation; the planner itself prices a lap at {s['planner_per_lap_s']:.2f} s |",
        "",
        "For scale: the median standard deviation of excess time between cars "
        f"of the same race is {s['within_race_sd_s']:.1f} s.",
        "",
    ])


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
    print(stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())
