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
    deterministic_time,
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
    assert opt.deterministic_time_s <= deterministic_time(naive, **args) + 1e-6


def test_deterministic_time_reproduces_the_dp_objective() -> None:
    """Scoring the optimum by hand must return exactly what the DP minimised —
    otherwise the baseline is being compared on a different objective than the
    one it is supposed to lose to."""
    args = dict(green_pace_s=93.0, net_slope_s=0.0135, pit_loss_s=79.0)
    opt = optimal_stop_plan(213, fuel_range_laps=42, **args)
    assert deterministic_time(opt, **args) == pytest.approx(opt.deterministic_time_s)


def test_an_unscored_plan_says_so_instead_of_claiming_zero() -> None:
    """``min_stops_plan`` has no pace inputs, so it cannot know its own time.

    Pinned because the previous placeholder was ``0.0``: comparing a baseline
    against the optimum by that field silently reported the baseline as
    finishing the race instantly, i.e. as beating every real plan.
    """
    naive = min_stops_plan(213, 42)
    assert naive.deterministic_time_s is None
    assert deterministic_time(naive, 93.0, 0.0135, 79.0) > 0.0


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
        green_pace_s=130.0, lap_noise_s=0.8,
        # df=inf keeps this toy model's slope Gaussian: the t degrees of
        # freedom are a property of a real fit's cluster count, and inventing
        # one here would make the fixture assert something it does not test.
        net_slope_s=0.04, net_slope_se=0.01, net_slope_df=float("inf"),
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
def test_tyre_limited_racing_needs_a_cheap_stop_and_real_degradation() -> None:
    """The cross-series rule, replacing a narrower claim that read as a fact
    about cars (``reports/when_tyres_beat_fuel.md``).

    Two conditions, both necessary and neither sufficient:

    1. **A cheap stop.** No entry with a pit loss above ~22.5 s is
       tyre-limited anywhere in 66 circuit-class entries across four series.
       A Hypercar stop costs 60-91 s, which buys some 2,000 laps of
       degradation at a typical slope -- no tyre repays that.
    2. **Degradation to escape.** Among the cheap-stop entries, the
       tyre-limited ones carry visibly steeper slopes than the rest.

    This test used to assert "GT3 is tyre-limited, prototypes are not". That
    was true of the rows and false as an explanation: condition on stop cost
    and the split happens inside every class, GTP and LMP2 included. GT3
    dominated the list only because GT3 racing is where cheap stops are
    common.
    """
    from scipy import stats

    art = pd.read_csv(ENDURANCE_DERIVED_DIR / "multistop_plans.csv")
    art["tyre_limited"] = art["optimal_stops"] != art["min_stops"]
    assert (art["optimal_stops"] >= art["min_stops"]).all()
    tyre, fuel = art[art["tyre_limited"]], art[~art["tyre_limited"]]
    assert len(tyre) >= 5, "the finding needs some positives to be about"

    # 1. the hard edge: an expensive stop is never worth an extra visit
    assert tyre["pit_loss_s"].max() < fuel["pit_loss_s"].max()
    assert tyre["pit_loss_s"].median() < 0.5 * fuel["pit_loss_s"].median()
    assert stats.mannwhitneyu(tyre["pit_loss_s"], fuel["pit_loss_s"]).pvalue < 0.01

    # ... and it is necessary, not sufficient
    cheap = art[art["pit_loss_s"] <= tyre["pit_loss_s"].max()]
    assert (~cheap["tyre_limited"]).any(), (
        "if every cheap-stop entry were tyre-limited the stop cost would be "
        "the whole story, and condition 2 below would be untestable"
    )

    # 2. among cheap stops, degradation decides
    assert stats.mannwhitneyu(
        cheap[cheap["tyre_limited"]]["net_slope_s"],
        cheap[~cheap["tyre_limited"]]["net_slope_s"],
    ).pvalue < 0.05

    # 3. the class is a proxy, not the mechanism: the split occurs in more
    # than one class once stop cost is held down.
    classes_split = {
        c for c, g in cheap.groupby("car_class") if g["tyre_limited"].any()
    }
    assert len(classes_split) >= 3, (
        f"only {classes_split} split on cheap stops; if the effect collapsed "
        "into one class the class-as-proxy reading would need revisiting"
    )


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
