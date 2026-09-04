"""Intervals and tests for the three headline results.

Every headline in this project is currently *described* rather than *tested*.
"GT3 transfers and prototypes do not" is a comparison of two numbers with no
statement of how much either could move; "r = -0.982" carries no interval;
"22.5 s" is quoted as a threshold with nothing said about how well located it
is. A reviewer stops at the first of those.

Three things make this harder than calling `scipy.stats`:

**The clustering.** Transfer scores are one per circuit-class, and the folds
inside a circuit-class share a pooled fitted slope. Resampling folds would treat
51 clusters as 194 independent observations and produce an interval far too
narrow. Everything here resamples the cluster.

**The cluster count.** Six classes carry the pit-loss correlation. A bootstrap
over six points is not inference, it is decoration — so the correlation is
resampled over the 205 *races*, recomputing the class medians inside each
replicate, which is the level the data actually varies at.

**The threshold is a maximum.** Bootstrapping a max is a known bad case: the
statistic sits on the boundary of its own support, the bootstrap distribution
is degenerate on one side, and the interval it produces understates the
uncertainty. That is stated here rather than hidden behind a percentile, and
what is reported instead is the sensitivity that actually matters — how far the
edge moves when the single race defining it is removed.

Seeded throughout, so a published interval is reproducible rather than
approximately reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

DEFAULT_DRAWS = 10_000
DEFAULT_SEED = 20260904


@dataclass(frozen=True)
class Interval:
    """A point estimate with a percentile bootstrap interval."""

    estimate: float
    low: float
    high: float
    level: float
    draws: int
    #: What was resampled. Recorded because the same statistic with the wrong
    #: resampling unit produces a narrower interval and looks better for it.
    unit: str

    def __str__(self) -> str:
        return f"{self.estimate:+.4f} [{self.low:+.4f}, {self.high:+.4f}]"

    @property
    def excludes_zero(self) -> bool:
        return (self.low > 0) or (self.high < 0)


@dataclass(frozen=True)
class GroupComparison:
    """A difference in group means, with an interval and a permutation p."""

    difference: Interval
    p_value: float
    n_a: int
    n_b: int
    #: Permutation rather than bootstrap for the p-value: with 12 clusters in
    #: one group the bootstrap interval is doing well to be honest about
    #: width, and the exchangeability test needs no distributional assumption
    #: at all.
    permutations: int


def cluster_bootstrap(
    values: np.ndarray,
    statistic,
    draws: int = DEFAULT_DRAWS,
    level: float = 0.95,
    seed: int = DEFAULT_SEED,
    unit: str = "cluster",
) -> Interval:
    """Percentile bootstrap, resampling whole rows of ``values``.

    ``values`` is one row per independent unit — a circuit-class, a race —
    and ``statistic`` maps a resampled array to a number. Resampling the row
    rather than the observation is the whole point: it is what keeps the
    interval honest when observations inside a unit share a fitted quantity.
    """
    values = np.asarray(values)
    if len(values) < 2:
        raise ValueError("a bootstrap over fewer than two units is not an interval")
    rng = np.random.default_rng(seed)
    n = len(values)
    replicates = np.empty(draws, dtype=float)
    for i in range(draws):
        replicates[i] = statistic(values[rng.integers(0, n, n)])
    tail = (1.0 - level) / 2.0
    return Interval(
        estimate=float(statistic(values)),
        low=float(np.quantile(replicates, tail)),
        high=float(np.quantile(replicates, 1.0 - tail)),
        level=level, draws=draws, unit=unit,
    )


def compare_groups(
    group_a: np.ndarray,
    group_b: np.ndarray,
    draws: int = DEFAULT_DRAWS,
    permutations: int = DEFAULT_DRAWS,
    seed: int = DEFAULT_SEED,
    unit: str = "circuit-class",
) -> GroupComparison:
    """Difference in means between two groups of clusters, tested two ways.

    The interval comes from resampling each group independently; the p-value
    from permuting the group labels, which assumes only exchangeability under
    the null. With 12 clusters on one side that matters — a bootstrap interval
    at this size is worth reporting but is not the thing to hang a claim on.
    """
    a, b = np.asarray(group_a, float), np.asarray(group_b, float)
    if len(a) < 2 or len(b) < 2:
        raise ValueError("each group needs at least two clusters")
    rng = np.random.default_rng(seed)

    observed = float(a.mean() - b.mean())
    replicates = np.empty(draws, dtype=float)
    for i in range(draws):
        replicates[i] = (
            a[rng.integers(0, len(a), len(a))].mean()
            - b[rng.integers(0, len(b), len(b))].mean()
        )
    tail = 0.025
    interval = Interval(
        estimate=observed,
        low=float(np.quantile(replicates, tail)),
        high=float(np.quantile(replicates, 1.0 - tail)),
        level=0.95, draws=draws, unit=unit,
    )

    pooled = np.concatenate([a, b])
    extreme = 0
    for _ in range(permutations):
        shuffled = rng.permutation(pooled)
        difference = shuffled[:len(a)].mean() - shuffled[len(a):].mean()
        if abs(difference) >= abs(observed):
            extreme += 1
    # Add-one correction: a permutation test can never report p = 0, and
    # printing one would claim more than 10,000 permutations can support.
    p_value = (extreme + 1) / (permutations + 1)

    return GroupComparison(interval, p_value, len(a), len(b), permutations)


def boundary_sensitivity(values: np.ndarray) -> dict[str, float]:
    """How far a maximum moves when the single point defining it is dropped.

    For a threshold defined as "the largest value at which the condition still
    holds", the bootstrap is the wrong instrument: the statistic sits on the
    edge of its own support, so resampling produces a distribution that is
    degenerate above the maximum and understates uncertainty below it.

    What is informative instead is leave-one-out — specifically, leaving out the
    point that *is* the maximum, since that is the only observation the estimate
    depends on. A large gap to the second-largest means the threshold rests on
    one race.
    """
    values = np.sort(np.asarray(values, float))[::-1]
    if len(values) < 2:
        raise ValueError("a boundary needs at least two values to be sensitive")
    return {
        "maximum": float(values[0]),
        "without_the_defining_point": float(values[1]),
        "gap": float(values[0] - values[1]),
        "relative_gap": float((values[0] - values[1]) / values[0]),
        "n": float(len(values)),
    }


def correlation_over_units(
    unit_values: list[np.ndarray],
    aggregate,
    draws: int = DEFAULT_DRAWS,
    level: float = 0.95,
    seed: int = DEFAULT_SEED,
) -> Interval:
    """Bootstrap a group-level correlation by resampling *within* each group.

    The pit-loss rule correlates six class-level summaries. Resampling those six
    points would be a bootstrap with n = 6 and is not worth reporting. Instead
    each class's races are resampled, the class summary is recomputed inside
    every replicate, and the correlation is taken across the six recomputed
    summaries — so the variation being propagated is the variation that exists.

    ``unit_values`` is one array of races per group; ``aggregate`` maps a
    resampled group to its ``(x, y)`` pair.
    """
    if len(unit_values) < 3:
        raise ValueError("a correlation needs at least three groups")
    rng = np.random.default_rng(seed)
    groups = [np.asarray(group) for group in unit_values]

    def correlate(pairs: list[tuple[float, float]]) -> float:
        xs = np.array([p[0] for p in pairs], float)
        ys = np.array([p[1] for p in pairs], float)
        if np.std(xs) == 0 or np.std(ys) == 0:
            return float("nan")
        return float(np.corrcoef(xs, ys)[0, 1])

    observed = correlate([aggregate(group) for group in groups])
    replicates = []
    for _ in range(draws):
        resampled = [
            group[rng.integers(0, len(group), len(group))] for group in groups
        ]
        value = correlate([aggregate(group) for group in resampled])
        if np.isfinite(value):
            replicates.append(value)
    if len(replicates) < draws // 2:
        raise ValueError(
            "over half the bootstrap replicates were degenerate; the groups "
            "are too small or too uniform for this interval to mean anything"
        )
    tail = (1.0 - level) / 2.0
    return Interval(
        estimate=observed,
        low=float(np.quantile(replicates, tail)),
        high=float(np.quantile(replicates, 1.0 - tail)),
        level=level, draws=len(replicates), unit="race within class",
    )
