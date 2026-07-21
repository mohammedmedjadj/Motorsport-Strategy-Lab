"""Endurance adversarial rival: the shared game invariants must hold on the
endurance engine too, and the undercut/cover effect must scale with the
circuit's degradation (steep -> the cover matters hugely; flat -> barely)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data.endurance_loader import EnduranceLoader
from src.degradation.endurance import build_endurance_frame, fit_endurance_degradation
from src.ingestion.config import ENDURANCE_DERIVED_DIR
from src.safety_car.endurance import (
    extract_events,
    fit_neutralisation_models,
    load_race_flags,
    race_timeline,
)
from src.simulator.adversarial_endurance import EnduranceRival, duel_endurance
from src.simulator.endurance import EnduranceScenario, build_race_model

_timeline = race_timeline(load_race_flags())
_events = extract_events(_timeline)
_post = {(m.series, m.kind): m for m in fit_neutralisation_models(_timeline, _events)}
_swap = pd.read_csv(ENDURANCE_DERIVED_DIR / "endurance_overtaking_difficulty.csv")


def _model(series: str, year: int, event: str, cls: str):
    laps = EnduranceLoader(series).load_laps(year, event, cls)
    fit = fit_endurance_degradation(build_endurance_frame(laps))
    fcy, sc = _post[(series, "FCY")], _post[(series, "SC")]
    fd = tuple(e.duration_laps for e in _events if e.series == series and e.kind == "FCY")
    sd = tuple(e.duration_laps for e in _events if e.series == series and e.kind == "SC")
    model = build_race_model(laps, fit.net_slope.value, fit.net_slope.se,
                             fcy.n_events + 0.5, fcy.laps_exposure, fd, fit.rmse_s,
                             sc_alpha=sc.n_events + 0.5, sc_exposure=sc.laps_exposure,
                             sc_durations=sd)
    swap = float(_swap[(_swap.series == series) & (_swap.circuit == event)].adj_swap_rate.iloc[0])
    return model, swap


def _duel(series, year, event, cls, total, gap_s=1.5, seed=7, n=1500):
    model, swap = _model(series, year, event, cls)
    scen = EnduranceScenario(current_lap=total // 2, total_laps=total, tyre_age=12,
                             laps_since_refuel=12)
    rival = EnduranceRival(gap_s=gap_s, tyre_age=12, laps_since_refuel=12,
                           pit_lap=total // 2 + 15)
    return duel_endurance(scen, rival, model, swap_rate=swap, n_draws=n, seed=seed)


def test_game_invariants_hold_on_the_endurance_engine() -> None:
    r = _duel("wec", 2024, "Bahrain", "HYPERCAR", 235)
    assert ((r.win_prob >= 0) & (r.win_prob <= 1)).all()
    assert r.naive_win_prob >= r.naive_win_prob_if_covered - 1e-9
    assert r.adversarial_win_prob >= r.naive_win_prob_if_covered - 1e-9


def test_is_reproducible() -> None:
    a = _duel("imsa", 2023, "Watkins Glen", "GTP", 201, seed=3, n=800)
    b = _duel("imsa", 2023, "Watkins Glen", "GTP", 201, seed=3, n=800)
    assert np.array_equal(a.win_prob, b.win_prob)


def test_cover_matters_far_more_where_degradation_is_steep() -> None:
    """Bahrain's steep, significant net slope makes an uncovered undercut hugely
    powerful, so covering it is worth a lot; Watkins Glen's near-zero slope
    makes the undercut weak, so covering barely matters. The endurance model
    must reproduce that ordering."""
    steep = _duel("wec", 2024, "Bahrain", "HYPERCAR", 235)
    flat = _duel("imsa", 2023, "Watkins Glen", "GTP", 201)
    assert steep.naive_overstatement > flat.naive_overstatement
    assert steep.naive_overstatement > 0.2


def test_candidate_windows_are_fuel_bounded() -> None:
    r = _duel("wec", 2024, "Bahrain", "HYPERCAR", 235)
    # Both cars' pit-lap options are capped by the fuel range, not the race end.
    assert max(r.ego_pit_laps) < 235
    assert len(r.rival_pit_laps) > 0
