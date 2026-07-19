"""Turn raw simulation draws into a pit-window recommendation.

The output is deliberately a distribution summary per candidate lap plus a
window — never a single "pit on lap N" number. With the propagated Phase
2/3 uncertainty, laps within a fraction of a second of each other are not
distinguishable and the honest recommendation is the set of them.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.simulator.engine import Scenario, SimulationResult

#: Candidates whose median lies within this margin of the best are
#: statistically indistinguishable for practical purposes -> the "window".
WINDOW_TOLERANCE_S = 0.5


@dataclass(frozen=True)
class Recommendation:
    """Distribution summary and recommended window for one scenario."""

    scenario: Scenario
    table: pd.DataFrame  # one row per candidate pit lap
    best_lap: int
    window: tuple[int, ...]

    def summary_lines(self) -> list[str]:
        w = ", ".join(str(lap) for lap in self.window)
        lines = [
            f"Best median pit lap: **{self.best_lap}** — recommended window "
            f"(medians within {WINDOW_TOLERANCE_S}s): **[{w}]**.",
        ]
        best = self.table.loc[self.table["pit_lap"] == self.best_lap].iloc[0]
        spread = best["p90_s"] - best["p10_s"]
        lines.append(
            f"Outcome spread at the best lap (p10-p90): {spread:.1f}s — "
            "this is the honest uncertainty of any single-race outcome."
        )
        for rival_col in [c for c in self.table.columns if c.startswith("p_ahead_")]:
            rival = rival_col.removeprefix("p_ahead_")
            at_best = float(best[rival_col])
            peak = self.table.loc[self.table[rival_col].idxmax()]
            lines.append(
                f"vs {rival}: P(ahead) = {at_best:.2f} at lap {self.best_lap}; "
                f"maximised at lap {int(peak['pit_lap'])} ({peak[rival_col]:.2f})."
            )
        return lines


def summarise(scenario: Scenario, result: SimulationResult) -> Recommendation:
    """Aggregate per-draw outcomes into the recommendation table."""
    medians = np.median(result.our_time, axis=1)
    rows = {
        "pit_lap": list(result.candidates),
        "median_s": medians,
        "mean_s": result.our_time.mean(axis=1),
        "p10_s": np.percentile(result.our_time, 10, axis=1),
        "p90_s": np.percentile(result.our_time, 90, axis=1),
        "p_best": result.p_best,
    }
    for rival, ahead in result.ahead_of_rival.items():
        rows[f"p_ahead_{rival}"] = ahead.mean(axis=1)
    table = pd.DataFrame(rows)

    best_idx = int(np.argmin(medians))
    best_lap = result.candidates[best_idx]
    window = tuple(
        int(lap)
        for lap, m in zip(result.candidates, medians)
        if m <= medians[best_idx] + WINDOW_TOLERANCE_S
    )
    return Recommendation(scenario=scenario, table=table, best_lap=best_lap, window=window)


def pareto_front(
    rec: Recommendation, objectives: dict[str, str]
) -> pd.DataFrame:
    """Exact Pareto-optimal pit laps over several competing objectives.

    ``objectives`` maps a column of ``rec.table`` to ``"min"`` or ``"max"``,
    e.g. ``{"mean_s": "min", "p_ahead_car_ahead": "max"}`` to trade expected
    race time against the probability of finishing ahead of a rival. Returns
    the sub-table of *non-dominated* candidates — those for which no other
    candidate is at least as good on every objective and strictly better on
    one — sorted by the first objective.

    The candidate set is a small discrete 1-D grid (feasible pit laps), so the
    front is enumerated exactly by pairwise non-dominated sorting; there is no
    need for, and no accuracy lost relative to, a metaheuristic like NSGA-II,
    whose purpose is large or continuous search spaces.

    The default single-objective ``summarise`` recommendation is the special
    case ``{"median_s": "min"}``; this exposes the trade-off that collapses.
    """
    if not objectives:
        raise ValueError("need at least one objective")
    missing = [c for c in objectives if c not in rec.table.columns]
    if missing:
        raise ValueError(f"unknown objective column(s): {missing}")
    bad = {d for d in objectives.values()} - {"min", "max"}
    if bad:
        raise ValueError(f"objective direction must be 'min' or 'max', got {bad}")

    # Orient every objective so that "larger is better", then a point is
    # dominated iff some other point is >= on all axes and > on at least one.
    signs = np.array([1.0 if d == "max" else -1.0 for d in objectives.values()])
    values = rec.table[list(objectives)].to_numpy(dtype=float) * signs
    n = len(values)
    keep = np.ones(n, dtype=bool)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if np.all(values[j] >= values[i]) and np.any(values[j] > values[i]):
                keep[i] = False
                break

    first = next(iter(objectives))
    front = rec.table.loc[keep].sort_values(
        first, ascending=objectives[first] == "min"
    )
    return front.reset_index(drop=True)


def table_markdown(rec: Recommendation, max_rows: int = 12) -> str:
    """Compact markdown table centred on the recommended window."""
    df = rec.table.copy()
    if len(df) > max_rows:
        centre = df.index[df["pit_lap"] == rec.best_lap][0]
        lo = max(0, centre - max_rows // 2)
        df = df.iloc[lo : lo + max_rows]
    cols = [c for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, row in df.iterrows():
        cells = [
            f"{row[c]:.0f}" if c == "pit_lap" else f"{row[c]:.2f}" for c in cols
        ]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)
