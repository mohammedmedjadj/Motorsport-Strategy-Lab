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

from src.data.endurance_loader import slugify  # noqa: E402
from src.data.endurance_scope import canonical_circuit  # noqa: E402
from src.ingestion.config import ENDURANCE_DERIVED_DIR  # noqa: E402
from src.simulator.endurance_models import (  # noqa: E402
    load_race_model,
    race_distance,
)
from src.simulator.multistop import (  # noqa: E402
    TrafficModel,
    evaluate_plan,
    min_stops_plan,
    optimal_stop_plan,
)

#: **Every** scoped race-season whose laps are committed — not one per circuit.
#:
#: This layer used to run on a single representative season per circuit-class,
#: justified on the grounds that "fuel range and stop structure are circuit
#: properties". Fuel range is. **The degradation slope is not**, and the plan
#: depends on it: `optimal_stop_plan` trades tyre loss against pit loss, so
#: whether a race comes out tyre-limited is a function of that season's fitted
#: slope.
#:
#: This project's own most-cited result is that degradation slopes **fail to
#: transfer between seasons** — leave-one-race-out within-stint R² is at or
#: below zero almost everywhere. A layer that picks one arbitrary season and
#: calls the answer a property of the circuit is contradicted by the finding
#: printed two reports over. It covered 65 of 209 modelled race-seasons, 31%,
#: and the headline "9 of 66 circuit-seasons are tyre-limited" plus the −0.913
#: pit-loss correlation were both computed on that sample.
#:
#: Races with no usable model are still skipped — a genuinely caution-free race
#: has no FCY *or* SC laps to measure a pace ratio from — but they are now
#: skipped **individually and counted**, rather than silently standing in for
#: a circuit's other seasons.
def _scoped_races() -> list[tuple[str, int, str, str, str]]:
    """Flat list of (series, year, event, car_class, circuit_slug)."""
    from src.data.endurance_loader import derived_path, slugify
    from src.data.endurance_scope import ENDURANCE_SCOPE
    races = [
        (series, year, cs.event, cs.car_class, slugify(cs.event))
        for series, circuits in ENDURANCE_SCOPE.items()
        for cs in circuits
        for year in sorted(cs.seasons)
        if derived_path(series, year, cs.event, cs.car_class).exists()
    ]
    return sorted(races)


SCOPED_RACES = _scoped_races()


def _build_model(series: str, year: int, event: str, car_class: str):
    """The race model plus this race's distance in laps.

    The model itself comes from the shared builder so this script, the audit
    and the demo cannot disagree about what "the Bahrain 2024 model" is.
    """
    model = load_race_model(series, year, event, car_class)
    return model, race_distance(series, year, event, car_class)


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
    skipped: list[tuple] = []
    for index, (series, year, event, car_class, circuit) in enumerate(SCOPED_RACES, 1):
        print(f"[{index}/{len(SCOPED_RACES)}] {series} {year} {event} ({car_class})",
              flush=True)
        try:
            model, race_laps = _build_model(series, year, event, car_class)
        except ValueError as exc:
            skipped.append((series, year, event, car_class, str(exc)))
            print(f"  skip (no usable model: {exc})", flush=True)
            continue
        opt = optimal_stop_plan(race_laps, model.green_pace_s, model.net_slope_s,
                                model.pit_loss_s, model.fuel_range_laps)
        naive = min_stops_plan(race_laps, model.fuel_range_laps)
        # The headline claim is on STOP COUNT: does the optimum ever take more
        # stops than the fuel minimum? Separately, at equal stop count the DP can
        # still choose a different stint-length *pattern* (re-spacing evenly
        # rather than running the tank flat out with a short last stint) — a
        # real, narrower finding that a same-named boolean must not blur into
        # "tyre-limited", so the two are reported as distinct columns.
        fuel_limited_on_stops = opt.n_stops == naive.n_stops
        stint_pattern_matches_naive = opt.stint_lengths == naive.stint_lengths
        breakeven = _breakeven_slope(race_laps, model, naive.n_stops)

        sd = stability.loc[(stability["series"] == series)
                           & (stability["circuit"] == circuit), "clear_vs_traffic_sd_s"]
        traffic = TrafficModel(float(sd.iloc[0])) if len(sd) else None

        dist = evaluate_plan(opt, race_laps, model, n_draws=4000)
        dist_t = (evaluate_plan(opt, race_laps, model, n_draws=4000, traffic=traffic)
                  if traffic is not None else dist)
        rows.append({
            # car_class is part of the identity of a row, not decoration: a
            # series can field two classes at the same circuit-year, and
            # without it those rows are indistinguishable on every key a
            # consumer would naturally merge or filter on.
            "series": series, "circuit": circuit,
            # The canonical circuit is the identity a validation fold must
            # group on; `circuit` stays the source's own slug so a row can
            # still be traced back to the file it came from. They differ only
            # where a track was renamed upstream (see CIRCUIT_ALIASES).
            "circuit_canonical": slugify(canonical_circuit(event)),
            "car_class": car_class, "year": year,
            "race_laps": race_laps, "green_pace_s": round(model.green_pace_s, 1),
            "net_slope_s": round(model.net_slope_s, 4),
            "pit_loss_s": round(model.pit_loss_s, 1),
            "fuel_range_laps": model.fuel_range_laps,
            "min_stops": naive.n_stops, "optimal_stops": opt.n_stops,
            "fuel_limited": fuel_limited_on_stops,
            "stint_pattern_matches_naive": stint_pattern_matches_naive,
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
    summary = table.groupby(["series", "car_class"]).agg(
        races=("year", "size"),
        circuits=("circuit_canonical", "nunique"),
        tyre_limited=("fuel_limited", lambda s: int((~s).sum())),
        median_pit_loss=("pit_loss_s", "median"),
    )
    print(summary.to_string())
    # Skips are an artifact, not a print. A race missing from the plan table is
    # either explained here or it is a silent coverage hole, and
    # tests/test_coverage.py asserts exactly that: every scoped race is either
    # planned, or recorded below with the reason it could not be.
    pd.DataFrame(
        skipped, columns=["series", "year", "event", "car_class", "reason"]
    ).to_csv(ENDURANCE_DERIVED_DIR / "multistop_skipped.csv", index=False)
    if skipped:
        print(f"\n{len(skipped)} of {len(SCOPED_RACES)} race-seasons skipped "
              "(no usable FCY/SC model):")
        for series, year, event, car_class, reason in skipped:
            print(f"  - {series} {year} {event} ({car_class}): {reason}")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
