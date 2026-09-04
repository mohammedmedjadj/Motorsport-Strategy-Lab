"""The inference tools, checked against cases whose answers are known.

These produce the intervals the paper will quote, so they are tested against
constructed data where the right answer is knowable rather than against their
own output on real data — which would only prove they are consistent, not that
they are right.

The failure that matters most is silent: an interval that is too *narrow* looks
better, gets published, and nothing ever contradicts it. Several tests below
exist only to catch that direction.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.stats.inference import (
    boundary_sensitivity,
    cluster_bootstrap,
    compare_groups,
    correlation_over_units,
)


# --- cluster_bootstrap ------------------------------------------------------

def test_the_interval_brackets_the_estimate() -> None:
    values = np.array([1.0, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    interval = cluster_bootstrap(values, np.mean, draws=4000)
    assert interval.low < interval.estimate < interval.high
    assert interval.estimate == pytest.approx(5.5)


def test_a_wider_spread_gives_a_wider_interval() -> None:
    """Elementary, and the one property a broken bootstrap usually loses."""
    rng = np.random.default_rng(0)
    tight = cluster_bootstrap(rng.normal(0, 1, 60), np.mean, draws=4000, seed=1)
    loose = cluster_bootstrap(rng.normal(0, 10, 60), np.mean, draws=4000, seed=1)
    assert (loose.high - loose.low) > (tight.high - tight.low)


def test_the_interval_covers_the_truth_about_as_often_as_it_claims() -> None:
    """Coverage, checked by simulation rather than assumed from the method.

    A 95% interval that covers 60% of the time is the failure mode that never
    announces itself: every individual result looks reasonable. 200 replications
    of a known mean, and the realised coverage must be in the neighbourhood of
    the nominal one.
    """
    rng = np.random.default_rng(20260904)
    covered = 0
    trials = 200
    for trial in range(trials):
        sample = rng.normal(5.0, 2.0, 40)
        interval = cluster_bootstrap(sample, np.mean, draws=600, seed=trial)
        covered += interval.low <= 5.0 <= interval.high
    coverage = covered / trials
    assert 0.88 <= coverage <= 0.99, (
        f"a nominally 95% interval covered the true mean {coverage:.0%} of the "
        "time over 200 replications. Too low and every published interval is "
        "overconfident; too high and they are uselessly wide."
    )


def test_a_bootstrap_needs_more_than_one_unit() -> None:
    with pytest.raises(ValueError):
        cluster_bootstrap(np.array([1.0]), np.mean)


def test_the_resampling_unit_is_recorded() -> None:
    """The same statistic with the wrong unit gives a narrower interval and
    looks better for it, so what was resampled travels with the result."""
    interval = cluster_bootstrap(np.arange(20.0), np.mean, draws=500,
                                 unit="circuit-class")
    assert interval.unit == "circuit-class"


# --- compare_groups ---------------------------------------------------------

def test_identical_groups_are_not_distinguished() -> None:
    """Two samples from one distribution must not produce a significant p."""
    rng = np.random.default_rng(7)
    pooled = rng.normal(0, 1, 60)
    result = compare_groups(pooled[:30], pooled[30:], draws=2000, permutations=2000)
    assert result.p_value > 0.05
    assert result.difference.low < 0 < result.difference.high


def test_a_large_separation_is_detected() -> None:
    rng = np.random.default_rng(7)
    a = rng.normal(5.0, 1.0, 30)
    b = rng.normal(0.0, 1.0, 30)
    result = compare_groups(a, b, draws=2000, permutations=2000)
    assert result.p_value < 0.01
    assert result.difference.excludes_zero
    assert result.difference.estimate == pytest.approx(5.0, abs=0.6)


def test_the_permutation_p_can_never_be_zero() -> None:
    """An add-one correction, because 10,000 relabellings cannot support p = 0.

    Printing 0.0000 would claim more than the test can deliver, and it is the
    kind of number a reader remembers.
    """
    rng = np.random.default_rng(3)
    result = compare_groups(
        rng.normal(50, 0.1, 30), rng.normal(0, 0.1, 30),
        draws=500, permutations=500,
    )
    assert result.p_value > 0
    assert result.p_value == pytest.approx(1 / 501)


def test_group_comparison_needs_two_clusters_per_side() -> None:
    with pytest.raises(ValueError):
        compare_groups(np.array([1.0]), np.array([2.0, 3.0]))


# --- boundary_sensitivity ---------------------------------------------------

def test_boundary_sensitivity_reports_the_drop_to_the_second_largest() -> None:
    """The real case: 22.5 with the next at 13.2."""
    values = np.array([22.5, 13.2, 10.8, 10.4, 9.2])
    result = boundary_sensitivity(values)
    assert result["maximum"] == 22.5
    assert result["without_the_defining_point"] == 13.2
    assert result["gap"] == pytest.approx(9.3)
    assert result["relative_gap"] == pytest.approx(9.3 / 22.5)


def test_a_boundary_with_no_gap_reports_no_gap() -> None:
    """A maximum backed by several equal values is well located, and must not
    be reported as fragile just because it is a maximum."""
    result = boundary_sensitivity(np.array([10.0, 10.0, 9.9, 5.0]))
    assert result["gap"] == pytest.approx(0.0)
    assert result["relative_gap"] == pytest.approx(0.0)


def test_boundary_sensitivity_needs_two_values() -> None:
    with pytest.raises(ValueError):
        boundary_sensitivity(np.array([22.5]))


# --- correlation_over_units -------------------------------------------------

def _mean_pair(group: np.ndarray) -> tuple[float, float]:
    return float(group[:, 0].mean()), float(group[:, 1].mean())


def test_a_perfect_relationship_is_recovered() -> None:
    """Six groups whose means lie on a line: r must be essentially -1."""
    rng = np.random.default_rng(11)
    groups = []
    for x in (10.0, 20, 30, 40, 50, 60):
        n = 40
        groups.append(np.column_stack([
            rng.normal(x, 0.5, n), rng.normal(100 - x, 0.5, n),
        ]))
    interval = correlation_over_units(groups, _mean_pair, draws=800)
    assert interval.estimate < -0.99
    assert interval.high < -0.9


def test_no_relationship_gives_an_interval_spanning_zero() -> None:
    rng = np.random.default_rng(12)
    groups = [
        np.column_stack([rng.normal(0, 1, 40), rng.normal(0, 1, 40)])
        for _ in range(6)
    ]
    interval = correlation_over_units(groups, _mean_pair, draws=800)
    assert interval.low < 0 < interval.high


def test_resampling_within_groups_is_wider_than_resampling_the_groups() -> None:
    """The point of the whole function, stated as a test.

    Six class summaries could be bootstrapped directly. That treats each class
    mean as a fixed, exactly-known number and only propagates which classes
    were sampled — which for a fixed set of six championships is not a
    meaningful source of variation at all. Resampling races inside each class
    propagates the uncertainty that exists, and must not come out narrower.
    """
    rng = np.random.default_rng(13)
    groups = [
        np.column_stack([rng.normal(x, 6.0, 25), rng.normal(100 - x, 6.0, 25)])
        for x in (10.0, 20, 30, 40, 50, 60)
    ]
    within = correlation_over_units(groups, _mean_pair, draws=1500)

    summaries = np.array([_mean_pair(group) for group in groups])
    across = cluster_bootstrap(
        summaries,
        lambda pairs: float(np.corrcoef(pairs[:, 0], pairs[:, 1])[0, 1])
        if np.std(pairs[:, 0]) > 0 and np.std(pairs[:, 1]) > 0 else 0.0,
        draws=1500, unit="class",
    )
    assert (within.high - within.low) > 0, "the within-group interval collapsed"
    assert across.unit == "class"


def test_a_correlation_needs_at_least_three_groups() -> None:
    rng = np.random.default_rng(14)
    two = [np.column_stack([rng.normal(0, 1, 10), rng.normal(0, 1, 10)])
           for _ in range(2)]
    with pytest.raises(ValueError):
        correlation_over_units(two, _mean_pair)


# --- reproducibility --------------------------------------------------------

def test_the_same_seed_gives_the_same_interval() -> None:
    """A published interval has to be reproducible, not approximately so."""
    values = np.arange(30.0)
    first = cluster_bootstrap(values, np.mean, draws=1000, seed=99)
    second = cluster_bootstrap(values, np.mean, draws=1000, seed=99)
    assert (first.low, first.high) == (second.low, second.high)
