"""The committed-strategy replay, on the endurance audit.

The endurance audit asks the same kind of single-next-stop engine as Formula 1
where to make the first stop, and that engine also runs the stint after it to
the flag: it bounds the first stop by the fuel clock, and assumes nothing about
the stop after. A real endurance car stops again a fuel range later, so the
same mismatch is possible here. See ``run_committed_strategy.py`` for the
argument; this applies it with the two constraints endurance adds.

- **Fuel bounds both stints.** The first stop must come before the tank runs
  dry, and the stint from it to the team's second stop must also fit inside one
  tank. A candidate that leaves an infeasible second stint is not a plan.
- **No skipping the stop.** Over the shortened horizon the engine offers "run to
  the flag" when the horizon is inside the fuel range; that would be skipping a
  stop the team made, so it is not a candidate here.

Writes ``data/derived/endurance/committed_strategy.csv`` and
``reports/cross_series/committed_strategy_endurance.md``.

    python scripts/run_committed_strategy_endurance.py
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.audit.endurance_case_state import load_case_laps, pit_stops, state_at  # noqa: E402
from src.ingestion.config import ENDURANCE_DERIVED_DIR  # noqa: E402
from src.reporting.class_reports import CLASS_LABELS  # noqa: E402
from src.simulator.endurance import EnduranceScenario, simulate  # noqa: E402
from src.simulator.endurance_models import load_race_model  # noqa: E402

#: Same draw count and seed as the published endurance audit.
N_DRAWS = 1200
SEED = 20260712
BOOT_SEED = 20261031
BOOT_DRAWS = 10_000

AUDIT = ENDURANCE_DERIVED_DIR / "systematic_audit.csv"
OUT_CSV = ENDURANCE_DERIVED_DIR / "committed_strategy.csv"
OUT_SUMMARY = ENDURANCE_DERIVED_DIR / "committed_strategy_summary.csv"
OUT_MD = REPO / "reports" / "cross_series" / "committed_strategy_endurance.md"


def committed_lap(row, laps: pd.DataFrame, model, horizon: int) -> dict | None:
    """The engine's first-stop lap when the race ends, for it, at ``horizon``,
    with the feasible window it chose from."""
    decision = int(row.decision_lap)
    real = int(row.real_pit_lap)
    try:
        state = state_at(laps, str(row.car), decision)
    except (LookupError, ValueError):
        return None
    scenario = EnduranceScenario(
        current_lap=decision,
        total_laps=horizon,
        tyre_age=state.tyre_age,
        laps_since_refuel=state.laps_since_refuel,
    )
    try:
        table = simulate(scenario, model, n_draws=N_DRAWS, seed=SEED)
    except ValueError:
        return None
    # A first stop needs a second stint after it that one tank can cover, and
    # at least one lap long; skipping the stop is not on offer.
    earliest = horizon - model.fuel_range_laps
    feasible = table[
        (table["pit_lap"] > 0)
        & (table["pit_lap"] >= earliest)
        & (table["pit_lap"] < horizon)
    ]
    if feasible.empty or real not in set(feasible["pit_lap"]):
        return None
    laps_window = feasible["pit_lap"].to_numpy()
    return {
        "lap": int(feasible.loc[feasible["median_s"].idxmin(), "pit_lap"]),
        "window_laps": int(len(laps_window)),
        "uniform_miss": float(np.mean(np.abs(laps_window - real))),
        "midpoint_miss": float(abs((laps_window.min() + laps_window.max()) / 2 - real)),
    }


def build() -> pd.DataFrame:
    audit = pd.read_csv(AUDIT, dtype={"car": str})
    cache_laps: dict[tuple, pd.DataFrame] = {}
    cache_model: dict[tuple, object] = {}
    rows = []
    for i, row in enumerate(audit.itertuples(), 1):
        key = (row.series, int(row.year), row.event, row.car_class)
        if key not in cache_laps:
            cache_laps[key] = load_case_laps(*key)
            cache_model[key] = load_race_model(*key)
        laps = cache_laps[key]
        stops = pit_stops(laps, str(row.car))
        later = [s for s in stops if s > int(row.real_pit_lap)]
        second = later[0] if later else None
        committed = None
        chance = {"window_laps": None, "uniform_miss": None, "midpoint_miss": None}
        if second is not None:
            if i % 50 == 0:
                print(f"[{i}/{len(audit)}]", flush=True)
            result = committed_lap(row, laps, cache_model[key], int(second))
            if result is not None:
                committed = result.pop("lap")
                chance = result
        rows.append({
            "series": row.series,
            "year": row.year,
            "event": row.event,
            "car_class": row.car_class,
            "car": row.car,
            "n_stops": len(stops),
            "decision_lap": row.decision_lap,
            "real_pit_lap": row.real_pit_lap,
            "second_pit_lap": second,
            "model_pit_lap": row.model_pit_lap,
            "committed_pit_lap": committed,
            "delta_laps": row.delta_laps,
            "committed_delta_laps": (
                None if committed is None else committed - int(row.real_pit_lap)
            ),
            **chance,
        })
    frame = pd.DataFrame(rows)
    for col in ("second_pit_lap", "committed_pit_lap", "committed_delta_laps"):
        frame[col] = frame[col].astype("Int64")
    return frame


def paired_bootstrap(part: pd.DataFrame, rng) -> dict:
    """Both medians from the same resampled races (a race is year + event)."""
    key = part[["year", "event"]].astype(str).agg("_".join, axis=1)
    races = [g for _, g in part.groupby(key)]
    before = [g["delta_laps"].to_numpy(dtype=float) for g in races]
    after = [g["committed_delta_laps"].to_numpy(dtype=float) for g in races]
    n = len(races)
    b = np.empty(BOOT_DRAWS)
    a = np.empty(BOOT_DRAWS)
    for i in range(BOOT_DRAWS):
        picked = rng.integers(0, n, size=n)
        b[i] = np.median(np.concatenate([before[j] for j in picked]))
        a[i] = np.median(np.concatenate([after[j] for j in picked]))
    bl, bh = np.percentile(b, [2.5, 97.5])
    al, ah = np.percentile(a, [2.5, 97.5])
    return {
        "n_decisions": int(len(part)),
        "n_races": n,
        "median_delta": float(np.median(part["delta_laps"])),
        "ci_low": float(bl),
        "ci_high": float(bh),
        "committed_median_delta": float(np.median(part["committed_delta_laps"])),
        "committed_ci_low": float(al),
        "committed_ci_high": float(ah),
        "committed_contains_zero": bool(al <= 0 <= ah),
        "committed_abs_miss": float(np.median(np.abs(part["committed_delta_laps"]))),
        "uniform_miss": float(np.nanmedian(part["uniform_miss"].astype(float)))
        if part["uniform_miss"].notna().any() else float("nan"),
        "midpoint_miss": float(np.nanmedian(part["midpoint_miss"].astype(float)))
        if part["midpoint_miss"].notna().any() else float("nan"),
        "window_laps": float(np.nanmedian(part["window_laps"].astype(float)))
        if part["window_laps"].notna().any() else float("nan"),
    }


def summary(frame: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(BOOT_SEED)
    replayed = frame.dropna(subset=["committed_delta_laps"]).copy()
    replayed["committed_delta_laps"] = replayed["committed_delta_laps"].astype(float)
    rows = []
    for (series, car_class), part in replayed.groupby(["series", "car_class"]):
        stats = paired_bootstrap(part, rng)
        stats["series"] = series
        stats["car_class"] = car_class
        rows.append(stats)
    cols = ["series", "car_class", "n_decisions", "n_races", "median_delta",
            "ci_low", "ci_high", "committed_median_delta", "committed_ci_low",
            "committed_ci_high", "committed_contains_zero", "committed_abs_miss",
            "uniform_miss", "midpoint_miss", "window_laps"]
    return pd.DataFrame(rows)[cols]


def _fmt(x: float) -> str:
    return f"{x:+.0f}" if float(x).is_integer() else f"{x:+.1f}"


def report(frame: pd.DataFrame, table: pd.DataFrame) -> str:
    n_second = int(frame["second_pit_lap"].notna().sum())
    n_replayed = int(frame["committed_delta_laps"].notna().sum())
    lines = [
        "<!-- GENERATED by scripts/run_committed_strategy_endurance.py — do not edit by hand. -->",
        "",
        "# Endurance audit, replayed with the team's second stop as the horizon",
        "",
        f"Of {len(frame)} published endurance decisions, {n_second} have a later "
        f"stop by the same car, and {n_replayed} of those can be replayed with "
        "the horizon at that stop: the real first stop has to be a feasible "
        "candidate once the second stint must also fit in one tank. Medians of "
        "model lap minus real lap on those decisions, before and after, with "
        "intervals from resampling whole races (the same races for both "
        "columns).",
        "",
        "| class | decisions | races | median gap, published | 95% interval | "
        "median gap, committed strategy | 95% interval |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in table.itertuples():
        label = CLASS_LABELS.get((r.series, r.car_class), f"{r.series} {r.car_class}")
        lines.append(
            f"| {label} | {r.n_decisions} | {r.n_races} | {_fmt(r.median_delta)} | "
            f"[{r.ci_low:+.1f}, {r.ci_high:+.1f}] | {_fmt(r.committed_median_delta)} | "
            f"[{r.committed_ci_low:+.1f}, {r.committed_ci_high:+.1f}] |"
        )
    lines += [
        "",
        "## Is the agreement more than the window allows?",
        "",
        "In endurance the fuel clock bounds the first stop from above and, once "
        "the second stop is fixed, the second stint bounds it from below. The "
        "window can be narrow enough to make agreement automatic, so each class "
        "is compared against two chance baselines on the same windows: a lap "
        "drawn uniformly from the window, and its midpoint. A class where the "
        "engine does no better than chance carries no evidence either way.",
        "",
        "| class | median window, laps | engine miss | uniform lap miss | midpoint miss | informative |",
        "|---|---|---|---|---|---|",
    ]
    for r in table.itertuples():
        label = CLASS_LABELS.get((r.series, r.car_class), f"{r.series} {r.car_class}")
        beats = r.committed_abs_miss < min(r.uniform_miss, r.midpoint_miss)
        lines.append(
            f"| {label} | {r.window_laps:.0f} | {r.committed_abs_miss:.0f} | "
            f"{r.uniform_miss:.1f} | {r.midpoint_miss:.1f} | "
            f"{'yes' if beats else 'no'} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    warnings.filterwarnings("ignore")
    frame = build()
    table = summary(frame)
    frame.to_csv(OUT_CSV, index=False)
    table.to_csv(OUT_SUMMARY, index=False)
    OUT_MD.write_text(report(frame, table), encoding="utf-8")
    print(table.to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
