"""Smoke test: the extensions demo runs end-to-end on committed data and every
block produces output. Uses small draw counts to stay fast."""

from __future__ import annotations

from scripts import demo_extensions as demo


def test_monte_carlo_block_runs() -> None:
    lines = demo.demo_monte_carlo(circuit="barcelona", n_draws=200)
    assert any("MC" in line for line in lines) and len(lines) >= 3


def test_pareto_block_runs() -> None:
    lines = demo.demo_pareto(circuit="barcelona", n_draws=300)
    assert any("non-dominated" in line for line in lines)


def test_gp_vs_ols_block_runs() -> None:
    lines = demo.demo_gp_vs_ols(circuit="suzuka")
    assert any("OLS mean CV RMSE" in line for line in lines)


def test_kalman_block_runs() -> None:
    lines = demo.demo_kalman(circuit="suzuka")
    assert any("slope final" in line for line in lines)
