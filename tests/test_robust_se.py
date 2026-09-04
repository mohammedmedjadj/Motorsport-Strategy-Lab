"""Cluster-robust standard errors: does the estimator actually do its job?

These are coverage tests, not agreement tests. A standard error is a claim
about how often an interval contains the truth, so the only honest way to
check one is to generate data with a known truth and count. Both directions
are pinned:

- with independent errors, the robust estimator must not cost anything
  (it agrees with the classical one, and both cover ~95%);
- with clustered errors, the classical estimator must visibly *fail* to
  cover while the robust one holds. Asserting the failure matters as much
  as asserting the fix: it is what makes the change to the real fits a
  correction rather than a preference.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.degradation.robust import cluster_robust_se, critical_value

TRUE_SLOPE = 0.05  # s per lap of tyre age, the order of magnitude we fit


def _panel(
    rng: np.random.Generator, n_groups: int, per_group: int, slope_sd: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """One panel of laps: group intercepts, and a slope that *varies by group*
    around ``TRUE_SLOPE`` with spread ``slope_sd``.

    The varying slope is the point. A group-level shock to the *level* is
    absorbed wholesale by the group fixed effects and leaves the slope's
    standard error untouched — a first attempt at this test used one and the
    classical interval covered 97%, correctly. What actually breaks classical
    inference is structure that moves *with the regressor*: a car whose tyres
    genuinely degrade faster than the field's average degrades faster on every
    lap of the stint. Then the information about the population slope is
    carried by the number of *cars*, not the number of laps, and an estimator
    that counts laps is confident by a factor of roughly sqrt(laps per car).

    ``slope_sd=0`` is the textbook independent case.
    """
    groups = np.repeat(np.arange(n_groups), per_group)
    age = np.tile(np.arange(per_group, dtype=float), n_groups)
    fe = np.eye(n_groups)[groups]
    X = np.hstack([fe, age[:, None]])
    group_slope = rng.normal(TRUE_SLOPE, slope_sd, size=n_groups)[groups]
    y = fe @ rng.normal(90.0, 1.0, n_groups) + group_slope * age
    y = y + rng.normal(0.0, 0.3, size=y.size)
    return X, y, groups


def _coverage(slope_sd: float, n_reps: int = 300, seed: int = 7) -> tuple[float, float]:
    """(classical, robust) coverage of the slope's 95% interval."""
    rng = np.random.default_rng(seed)
    hits_classical = hits_robust = 0
    for _ in range(n_reps):
        X, y, groups = _panel(rng, n_groups=30, per_group=12, slope_sd=slope_sd)
        beta, _, rank, _ = np.linalg.lstsq(X, y, rcond=None)
        resid = y - X @ beta
        s2 = float(resid @ resid) / max(len(y) - rank, 1)
        classical = float(np.sqrt(max(np.linalg.pinv(X.T @ X)[-1, -1] * s2, 0.0)))
        robust, n_clusters = cluster_robust_se(X, y, beta, groups)
        slope = beta[-1]

        if abs(slope - TRUE_SLOPE) <= 1.96 * classical:
            hits_classical += 1
        if abs(slope - TRUE_SLOPE) <= critical_value(n_clusters) * robust[-1]:
            hits_robust += 1
    return hits_classical / n_reps, hits_robust / n_reps


def test_independent_errors_cost_nothing() -> None:
    """With i.i.d. errors both estimators are valid, so switching to the
    robust one must not be paid for in lost coverage."""
    classical, robust = _coverage(slope_sd=0.0)
    assert classical == pytest.approx(0.95, abs=0.04)
    assert robust == pytest.approx(0.95, abs=0.04)


def test_varying_slopes_break_the_classical_interval() -> None:
    """The failure this change exists to fix.

    ``slope_sd=0.04`` is not a stress test, and `test_the_chosen_spread_is_
    conservative` below checks that against the fitted coefficients rather than
    asserting it. This docstring used to name the range as "+0.015 (Monaco
    HARD) to +0.081 (Suzuka SOFT)" from a four-circuit scope; at twenty-five it
    is far wider, which makes 0.04 conservative rather than merely realistic.

    At it, the classical 95% interval covers 75% of the time while the
    cluster-robust one holds 95%.
    """
    classical, robust = _coverage(slope_sd=0.04)
    assert classical < 0.85, f"classical interval unexpectedly held ({classical:.2f})"
    assert robust > 0.90, f"robust interval failed to cover ({robust:.2f})"


def test_the_failure_grows_with_how_much_slopes_vary() -> None:
    """Monotone degradation of the classical interval, so the previous test
    is a point on a curve rather than a lucky constant."""
    coverage = [_coverage(slope_sd=sd)[0] for sd in (0.0, 0.02, 0.04)]
    assert coverage[0] > coverage[1] > coverage[2]


def test_robust_se_matches_classical_when_every_lap_is_its_own_cluster() -> None:
    """Degenerate check on the estimator itself: with one observation per
    cluster the sandwich reduces to the heteroscedasticity-robust (HC1) form,
    which for homoscedastic data must land near the classical value. Guards
    against an error in the finite-sample correction."""
    rng = np.random.default_rng(11)
    X, y, _ = _panel(rng, n_groups=25, per_group=10, slope_sd=0.0)
    beta, _, rank, _ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    s2 = float(resid @ resid) / max(len(y) - rank, 1)
    classical = float(np.sqrt(np.linalg.pinv(X.T @ X)[-1, -1] * s2))
    robust, n_clusters = cluster_robust_se(X, y, beta, np.arange(len(y)))
    assert n_clusters == len(y)
    assert robust[-1] == pytest.approx(classical, rel=0.25)


def test_a_single_cluster_admits_it_knows_nothing() -> None:
    """One cluster cannot identify the sandwich. NaN and an infinite critical
    value are the honest answers; a small number would not be."""
    rng = np.random.default_rng(3)
    X, y, _ = _panel(rng, n_groups=1, per_group=40, slope_sd=0.0)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    robust, n_clusters = cluster_robust_se(X, y, beta, np.zeros(len(y)))
    assert n_clusters == 1
    assert np.isnan(robust).all()
    assert critical_value(1) == float("inf")


def test_critical_value_penalises_few_clusters_and_converges() -> None:
    """The small-G guard: 5 cars in class must buy a visibly wider interval
    than 55 driver-races, and a large G must not be punished for using the
    robust machinery."""
    assert critical_value(5) > 2.7
    assert critical_value(55) == pytest.approx(2.0, abs=0.02)
    assert critical_value(5) > critical_value(20) > critical_value(100) > 1.96


def test_the_chosen_spread_is_conservative_against_the_fitted_slopes() -> None:
    """0.04 must stay a modest between-unit spread, not an invented one.

    The number above is the whole basis for calling the classical interval's
    75% coverage *the realistic case*. If the fitted slopes ever narrowed to
    the point where 0.04 were adversarial, that argument would quietly stop
    holding — and the docstring asserting it would still read fine.
    """
    import pandas as pd

    from src.ingestion.config import F1_DERIVED_DIR

    path = F1_DERIVED_DIR / "degradation_coefficients.csv"
    if not path.exists():
        pytest.skip("degradation coefficients not generated")
    slopes = pd.read_csv(path)["deg_p1"].dropna()
    spread = float(slopes.max() - slopes.min())
    assert spread > 4 * 0.04, (
        f"fitted tyre-age slopes span only {spread:.3f} s/lap "
        f"({slopes.min():+.3f} to {slopes.max():+.3f}), so a between-unit SD "
        "of 0.04 is no longer the modest case the coverage argument above "
        "rests on. Re-read that argument before trusting it."
    )
