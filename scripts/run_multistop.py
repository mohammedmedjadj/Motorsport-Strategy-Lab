"""Full-race multi-stop plans for every in-scope endurance circuit.

Extends the single-next-stop demo to the whole race: the exact minimum-time stop
sequence (dynamic program), whether that sequence is set by the fuel tank or by
tyre wear, how much steeper degradation would have to be to change it
(break-even slope), and the race-time distribution under stochastic
neutralisations — with the measured traffic spread folded in as calibrated
variance. `src/simulator/multistop.py`.

Offline: reads the committed derived laps + neutralisation flags + traffic
stability. Writes ``data/derived/endurance/multistop_plans.csv``.

Usage::

    python scripts/run_multistop.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.endurance_loader import EnduranceLoader  # noqa: E402
from src.degradation.endurance import (  # noqa: E402
    build_endurance_frame,
    fit_endurance_degradation,
)
from src.ingestion.config import ENDURANCE_DERIVED_DIR  # noqa: E402
from src.safety_car.endurance import (  # noqa: E402
    extract_events,
    fit_neutralisation_models,
    load_race_flags,
    race_timeline,
)
from src.simulator.endurance import build_race_model  # noqa: E402
from src.simulator.multistop import (  # noqa: E402
    TrafficModel,
    evaluate_plan,
    min_stops_plan,
    optimal_stop_plan,
)

# The circuits at the season each report already demos, for consistency.
CIRCUITS = [
    ("imsa", 2023, "Watkins Glen", "GTP", "watkins_glen"),
    ("imsa", 2023, "Sebring", "GTP", "sebring"),
    ("imsa", 2023, "Road America", "GTP", "road_america"),
    ("imsa", 2023, "Mosport", "GTP", "mosport"),
    ("wec", 2024, "Spa", "HYPERCAR", "spa"),
    ("wec", 2024, "Fuji", "HYPERCAR", "fuji"),
    ("wec", 2024, "Bahrain", "HYPERCAR", "bahrain"),
    ("wec", 2024, "Imola", "HYPERCAR", "imola"),
]


def _build_model(series: str, year: int, event: str, car_class: str):
    laps = EnduranceLoader(series).load_laps(year, event, car_class)
    fit = fit_endurance_degradation(build_endurance_frame(laps))
    timeline = race_timeline(load_race_flags())
    events = extract_events(timeline)
    post = {(m.series, m.kind): m for m in fit_neutralisation_models(timeline, events)}
    fcy, sc = post[(series, "FCY")], post[(series, "SC")]
    fcy_dur = tuple(e.duration_laps for e in events if e.series == series and e.kind == "FCY")
    sc_dur = tuple(e.duration_laps for e in events if e.series == series and e.kind == "SC")
    model = build_race_model(
        laps, fit.net_slope.value, fit.net_slope.se,
        fcy.n_events + 0.5, fcy.laps_exposure, fcy_dur, fit.rmse_s,
        sc_alpha=sc.n_events + 0.5, sc_exposure=sc.laps_exposure, sc_durations=sc_dur,
    )
    race_laps = int(laps.groupby("car")["lap"].max().median())
    return model, race_laps


def _breakeven_slope(race_laps: int, model, base_stops: int,
                     hi: float = 2.0, step: float = 0.005) -> float:
    """Smallest degradation slope at which the optimum takes more than the
    fuel-minimum number of stops — a measure of how far the race is from
    tyre-limited. ``nan`` if even an implausible 2 s/lap never triggers it."""
    slope = max(model.net_slope_s, 0.0)
    while slope <= hi:
        if optimal_stop_plan(race_laps, model.green_pace_s, slope,
                             model.pit_loss_s, model.fuel_range_laps).n_stops > base_stops:
            return round(slope, 3)
        slope += step
    return float("nan")


def main() -> None:
    stability = pd.read_csv(ENDURANCE_DERIVED_DIR / "endurance_traffic_stability.csv")
    rows = []
    for series, year, event, car_class, circuit in CIRCUITS:
        model, race_laps = _build_model(series, year, event, car_class)
        opt = optimal_stop_plan(race_laps, model.green_pace_s, model.net_slope_s,
                                model.pit_loss_s, model.fuel_range_laps)
        naive = min_stops_plan(race_laps, model.fuel_range_laps)
        fuel_limited = opt.stint_lengths == naive.stint_lengths
        breakeven = _breakeven_slope(race_laps, model, naive.n_stops)

        sd = stability.loc[(stability["series"] == series)
                           & (stability["circuit"] == circuit), "clear_vs_traffic_sd_s"]
        traffic = TrafficModel(float(sd.iloc[0])) if len(sd) else None

        dist = evaluate_plan(opt, race_laps, model, n_draws=4000)
        dist_t = (evaluate_plan(opt, race_laps, model, n_draws=4000, traffic=traffic)
                  if traffic is not None else dist)
        rows.append({
            "series": series, "circuit": circuit, "year": year,
            "race_laps": race_laps, "green_pace_s": round(model.green_pace_s, 1),
            "net_slope_s": round(model.net_slope_s, 4),
            "pit_loss_s": round(model.pit_loss_s, 1),
            "fuel_range_laps": model.fuel_range_laps,
            "min_stops": naive.n_stops, "optimal_stops": opt.n_stops,
            "fuel_limited": fuel_limited,
            "breakeven_slope_s": breakeven,
            "slope_headroom_x": (round(breakeven / model.net_slope_s, 1)
                                 if model.net_slope_s > 0 and breakeven == breakeven else float("nan")),
            "median_s": round(dist["median_s"], 0),
            "p10_s": round(dist["p10_s"], 0), "p90_s": round(dist["p90_s"], 0),
            "band_s": round(dist["p90_s"] - dist["p10_s"], 0),
            "band_with_traffic_s": round(dist_t["p90_s"] - dist_t["p10_s"], 0),
            "traffic_sd_s": round(traffic.clear_vs_traffic_sd_s, 4) if traffic else 0.0,
        })

    table = pd.DataFrame(rows)
    ENDURANCE_DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    out = ENDURANCE_DERIVED_DIR / "multistop_plans.csv"
    table.to_csv(out, index=False)
    print(table.to_string(index=False))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
