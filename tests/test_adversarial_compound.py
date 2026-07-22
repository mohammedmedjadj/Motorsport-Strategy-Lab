"""The compound-aware rival: a strictly richer covering strategy space than the
lap-only duel, so a frozen-rival simulator can only be *more* optimistic against
it — the game-theoretic invariant, plus reproducibility and well-formedness."""

from __future__ import annotations

import numpy as np

from src.simulator.adversarial import duel, duel_multi_compound
from src.simulator.artifacts import load_circuit_models
from src.simulator.engine import RivalSpec, Scenario

MODELS = load_circuit_models()


def _scenario():
    rival = RivalSpec("R", gap_s=1.5, compound="MEDIUM", tyre_age=22,
                      pit_lap=48, target_compound="HARD")
    scen = Scenario("barcelona", current_lap=38, total_laps=66, compound="MEDIUM",
                    tyre_age=22, target_compound="HARD", rivals=(rival,))
    return scen, rival


def test_reproducible_and_well_formed() -> None:
    scen, rival = _scenario()
    a = duel_multi_compound(scen, rival, MODELS["barcelona"], swap_rate=0.02,
                            n_draws=600, seed=3)
    b = duel_multi_compound(scen, rival, MODELS["barcelona"], swap_rate=0.02,
                            n_draws=600, seed=3)
    assert np.array_equal(a.win_prob, b.win_prob)
    n_comp = len(MODELS["barcelona"].degradation)
    assert a.win_prob.shape == (len(a.ego_pit_laps), len(a.ego_pit_laps) * n_comp)
    assert ((a.win_prob >= 0) & (a.win_prob <= 1)).all()
    assert a.rival_cover_strategy[1] in MODELS["barcelona"].degradation


def test_richer_rival_covers_at_least_as_well() -> None:
    """The invariant: the compound-aware rival's strategy set contains the
    lap-only rival's, so it covers at least as effectively — the frozen-rival
    plan's overstatement can only grow, never shrink, under seed-matched draws."""
    scen, rival = _scenario()
    m = MODELS["barcelona"]
    lap_only = duel(scen, rival, m, swap_rate=0.02, n_draws=1200, seed=5)
    multi = duel_multi_compound(scen, rival, m, swap_rate=0.02, n_draws=1200, seed=5)
    assert multi.naive_overstatement >= lap_only.naive_overstatement - 1e-9


def test_cover_strategy_is_a_real_menu_entry() -> None:
    scen, rival = _scenario()
    multi = duel_multi_compound(scen, rival, MODELS["barcelona"], swap_rate=0.02,
                                n_draws=600, seed=1)
    assert multi.rival_cover_strategy in multi.rival_strategies
