"""Reliability / attrition from the results-level WEC history (2011-2023).

The one strategic primitive that *results* data supports better than lap data:
the probability a car reaches the classified finish, estimated over 13 seasons.
Finishing is itself a strategy variable in endurance racing (a conservative
stint plan trades pace for the chance of being running at the flag), and no
lap-level model in this repo captures it.

Shares the Jeffreys smoother and grouping helper with the F1 layer via
``reliability.core``; only the duration-bucketing and its positive control are
WEC-specific here.
"""

from __future__ import annotations

import pandas as pd

from src.reliability.core import ReliabilityRate, finish_rate_by, jeffreys_rate

__all__ = ["ReliabilityRate", "finish_rate_by", "finish_rate_by_duration",
           "attrition_holds_with_duration"]


def finish_rate_by_duration(df: pd.DataFrame) -> list[ReliabilityRate]:
    """Finish rate bucketed by race length. The falsifiable prediction: attrition
    rises with duration, so the 24 h finish rate should sit below the 6 h one."""
    buckets = df.dropna(subset=["duration_h"]).copy()
    buckets["bucket"] = buckets["duration_h"].astype(int).astype(str) + "h"
    rates = [jeffreys_rate(b, grp["classified"]) for b, grp in buckets.groupby("bucket")]
    return sorted(rates, key=lambda r: int(r.group.rstrip("h")))


def attrition_holds_with_duration(df: pd.DataFrame) -> bool:
    """True iff the longest race in the data has a strictly lower finish rate
    than the shortest — the reliability model's positive control."""
    by_dur = finish_rate_by_duration(df)
    if len(by_dur) < 2:
        return False
    return by_dur[-1].rate < by_dur[0].rate
