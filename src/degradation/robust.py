"""Cluster-robust standard errors for the degradation fits.

Why this exists
---------------
Every degradation model in this project is a fixed-effects OLS on panel data:
laps nested inside a car's race. Classical OLS standard errors assume the
residuals are independent, and lap times are not remotely independent — a car
running in traffic, on a hot track, in a bad fuel phase or with a driver
having an off stint produces a *run* of correlated residuals. Treating those
laps as independent observations counts the same information many times over
and returns a standard error that is too small.

Measured on this project's own data, not assumed: clustering by driver-race
multiplies the F1 degradation-slope standard errors by 1.4x to 4.5x, and every
coefficient at every circuit moves the same way. On the endurance side the
median inflation is 1.3x (IMSA) and 1.5x (WEC).

This matters more here than in a typical regression write-up, because these
standard errors are not decoration: ``src/simulator/artifacts.py`` turns them
into the per-draw coefficient distribution the Monte Carlo engine samples
from. An understated standard error propagates directly into an understated
P10-P90 band, which is the one number this project asks to be believed.

Few clusters
------------
The sandwich estimator is consistent as the number of *clusters* grows, not as
the number of laps grows. Some endurance races field only 5-10 cars in class,
so G can be small and CR1 is then biased downward. Two guards:

- ``critical_value`` returns the ``t(G-1)`` quantile rather than 1.96, which
  widens intervals exactly when clusters are scarce (G=5 -> 2.78 vs G=55 ->
  2.00) and converges to the normal when they are not.
- ``n_clusters`` travels with the estimate so downstream code can sample from
  a t with the right tail weight instead of a normal.

Reference: Cameron & Miller (2015), "A Practitioner's Guide to Cluster-Robust
Inference", J. Human Resources 50(2).
"""

from __future__ import annotations

import numpy as np
from scipy import stats


def cluster_robust_se(
    X: np.ndarray, y: np.ndarray, beta: np.ndarray, groups: np.ndarray
) -> tuple[np.ndarray, int]:
    """CR1 cluster-robust standard errors, and the number of clusters.

    ``V = (X'X)^-1 (c * sum_g X_g' u_g u_g' X_g) (X'X)^-1`` with the usual
    finite-sample correction ``c = G/(G-1) * (N-1)/(N-K)``.

    Uses ``pinv`` for the same reason the fits do: a driver-race seen on a
    single compound leaves the design rank-deficient, which is a property of
    real race data rather than a bug to reject.

    Returns ``(se, n_clusters)``. With a single cluster the sandwich is not
    identified and the standard errors come back as NaN rather than as a
    confidently wrong small number.
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    u = y - X @ beta
    uniq = np.unique(groups)
    n_clusters = int(uniq.size)
    if n_clusters < 2:
        return np.full(X.shape[1], np.nan), n_clusters

    xtx_inv = np.linalg.pinv(X.T @ X)
    meat = np.zeros((X.shape[1], X.shape[1]))
    for g in uniq:
        mask = groups == g
        score = X[mask].T @ u[mask]
        meat += np.outer(score, score)

    n_obs = X.shape[0]
    rank = int(np.linalg.matrix_rank(X))
    correction = (n_clusters / (n_clusters - 1)) * ((n_obs - 1) / max(n_obs - rank, 1))
    cov = xtx_inv @ (correction * meat) @ xtx_inv
    return np.sqrt(np.clip(np.diag(cov), 0.0, None)), n_clusters


def classical_se(X: np.ndarray, y: np.ndarray, beta: np.ndarray) -> np.ndarray:
    """Textbook homoscedastic OLS standard errors.

    Kept not because anything should use them, but because the size of the
    correction is itself a reported result: a claim that clustering matters
    has to be checked against the thing it replaced, on this run, rather than
    quoted from the day it was measured.
    """
    X = np.asarray(X, dtype=float)
    resid = np.asarray(y, dtype=float) - X @ beta
    rank = int(np.linalg.matrix_rank(X))
    sigma2 = float(resid @ resid) / max(X.shape[0] - rank, 1)
    return np.sqrt(np.clip(np.diag(np.linalg.pinv(X.T @ X)) * sigma2, 0.0, None))


def t_degrees_of_freedom(n_clusters: float | None) -> float:
    """Degrees of freedom for the ``t`` a sampler should draw from: ``G - 1``.

    One place for the conversion because the arithmetic has two traps and
    both are silent. ``G - 1`` with ``G = 1`` gives ``df = 0``, which
    ``numpy.random.Generator.standard_t`` rejects at the point of use, far
    from the cause. And a missing cluster count is not the same as an
    abundant one: ``None`` returns ``inf`` (draw a normal — this estimate
    carries no cluster information at all), whereas ``G = 1`` is an error,
    because :func:`cluster_robust_se` has already returned NaN there and a
    caller reaching this function with it is asking to sample from nothing.

    ``G = 2`` legitimately returns ``df = 1``: a Cauchy. The quantiles exist
    and are enormous, which is the honest description of what two clusters
    tell you, not a defect to clamp away.
    """
    if n_clusters is None:
        return float("inf")
    n = float(n_clusters)
    if n < 2:
        raise ValueError(
            f"n_clusters={n_clusters!r} cannot support a cluster-robust "
            "reference distribution; at least 2 clusters are needed"
        )
    return n - 1.0


def critical_value(n_clusters: int, level: float = 0.95) -> float:
    """Two-sided ``t(G-1)`` critical value for a cluster-robust interval.

    The reference distribution for cluster-robust inference is ``t(G-1)``, not
    the normal: with 5 cars in class the interval has to be 42% wider than the
    normal one to keep its nominal coverage. Returns the normal quantile when
    G is large enough for the difference to be immaterial, and for
    ``n_clusters < 2`` returns ``inf`` — an interval that admits it knows
    nothing, rather than one that looks precise.
    """
    if n_clusters < 2:
        return float("inf")
    return float(stats.t.ppf(0.5 + level / 2.0, df=n_clusters - 1))
