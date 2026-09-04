"""Worked examples for the three baseline rules, checked by hand.

These are the yardstick the whole audit is measured against, so they are tested
against arithmetic done on paper rather than against their own output. A
baseline with a bug does not fail loudly — it produces a plausible lap number
and quietly decides whether the exact optimiser looks worth its complexity.
"""

from __future__ import annotations

import math

import pytest

from src.audit.baselines import (
    Recommendation,
    cumulative_degradation_s,
    fixed_interval,
    fuel_deadline,
    threshold,
    threshold_age,
)


# --- B1 ---------------------------------------------------------------------

def test_fixed_interval_splits_the_race_evenly() -> None:
    """A one-stop plan over 58 laps stops at half distance."""
    assert fixed_interval(58, n_stops=1).lap == 29
    # Two stops make three stints: 57/3 = 19 and 38.
    assert fixed_interval(57, n_stops=2, which=1).lap == 19
    assert fixed_interval(57, n_stops=2, which=2).lap == 38


def test_fixed_interval_rounds_rather_than_truncates() -> None:
    """53 laps, one stop: 26.5 -> 26 (banker's rounding), not 26 by truncation.

    Pinned because the two agree here by luck and diverge elsewhere, and a
    silent switch between them would move a whole column of the results table
    by one lap.
    """
    assert fixed_interval(53, n_stops=1).lap == 26
    assert fixed_interval(55, n_stops=1).lap == 28  # 27.5 -> 28


def test_fixed_interval_refuses_impossible_plans() -> None:
    assert not fixed_interval(0, n_stops=1).is_defined
    assert not fixed_interval(58, n_stops=0).is_defined
    assert not fixed_interval(58, n_stops=1, which=2).is_defined


# --- the quantity B2 turns on -----------------------------------------------

def test_cumulative_degradation_is_the_triangular_sum() -> None:
    """A 0.10 s/lap tyre, 10 laps old, has cost 0.10 x (1+..+10) = 5.5 s."""
    assert cumulative_degradation_s(0.10, 10) == pytest.approx(5.5)
    assert cumulative_degradation_s(0.10, 0) == 0.0
    assert cumulative_degradation_s(0.10, -3) == 0.0


def test_the_triangular_sum_is_not_the_integral() -> None:
    """They differ by slope x age / 2, which is why the exact form is used.

    Over a 40-lap stint at 0.05 s/lap that is a full second — small against a
    22 s pit loss, but this is the only quantity the rule compares to it.
    """
    slope, age = 0.05, 40
    integral = slope * age**2 / 2
    assert cumulative_degradation_s(slope, age) - integral == pytest.approx(
        slope * age / 2
    )


# --- B2 ---------------------------------------------------------------------

def test_threshold_fires_on_the_first_lap_the_tyre_has_cost_more_than_the_stop() -> None:
    """Slope 0.10, pit loss 5.5 s: age 10 costs exactly 5.5, so it fires at 11.

    The condition is strictly *greater than*, so the lap where the loss equals
    the pit loss is not yet worth stopping for.
    """
    # Stint starts fresh at the decision lap, so age tracks laps since then.
    result = threshold(
        decision_lap=1, tyre_age_at_decision=0,
        slope_s_per_lap=0.10, pit_loss_s=5.5, race_laps=60,
    )
    # age 10 is reached on lap 11 (age 0 on lap 1); 5.5 is not > 5.5, so lap 12.
    assert result.lap == 12
    assert cumulative_degradation_s(0.10, 10) == pytest.approx(5.5)
    assert cumulative_degradation_s(0.10, 11) > 5.5


def test_threshold_accounts_for_a_tyre_that_is_already_worn() -> None:
    """The rule reads the age it is given, not the laps since the decision."""
    fresh = threshold(20, 0, 0.10, 5.5, 60)
    worn = threshold(20, 8, 0.10, 5.5, 60)
    assert worn.lap is not None and fresh.lap is not None
    assert worn.lap < fresh.lap, (
        "a tyre eight laps into its life must reach the threshold sooner than "
        "a fresh one fitted at the same lap"
    )
    assert worn.lap == 23  # age 11 first exceeds 5.5, reached on lap 20+3


def test_threshold_says_do_not_stop_rather_than_stopping_at_the_flag() -> None:
    """A durable tyre and an expensive stop means the rule declines to fire."""
    result = threshold(10, 0, 0.001, 60.0, 50)
    assert not result.is_defined
    assert "never exceeds" in (result.undefined_reason or "")


def test_threshold_refuses_a_non_positive_slope() -> None:
    """A tyre that does not degrade can never repay a stop, and saying so is
    the answer — not a lap number produced by an infinite loop guard."""
    assert not threshold(10, 0, 0.0, 22.0, 60).is_defined
    assert not threshold(10, 0, -0.05, 22.0, 60).is_defined


def test_threshold_leaves_a_final_stint() -> None:
    """It must not recommend a stop with two laps left."""
    result = threshold(10, 0, 0.001, 0.001, 50, min_final_stint=3)
    assert result.lap is None or result.lap <= 47


def test_threshold_age_matches_the_lap_the_rule_actually_fires_on() -> None:
    """Closed form and loop must agree, or one of them is wrong.

    Checked across a spread of realistic slopes and pit losses rather than one
    pair, because the closed form solves the continuous equation and the loop
    walks integers — they agree only if the algebra is right.

    Exact ties are allowed to go either way, and that is not a fudge. When the
    closed form lands on a whole number the accumulated tyre loss *equals* the
    pit loss, and the rule is genuinely indifferent: stopping and staying out
    cost the same. Which side floating point falls on is arbitrary — slope 0.20
    against a 60 s pit loss computes 60.000000000000014 and fires, while the
    same quantity in exact arithmetic would not. A tolerance would not remove
    the arbitrariness, only move it, so the tie is stated instead.
    """
    for slope in (0.02, 0.05, 0.10, 0.20):
        for pit_loss in (5.0, 22.0, 60.0):
            age = threshold_age(slope, pit_loss)
            fires_at = threshold(1, 0, slope, pit_loss, race_laps=2000)
            assert fires_at.is_defined
            fired_age = fires_at.lap - 1
            exact_tie = abs(age - round(age)) < 1e-9
            expected = {math.floor(age) + 1} | ({round(age)} if exact_tie else set())
            assert fired_age in expected, (
                f"slope {slope}, pit loss {pit_loss}: closed form says age "
                f"{age:.6f}, loop fired at age {fired_age}, expected one of "
                f"{sorted(expected)}"
            )


# --- B3 ---------------------------------------------------------------------

def test_fuel_deadline_returns_the_deadline() -> None:
    assert fuel_deadline(34).lap == 34


def test_fuel_deadline_is_undefined_where_refuelling_is_banned() -> None:
    """F1 has not refuelled since 2010. The rule does not exist there.

    It must not fall back to the race end: that would put a number in the
    results table for a rule nobody could follow, and the table would read as
    though F1 had been measured on all three baselines.
    """
    result = fuel_deadline(58, refuelling_allowed=False)
    assert not result.is_defined
    assert "no refuelling" in (result.undefined_reason or "")


def test_fuel_deadline_is_undefined_without_a_measured_range() -> None:
    assert not fuel_deadline(None).is_defined
    assert not fuel_deadline(0).is_defined


# --- the contract every baseline shares -------------------------------------

@pytest.mark.parametrize(
    "result",
    [
        fixed_interval(58, 1),
        fixed_interval(0, 1),
        threshold(10, 0, 0.05, 22.0, 60),
        threshold(10, 0, 0.0, 22.0, 60),
        fuel_deadline(34),
        fuel_deadline(None),
    ],
    ids=["b1-ok", "b1-undefined", "b2-ok", "b2-undefined", "b3-ok", "b3-undefined"],
)
def test_an_undefined_recommendation_always_says_why(result: Recommendation) -> None:
    """No silent defaults. Either a lap, or a stated reason there is none."""
    if result.is_defined:
        assert result.undefined_reason is None
        assert result.lap is not None and result.lap > 0
    else:
        assert result.undefined_reason, (
            "a baseline declined to answer without saying why, so the "
            "comparison table cannot report whether it was inapplicable or "
            "simply broken"
        )
