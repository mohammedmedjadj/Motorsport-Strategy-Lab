"""Endurance neutralisation extraction and posteriors, on the full committed
96-race flag set plus synthetic timelines with known answers."""

from __future__ import annotations

import pandas as pd
import pytest

from src.safety_car.endurance import (
    NEUTRALISATION_FLAGS,
    RACE_KEY,
    extract_events,
    fit_neutralisation_models,
    fit_neutralisation_models_by_circuit,
    load_race_flags,
    race_exposure,
    race_timeline,
)


def _timeline(flags: list[str], series: str = "imsa") -> pd.DataFrame:
    """One synthetic race whose modal flag per lap is exactly ``flags``."""
    rows = [
        {"series_code": series, "year": 2024, "event": "Synthetic", "session_id": 1,
         "lap": i + 1, "flags": f, "car_laps": 10}
        for i, f in enumerate(flags)
    ]
    return race_timeline(pd.DataFrame(rows))


@pytest.fixture(scope="module")
def real_timeline() -> pd.DataFrame:
    return race_timeline(load_race_flags())


def test_contiguous_runs_become_single_events() -> None:
    events = extract_events(_timeline(["GF", "FCY", "FCY", "FCY", "GF", "FCY", "GF"]))
    assert [(e.kind, e.start_lap, e.duration_laps) for e in events] == [
        ("FCY", 2, 3), ("FCY", 6, 1)
    ]


def test_finish_and_red_flags_are_not_neutralisations() -> None:
    """FF is the chequered flag and RF is too rare to model — neither may leak
    into the event list."""
    events = extract_events(_timeline(["GF", "RF", "GF", "FF"]))
    assert events == []
    assert "FF" not in NEUTRALISATION_FLAGS and "RF" not in NEUTRALISATION_FLAGS


def test_safety_car_flag_maps_to_its_own_kind() -> None:
    events = extract_events(_timeline(["GF", "SF", "SF", "GF", "FCY"], series="wec"))
    assert sorted((e.kind, e.duration_laps) for e in events) == [("FCY", 1), ("SC", 2)]


def test_adjacent_different_kinds_do_not_merge() -> None:
    events = extract_events(_timeline(["FCY", "SF", "SF"], series="wec"))
    assert [(e.kind, e.duration_laps) for e in events] == [("FCY", 1), ("SC", 2)]


def test_exposure_is_the_race_length() -> None:
    exposure = race_exposure(_timeline(["GF"] * 40))
    assert int(exposure["laps"].iloc[0]) == 40


def test_real_data_covers_every_race(real_timeline) -> None:
    assert real_timeline.groupby(RACE_KEY).ngroups == 96
    assert set(real_timeline["series_code"].unique()) == {"imsa", "wec"}


def test_imsa_fcy_is_near_certain_and_imsa_has_no_safety_car(real_timeline) -> None:
    """The headline contrast between the series, and the zero-count case the
    Jeffreys prior exists to handle."""
    events = extract_events(real_timeline)
    models = {(m.series, m.kind): m for m in fit_neutralisation_models(real_timeline, events)}

    imsa_fcy = models[("imsa", "FCY")]
    assert imsa_fcy.occurrence.mean > 0.9
    assert imsa_fcy.occurrence.ci_low > 0.85

    # IMSA never shows the WEC Safety Car flag: the posterior must stay near
    # zero with a finite upper bound rather than collapsing to exactly 0.
    imsa_sc = models[("imsa", "SC")]
    assert imsa_sc.n_events == 0
    assert 0 < imsa_sc.occurrence.mean < 0.05
    assert imsa_sc.occurrence.ci_high < 0.10


def test_wec_uses_safety_car_more_than_fcy(real_timeline) -> None:
    events = extract_events(real_timeline)
    models = {(m.series, m.kind): m for m in fit_neutralisation_models(real_timeline, events)}
    assert models[("wec", "SC")].n_events > models[("wec", "FCY")].n_events
    assert models[("wec", "SC")].occurrence.mean > models[("wec", "FCY")].occurrence.mean


def test_every_race_counts_in_the_denominator(real_timeline) -> None:
    """Races without the event still count — otherwise probabilities inflate."""
    events = extract_events(real_timeline)
    for m in fit_neutralisation_models(real_timeline, events):
        assert m.n_races_with_event <= m.n_races
        assert m.laps_exposure > 0
        assert m.occurrence.n_observations == m.n_races


def test_empty_timeline_is_rejected() -> None:
    with pytest.raises(ValueError, match="no flag rows"):
        race_timeline(pd.DataFrame())


def test_per_circuit_models_have_a_real_multi_season_sample(real_timeline) -> None:
    """Scoped circuits must each have several seasons of exposure in
    race_flags.csv, comparable to the F1 phase's 6-8 editions per circuit —
    not just the single season materialised for degradation/simulator work."""
    events = extract_events(real_timeline)
    models = fit_neutralisation_models_by_circuit(real_timeline, events)
    scoped = {
        ("imsa", "Watkins Glen"), ("imsa", "Sebring"),
        ("imsa", "Mosport"), ("imsa", "Road America"),
        ("wec", "Spa"), ("wec", "Fuji"), ("wec", "Bahrain"), ("wec", "Imola"),
    }
    by_circuit = {(m.series, m.event) for m in models}
    assert scoped <= by_circuit
    for series, event in scoped:
        n_races = {m.n_races for m in models if (m.series, m.event) == (series, event)}
        assert n_races.pop() >= 3


def test_wec_safety_car_is_circuit_specific_not_series_wide(real_timeline) -> None:
    """WEC's SC/FCY balance is not uniform across circuits: Spa leans SC far
    more heavily than the series-wide pool alone would suggest."""
    events = extract_events(real_timeline)
    models = {
        (m.series, m.event, m.kind): m
        for m in fit_neutralisation_models_by_circuit(real_timeline, events)
    }
    spa_sc = models[("wec", "Spa", "SC")]
    spa_fcy = models[("wec", "Spa", "FCY")]
    assert spa_sc.occurrence.mean > spa_fcy.occurrence.mean
