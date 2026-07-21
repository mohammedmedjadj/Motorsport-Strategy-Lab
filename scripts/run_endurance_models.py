"""Regenerate the committed endurance model artifacts from the raw laps.

The endurance reports (reports/imsa/, reports/wec/) are written by hand for
their prose, but their *numbers* must not drift from the data. This script
recomputes those numbers from the materialised laps and writes them to
machine-readable CSVs under data/derived/endurance/, so the reports can be
checked against a reproducible source (and a data refresh regenerates them):

- endurance_degradation_fits.csv  — per circuit-season net slope, CI, RMSE,
  fuel/deg correlation, separability
- endurance_degradation_loro.csv  — leave-one-season-out CV per circuit
- endurance_data_quality.csv       — per-race lap accounting (frame stages)

The neutralisation posteriors already have a reproducible source
(data/derived/endurance/race_flags.csv via scripts/run_endurance_flags.py),
so they are not duplicated here.

Usage (from the repo root; offline — reads the committed derived CSVs)::

    python scripts/run_endurance_models.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.endurance_loader import EnduranceLoader  # noqa: E402
from src.data.endurance_scope import ENDURANCE_SCOPE  # noqa: E402
from src.degradation.endurance import (  # noqa: E402
    build_endurance_frame,
    fit_endurance_degradation,
    frame_diagnostics,
)
from src.degradation.endurance_validation import (  # noqa: E402
    leave_one_race_out_endurance,
    mean_r2,
)
from src.ingestion.config import ENDURANCE_DERIVED_DIR  # noqa: E402
from src.simulator.endurance import estimate_tyre_change_premium  # noqa: E402
from src.simulator.track_position import (  # noqa: E402
    adjacent_swap_rate_endurance,
    measure_circuit,
)
from src.simulator.traffic import measure_traffic_cost  # noqa: E402

HOLD_LAPS = 15
FIELD_DIR = ENDURANCE_DERIVED_DIR / "field"
PRIME_CLASS = {"imsa": "GTP", "wec": "HYPERCAR"}


def _frames(series: str, event: str, car_class: str, seasons: tuple[int, ...]):
    loader = EnduranceLoader(series)
    return {
        str(yr): build_endurance_frame(loader.load_laps(yr, event, car_class))
        for yr in seasons
    }


def main() -> int:
    fits: list[dict[str, object]] = []
    loro: list[dict[str, object]] = []
    quality: list[dict[str, object]] = []

    for series, circuits in ENDURANCE_SCOPE.items():
        for cs in circuits:
            frames = _frames(series, cs.event, cs.car_class, cs.seasons)
            loader = EnduranceLoader(series)

            for season in cs.seasons:
                laps = loader.load_laps(season, cs.event, cs.car_class)
                d = frame_diagnostics(laps)
                quality.append({
                    "series": series, "event": cs.event, "season": season,
                    "total_laps": d.total_laps, "non_green_or_pit": d.non_green_or_pit,
                    "missing_tyre_age": d.missing_tyre_age,
                    "field_wide_trimmed": d.field_wide_trimmed,
                    "per_car_trimmed": d.per_car_trimmed,
                    "insufficient_car_laps": d.insufficient_car_laps,
                    "kept": d.kept, "pct_kept": round(d.pct_kept, 1),
                })
                fit = fit_endurance_degradation(frames[str(season)])
                fits.append({
                    "series": series, "event": cs.event, "season": season,
                    "n_laps": fit.n_laps, "n_cars": fit.n_cars,
                    "net_slope": round(fit.net_slope.value, 4),
                    "ci_low": round(fit.net_slope.ci_low, 4),
                    "ci_high": round(fit.net_slope.ci_high, 4),
                    "rmse_s": round(fit.rmse_s, 3),
                    "fuel_deg_corr": round(fit.fuel_deg_correlation, 3),
                    "separable": fit.separable,
                })

            if len(frames) >= 2:
                folds = leave_one_race_out_endurance(frames)
                for f in folds:
                    loro.append({
                        "series": series, "event": cs.event,
                        "held_out_season": f.held_out,
                        "pooled_slope": round(f.pooled_slope, 4),
                        "own_slope": round(f.own_slope, 4),
                        "r2_within": round(f.r2_within, 4),
                        "rmse_s": round(f.rmse_s, 3), "n_laps": f.n_laps,
                    })
                loro.append({
                    "series": series, "event": cs.event,
                    "held_out_season": "MEAN",
                    "pooled_slope": "", "own_slope": "",
                    "r2_within": round(mean_r2(folds), 4), "rmse_s": "", "n_laps": "",
                })

    # Pit-stop procedure: pool every scoped race per series (a series-level
    # rulebook property, not a per-circuit one) and measure the tyre-change
    # premium — IMSA services tyres in parallel with fuel, WEC in sequence.
    pit_procedure: list[dict[str, object]] = []
    for series, circuits in ENDURANCE_SCOPE.items():
        loader = EnduranceLoader(series)
        pooled = pd.concat(
            [loader.load_laps(yr, cs.event, cs.car_class)
             for cs in circuits for yr in cs.seasons],
            ignore_index=True,
        )
        p = estimate_tyre_change_premium(pooled)
        pit_procedure.append({
            "series": series,
            "fuel_only_median_s": round(p.fuel_only_median_s, 1),
            "tyre_change_median_s": round(p.tyre_change_median_s, 1),
            "tyre_change_premium_s": round(p.premium_s, 1),
            "n_fuel_only": p.n_fuel_only, "n_tyre_change": p.n_tyre_change,
        })

    # Track-position value (overtaking difficulty), per circuit, position
    # reconstructed from cumulative time within the class.
    overtaking: list[dict[str, object]] = []
    for series, circuits in ENDURANCE_SCOPE.items():
        loader = EnduranceLoader(series)
        for cs in circuits:
            races = {str(yr): loader.load_laps(yr, cs.event, cs.car_class)
                     for yr in cs.seasons}
            o = measure_circuit(races, cs.event, rate_fn=adjacent_swap_rate_endurance)
            overtaking.append({
                "series": series, "circuit": cs.event,
                "adj_swap_rate": round(o.swap_rate, 4),
                "sd_across_races": round(o.sd, 4),
                "n_races": o.n_races, "n_transitions": o.n_transitions,
                f"p_hold_{HOLD_LAPS}_laps": round(o.hold_probability(HOLD_LAPS), 3),
            })

    # Inter-class traffic cost, from the committed multi-class field data
    # (one season per circuit under data/derived/endurance/field/).
    traffic: list[dict[str, object]] = []
    for path in sorted(FIELD_DIR.glob("field_*.csv")):
        series, _year, circuit_slug = path.stem.removeprefix("field_").split("_", 2)
        field = pd.read_csv(path)
        try:
            t = measure_traffic_cost(field, series, circuit_slug, PRIME_CLASS[series])
        except ValueError:
            continue
        traffic.append({
            "series": series, "circuit": circuit_slug,
            "clean_air_dev_s": t.clean_air_dev_s,
            "clear_vs_traffic_s": t.clear_vs_traffic_s,
            "cost_per_car_s": t.cost_per_car_s,
            "n_prime_laps": t.n_prime_laps, "n_other_cars": t.n_other_cars,
        })

    ENDURANCE_DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    outputs = {
        "endurance_degradation_fits.csv": fits,
        "endurance_degradation_loro.csv": loro,
        "endurance_data_quality.csv": quality,
        "endurance_pit_procedure.csv": pit_procedure,
        "endurance_overtaking_difficulty.csv": overtaking,
        "endurance_traffic_cost.csv": traffic,
    }
    for name, rows in outputs.items():
        path = ENDURANCE_DERIVED_DIR / name
        pd.DataFrame(rows).to_csv(path, index=False)
        print(f"wrote {path} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
