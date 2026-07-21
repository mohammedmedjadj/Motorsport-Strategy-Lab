"""Endurance simulator: measured artifacts, the fuel constraint, and the two
real races behaving consistently with their Phase 1 degradation findings."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data.endurance_loader import EnduranceLoader
from src.degradation.endurance import build_endurance_frame, fit_endurance_degradation
from src.safety_car.endurance import (
    extract_events,
    fit_neutralisation_models,
    load_race_flags,
    race_timeline,
)
from src.simulator.endurance import (
    EnduranceScenario,
    build_race_model,
    estimate_fcy_pace_ratio,
    estimate_fuel_range,
    estimate_pit_loss,
    estimate_tyre_change_premium,
    simulate,
)


def test_tyre_change_premium_is_measured_from_stop_durations() -> None:
    """Fuel-only stops sit near a base duration; tyre-change stops add a known
    premium. The estimator must recover that premium as the median difference."""
    rows = []
    for i in range(20):
        rows.append({"is_pit_lap": True, "pit_time_s": 40.0 + (i % 3),
                     "is_tyre_change": False})
        rows.append({"is_pit_lap": True, "pit_time_s": 60.0 + (i % 3),
                     "is_tyre_change": True})
    prem = estimate_tyre_change_premium(pd.DataFrame(rows))
    assert prem.premium_s == pytest.approx(20.0, abs=1.0)
    assert prem.n_fuel_only == 20 and prem.n_tyre_change == 20


def test_tyre_change_premium_needs_both_stop_types() -> None:
    only_fuel = pd.DataFrame({"is_pit_lap": [True] * 5, "pit_time_s": [40.0] * 5,
                              "is_tyre_change": [False] * 5})
    with pytest.raises(ValueError, match="both fuel-only and tyre-change"):
        estimate_tyre_change_premium(only_fuel)

RACES = {
    "imsa": ("imsa", 2023, "Watkins Glen", "GTP"),
    "wec": ("wec", 2024, "Spa", "HYPERCAR"),
}


def _model(key: str):
    series, year, event, cls = RACES[key]
    laps = EnduranceLoader(series).load_laps(year, event, cls)
    fit = fit_endurance_degradation(build_endurance_frame(laps))
    timeline = race_timeline(load_race_flags())
    events = extract_events(timeline)
    posteriors = {(m.series, m.kind): m for m in fit_neutralisation_models(timeline, events)}
    fcy = posteriors[(series, "FCY")]
    sc = posteriors[(series, "SC")]
    fcy_durations = tuple(
        e.duration_laps for e in events if e.series == series and e.kind == "FCY"
    )
    sc_durations = tuple(
        e.duration_laps for e in events if e.series == series and e.kind == "SC"
    )
    model = build_race_model(
        laps, fit.net_slope.value, fit.net_slope.se,
        fcy.n_events + 0.5, fcy.laps_exposure, fcy_durations, fit.rmse_s,
        sc_alpha=sc.n_events + 0.5, sc_exposure=sc.laps_exposure,
        sc_durations=sc_durations,
    )
    return model, laps, fit


@pytest.fixture(scope="module")
def imsa():
    return _model("imsa")


@pytest.fixture(scope="module")
def wec():
    return _model("wec")


def test_measured_artifacts_are_physical(imsa, wec) -> None:
    for model, _, _ in (imsa, wec):
        # Endurance stops refuel and often change driver: far costlier than F1.
        assert 40.0 < model.pit_loss_s < 100.0
        assert model.n_pit_events >= 20
        # A neutralised lap is slower than a green one, by a lot in endurance.
        assert 1.5 < model.fcy_pace_ratio < 2.5
        assert 15 <= model.fuel_range_laps <= 40
        assert model.green_pace_s > 0


def test_pit_loss_trims_non_routine_stops(imsa) -> None:
    """A car sitting in the garage produces a multi-thousand-second 'stop';
    it must not drag the estimate."""
    _, laps, _ = imsa
    median, iqr, n = estimate_pit_loss(laps)
    raw = laps.loc[laps["is_pit_lap"], "pit_time_s"].dropna()
    assert median < 0.5 * float(raw.max())  # the outlier is gone
    assert iqr > 0 and n > 0


def test_fuel_range_caps_the_candidate_set(imsa) -> None:
    model, _, _ = imsa
    used = 5
    scenario = EnduranceScenario(
        current_lap=100, total_laps=201, tyre_age=5, laps_since_refuel=used
    )
    candidates = [c for c in scenario.candidate_pit_laps(model) if c != 0]
    # Cannot run beyond the fuel range: the last candidate is fuel-bound.
    assert max(candidates) == 100 + (model.fuel_range_laps - used)
    assert min(candidates) == 101


def test_no_stop_offered_only_when_fuel_reaches_the_flag(imsa) -> None:
    model, _, _ = imsa
    near_end = EnduranceScenario(
        current_lap=195, total_laps=201, tyre_age=10, laps_since_refuel=0
    )
    assert 0 in near_end.candidate_pit_laps(model)  # 6 laps left, tank covers it
    mid = EnduranceScenario(
        current_lap=100, total_laps=201, tyre_age=10, laps_since_refuel=0
    )
    assert 0 not in mid.candidate_pit_laps(model)  # 101 laps left, must stop


def test_exhausted_fuel_is_rejected(imsa) -> None:
    model, _, _ = imsa
    dry = EnduranceScenario(
        current_lap=100, total_laps=201, tyre_age=10,
        laps_since_refuel=model.fuel_range_laps,
    )
    with pytest.raises(ValueError, match="fuel already exhausted"):
        dry.candidate_pit_laps(model)


def test_simulation_is_a_valid_reproducible_distribution(wec) -> None:
    model, _, _ = wec
    scenario = EnduranceScenario(
        current_lap=70, total_laps=141, tyre_age=8, laps_since_refuel=8
    )
    a = simulate(scenario, model, n_draws=400, seed=3)
    b = simulate(scenario, model, n_draws=400, seed=3)
    assert a["p_best"].sum() == pytest.approx(1.0)
    assert (a["p10_s"] <= a["median_s"]).all() and (a["median_s"] <= a["p90_s"]).all()
    assert np.allclose(a["median_s"], b["median_s"])  # seeded, reproducible


def test_spa_optimum_is_pinned_by_the_fuel_constraint(wec) -> None:
    """Spa has a clearly positive net slope, so tyres want the stop near the
    middle of the 71 remaining laps (~lap 106). Fuel does not allow it: the tank
    runs out at lap 90, and the simulator lands exactly on that boundary. The
    binding constraint is fuel, not tyres — a situation F1 never faces."""
    model, _, fit = wec
    assert fit.net_slope.ci_low > 0
    scenario = EnduranceScenario(
        current_lap=70, total_laps=141, tyre_age=8, laps_since_refuel=8
    )
    fuel_bound = 70 + (model.fuel_range_laps - 8)
    table = simulate(scenario, model, n_draws=800, seed=7)
    best = int(table.loc[table["median_s"].idxmin(), "pit_lap"])
    assert best == fuel_bound == int(table["pit_lap"].max())
    assert table["p_best"].max() > 0.5  # and it is decisive about it


def test_watkins_glen_is_honestly_indifferent(imsa) -> None:
    """Watkins Glen's net slope covers zero, so no stop lap is meaningfully
    better: the spread across candidates must stay negligible relative to the
    race, rather than the model inventing a confident answer."""
    model, _, fit = imsa
    assert fit.net_slope.ci_low < 0 < fit.net_slope.ci_high
    scenario = EnduranceScenario(
        current_lap=100, total_laps=201, tyre_age=8, laps_since_refuel=8
    )
    table = simulate(scenario, model, n_draws=800, seed=7)
    spread = table["median_s"].max() - table["median_s"].min()
    # Under 0.5% of the remaining race time: not a distinguishable difference.
    assert spread / table["median_s"].median() < 0.005


def test_wec_measures_its_own_safety_car_pace_ratio(wec) -> None:
    """WEC has real SF-flagged laps, so the Safety Car ratio must be measured
    directly, not borrowed from FCY — and Phase 2 found SC is the *more*
    frequent neutralisation kind at Spa, so its alpha must reflect that."""
    model, _, _ = wec
    assert model.sc_ratio_measured is True
    assert 1.3 < model.sc_pace_ratio < 3.0
    assert model.sc_alpha > model.fcy_alpha  # more SC events than FCY at Spa


def test_imsa_falls_back_to_fcy_ratio_for_its_absent_safety_car(imsa) -> None:
    """IMSA has zero observed Safety Car events in 63 races (Phase 2), so its
    race has no SF laps to measure from: the model must fall back to the FCY
    ratio and say so via sc_ratio_measured, not silently invent a number."""
    model, _, _ = imsa
    assert model.sc_ratio_measured is False
    assert model.sc_pace_ratio == model.fcy_pace_ratio
    assert model.sc_alpha < model.fcy_alpha  # Jeffreys near-zero rate


def test_status_timeline_can_contain_both_neutralisation_kinds(wec) -> None:
    """With WEC's measured hazards, drawing enough laps must eventually surface
    both FCY and SC states, not just one — the whole point of modelling both."""
    from src.simulator.endurance import FCY, GREEN, SC, _sample_status

    model, _, _ = wec
    rng = np.random.default_rng(1)
    status = _sample_status(model, n_laps=200, n_draws=200, rng=rng)
    seen = set(np.unique(status).tolist())
    assert seen == {GREEN, FCY, SC}


def test_pace_ratio_and_fuel_range_reject_impossible_input() -> None:
    empty = pd.DataFrame({
        "series": [], "event": [], "car_class": [], "car": [], "lap": [],
        "lap_time_s": [], "is_green": [], "is_pit_lap": [], "flag": [],
    })
    with pytest.raises(ValueError):
        estimate_fcy_pace_ratio(empty)
    with pytest.raises(ValueError):
        estimate_fuel_range(empty)
