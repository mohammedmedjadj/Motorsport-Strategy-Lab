"""Shared reliability primitives, used by both the WEC and F1 finish-rate layers.

Extracted so the two series compute attrition the same way — a single Jeffreys
``Beta(0.5, 0.5)`` smoother (the same prior the calibration backtest uses), one
``ReliabilityRate`` shape, one grouping helper. Neither series duplicates it.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from scipy import stats

JEFFREYS = 0.5


@dataclass(frozen=True)
class ReliabilityRate:
    """A finish-rate estimate for one group, with a Jeffreys credible interval."""

    group: str
    n_entries: int
    n_classified: int
    rate: float          # smoothed point estimate (k + 0.5) / (n + 1)
    lo95: float          # 2.5th percentile of Beta(k+0.5, n-k+0.5)
    hi95: float          # 97.5th percentile

    def summary_row(self) -> dict:
        return {
            "group": self.group, "n_entries": self.n_entries,
            "n_classified": self.n_classified, "finish_rate": round(self.rate, 4),
            "lo95": round(self.lo95, 4), "hi95": round(self.hi95, 4),
        }


def jeffreys_rate(group: str, classified: pd.Series) -> ReliabilityRate:
    """Jeffreys-smoothed finish rate for one boolean series of outcomes."""
    n = int(classified.shape[0])
    k = int(classified.sum())
    a, b = k + JEFFREYS, (n - k) + JEFFREYS
    point = (k + JEFFREYS) / (n + 2 * JEFFREYS)
    lo, hi = stats.beta.ppf([0.025, 0.975], a, b)
    return ReliabilityRate(group, n, k, float(point), float(lo), float(hi))


def finish_rate_by(df: pd.DataFrame, column: str,
                   classified_col: str = "classified") -> list[ReliabilityRate]:
    """Finish rate for every distinct value of ``column``, most-fragile first."""
    rates = [jeffreys_rate(str(value), grp[classified_col])
             for value, grp in df.groupby(column, dropna=True)]
    return sorted(rates, key=lambda r: r.rate)
