"""The multi-stop dynamic program (exactness, fuel constraint, response to
degradation) and the committed full-race artifact (drift guard + the honest
finding that every measured endurance race is fuel-limited on stop count)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.ingestion.config import ENDURANCE_DERIVED_DIR
from src.simulator.endurance import EnduranceRaceModel
from src.simulator.multistop import (
    TrafficModel,
    _stint_time,
    evaluate_plan,
    min_stops_plan,
    optimal_stop_plan,
)


# --- dynamic program: exactness and constraints -----------------------------


def test_stint_time_sums_degradation_over_the_stint() -> None:
    # 3 laps, 100 s green, +1 s/lap: ages 0,1,2 -> 100 + 101 + 102 = 303
    assert _stint_time(3, 100.0, 1.0) == pytest.approx(303.0)


def test_flat_tyres_minimise_stops() -> None:
    # race 4, tank 2, no degradation: the fewest-pits partition [2, 2] wins.
    plan = optimal_stop_plan(4, green_pace_s=100.0, net_slope_s=0.0,
                             pit_loss_s=30.0, fuel_range_laps=2)
    assert plan.stint_lengths == (2, 2)
    assert plan.n_stops == 1


def test_steep_degradation_buys_extra_stops() -> None:
    # same race, but tyres so punishing that an extra pit is worth 30 s.
    flat = optimal_stop_plan(4, 100.0, 0.0, 30.0, 2).n_stops
    steep = optimal_stop_plan(4, 100.0, 40.0, 30.0, 2).n_stops
    assert steep > flat


def test_every_stint_respects_the_fuel_tank() -> None:
    plan = optimal_stop_plan(235, green_pace_s=114.6, net_slope_s=0.049,
                             pit_loss_s=80.6, fuel_range_laps=32)
    assert max(plan.stint_lengths) <= 32
    assert sum(plan.stint_lengths) == 235


def test_optimum_never_beaten_by_the_min_stops_baseline() -> None:
    # The DP is exact, so its deterministic time must be <= any feasible plan's,
    # in particular the fuel-max baseline.
    args = dict(green_pace_s=93.0, net_slope_s=0.0135, pit_loss_s=79.0)
    opt = optimal_stop_plan(213, fuel_range_laps=42, **args)
    naive = min_stops_plan(213, 42)
    naive_time = sum(_stint_time(L, args["green_pace_s"], args["net_slope_s"])
                     for L in naive.stint_lengths) + naive.n_stops * args["pit_loss_s"]
    assert opt.deterministic_time_s <= naive_time + 1e-6


def test_more_degradation_never_reduces_the_stop_count() -> None:
    prev = 0
    for slope in (0.0, 0.05, 0.1, 0.2, 0.4, 0.8):
        n = optimal_stop_plan(140, 130.0, slope, 63.0, 28).n_stops
        assert n >= prev
        prev = n


def test_rejects_nonsense_race() -> None:
    with pytest.raises(ValueError):
        optimal_stop_plan(0, 100.0, 0.0, 30.0, 28)
    with pytest.raises(ValueError):
        optimal_stop_plan(100, 100.0, 0.0, 30.0, 0)


# --- Monte-Carlo evaluation + the traffic-as-variance contract --------------

def _toy_model() -> EnduranceRaceModel:
    return EnduranceRaceModel(
        series="wec", event="Test", car_class="HYPERCAR",
        green_pace_s=130.0, lap_noise_s=0.8, net_slope_s=0.04, net_slope_se=0.01,
        pit_loss_s=60.0, pit_loss_iqr_s=5.0, n_pit_events=50,
        fcy_pace_ratio=1.8, fcy_ratio_measured=True, fcy_alpha=1.0, fcy_exposure=2000.0, fcy_durations=(4, 6),
        sc_pace_ratio=2.1, sc_ratio_measured=True, sc_alpha=1.0, sc_exposure=2000.0,
        sc_durations=(6, 8), fuel_range_laps=28,
    )


def test_evaluate_plan_returns_an_ordered_distribution() -> None:
    model = _toy_model()
    plan = optimal_stop_plan(140, model.green_pace_s, model.net_slope_s,
                             model.pit_loss_s, model.fuel_range_laps)
    d = evaluate_plan(plan, 140, model, n_draws=2000)
    assert d["p10_s"] < d["median_s"] < d["p90_s"]
    assert d["n_stops"] == plan.n_stops
    # Sanity floor: at least the green running time with no stops/neutralisations.
    assert d["median_s"] > 140 * model.green_pace_s


def test_traffic_adds_variance_without_shifting_the_median() -> None:
    """The honesty contract: traffic is a zero-mean per-race effect, so it
    widens the band but leaves the median essentially unmoved (the average cost
    is already in green pace) — never a systematic bias on the plan."""
    model = _toy_model()
    plan = optimal_stop_plan(140, model.green_pace_s, model.net_slope_s,
                             model.pit_loss_s, model.fuel_range_laps)
    plain = evaluate_plan(plan, 140, model, n_draws=6000, seed=7)
    witht = evaluate_plan(plan, 140, model, n_draws=6000, seed=7,
                          traffic=TrafficModel(0.30))
    band_plain = plain["p90_s"] - plain["p10_s"]
    band_with = witht["p90_s"] - witht["p10_s"]
    assert band_with >= band_plain                      # variance can only grow
    # The median moves only by Monte-Carlo noise, an order of magnitude below the
    # ~35 s systematic shift a double-counted traffic bias would have produced.
    assert witht["median_s"] == pytest.approx(plain["median_s"], abs=0.1 * model.green_pace_s)


# --- committed artifact: drift guard + the scientific finding ----------------

@pytest.mark.skipif(not (ENDURANCE_DERIVED_DIR / "multistop_plans.csv").exists(),
                    reason="multistop artifact not generated")
def test_every_measured_race_is_fuel_limited_on_stop_count() -> None:
    """The headline finding, pinned: at no in-scope circuit does the optimum
    take more stops than the fuel minimum — measured tyre degradation is never
    steep enough to out-weigh a pit stop. The break-even slope (how much steeper
    it would need to be) is a positive multiple of the measured slope."""
    art = pd.read_csv(ENDURANCE_DERIVED_DIR / "multistop_plans.csv")
    assert (art["optimal_stops"] == art["min_stops"]).all()
    # Where the measured slope is positive, break-even is well above it.
    pos = art[art["net_slope_s"] > 0]
    assert (pos["breakeven_slope_s"] > pos["net_slope_s"]).all()
    assert (pos["slope_headroom_x"] >= 1.0).all()


@pytest.mark.skipif(not (ENDURANCE_DERIVED_DIR / "multistop_plans.csv").exists(),
                    reason="multistop artifact not generated")
def test_committed_multistop_plan_matches_a_fresh_dp() -> None:
    art = pd.read_csv(ENDURANCE_DERIVED_DIR / "multistop_plans.csv")
    row = art.iloc[0]
    fresh = optimal_stop_plan(int(row["race_laps"]), float(row["green_pace_s"]),
                              float(row["net_slope_s"]), float(row["pit_loss_s"]),
                              int(row["fuel_range_laps"]))
    assert fresh.n_stops == int(row["optimal_stops"])
    assert max(fresh.stint_lengths) <= int(row["fuel_range_laps"])
