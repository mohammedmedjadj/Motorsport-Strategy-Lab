"""Track-position value, measured from real timing.

The strategy layer's biggest missing piece of racecraft: how much is being
*ahead* worth? That depends entirely on how hard the circuit is to overtake at.
If you emerge from the pits just ahead of a rival, do you keep the place, or
does the circuit let them straight back past?

We measure this directly, no assumptions: the **adjacent-pair swap rate** — the
fraction of nose-to-tail (rank-adjacent) car pairs whose on-track order flips
between two consecutive green racing laps, averaged over the race. Restricting
to cars that are *both* green-racing on both laps makes it immune to pit-cycle
position shuffling, and using rank-*adjacent* pairs makes it the operationally
relevant quantity — "can the car right behind me get past" — rather than a
global fluidity index diluted by cars that never interact.

Crucially this is the **pace-neutral** baseline: a genuinely faster car passes
regardless of the circuit, so this measures how sticky position is *absent* a
pace advantage — exactly the quantity a strategist reasons about when weighing
an undercut ("I'll come out behind but on fresh tyres") against track position
("but can I even get back past here?").

Unlike tyre degradation — which this project shows does *not* transfer between
races — overtaking difficulty is a property of track geometry and is strikingly
stable season to season (see ``reports/f1/track_position.md``), which is why it
is reported as a genuine per-circuit constant.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

#: A rank-adjacent swap rate is only meaningful with enough co-racing cars.
MIN_CARS = 4


def _green_racing(laps: pd.DataFrame) -> pd.DataFrame:
    """Green-flag laps with a classified position, excluding pit in/out laps."""
    return laps[
        (laps["TrackStatus"].astype(str) == "1")
        & (~laps["is_in_lap"].astype(bool))
        & (~laps["is_out_lap"].astype(bool))
        & laps["Position"].notna()
    ]


def _swap_rate_from_by_lap(by_lap: dict[int, pd.Series]) -> tuple[float, int]:
    """Core measure, series-agnostic: ``by_lap`` maps lap number -> a Series of
    (car -> a lower-is-further-ahead position value). Returns the mean fraction
    of rank-adjacent pairs that swap between consecutive laps, and the count of
    lap transitions used. A transition needs at least ``MIN_CARS`` cars present
    on both of its laps."""
    rates: list[float] = []
    for lap in sorted(by_lap):
        here, nxt = by_lap.get(lap), by_lap.get(lap + 1)
        if here is None or nxt is None:
            continue
        common = here.index.intersection(nxt.index)
        if len(common) < MIN_CARS:
            continue
        order = here[common].sort_values().index.to_numpy()  # rank order this lap
        next_pos = nxt[common].reindex(order).to_numpy()      # their positions next lap
        # A rank-adjacent pair swapped iff the next-lap position sequence, read
        # in this-lap rank order, steps backwards.
        swaps = int((np.diff(next_pos) < 0).sum())
        rates.append(swaps / (len(order) - 1))
    if not rates:
        raise ValueError("no usable green racing lap transitions in this race")
    return float(np.mean(rates)), len(rates)


def adjacent_swap_rate(laps: pd.DataFrame) -> tuple[float, int]:
    """F1 adjacent-pair swap rate, using FastF1's classified ``Position`` per
    green racing lap."""
    green = _green_racing(laps)
    by_lap = {int(ln): sub.set_index("Driver")["Position"]
              for ln, sub in green.groupby("LapNumber")}
    return _swap_rate_from_by_lap(by_lap)


def adjacent_swap_rate_endurance(laps: pd.DataFrame) -> tuple[float, int]:
    """Endurance adjacent-pair swap rate. The normalised endurance schema has no
    per-lap position, so on-track order is **reconstructed** from cumulative
    race time within the class (lower cumulative time = further ahead) — the
    laps are already filtered to one class, so this is within-class position.
    Measured on green, non-pit laps only, so pit-cycle order changes are
    excluded exactly as the F1 in/out-lap filter does."""
    work = laps.sort_values(["car", "lap"], kind="stable").copy()
    work["cum"] = work.groupby("car", sort=False)["lap_time_s"].cumsum()
    racing = work[
        work["is_green"].astype(bool)
        & ~work["is_pit_lap"].astype(bool)
        & work["lap_time_s"].notna()
        & work["cum"].notna()
    ]
    by_lap = {int(ln): sub.set_index("car")["cum"]
              for ln, sub in racing.groupby("lap")}
    return _swap_rate_from_by_lap(by_lap)


def hold_probability(swap_rate: float, laps: int) -> float:
    """P(a car currently ahead keeps a rival directly behind over ``laps`` green
    laps), pace-neutral, as a first-order ``(1 - p)^laps`` model — each green lap
    is an independent chance for the adjacent pair to swap. It deliberately
    ignores any pace difference (a faster car passes regardless) and any
    DRS/dirty-air dynamics; it is the neutral baseline the strategy layer starts
    from, not a full overtaking model."""
    return float((1.0 - swap_rate) ** max(int(laps), 0))


@dataclass(frozen=True)
class OvertakingDifficulty:
    """Per-circuit overtaking difficulty, aggregated over its races."""

    circuit: str
    swap_rate: float      # mean adjacent-pair swap rate per green lap
    sd: float             # std across races — season-to-season stability
    n_races: int
    n_transitions: int

    def hold_probability(self, laps: int) -> float:
        """Pace-neutral P(hold an adjacent rival over ``laps`` green laps)."""
        return hold_probability(self.swap_rate, laps)


def measure_circuit(
    laps_by_race: dict[str, pd.DataFrame],
    circuit: str,
    rate_fn=adjacent_swap_rate,
) -> OvertakingDifficulty:
    """Aggregate the adjacent-swap rate across every race of one circuit.

    ``rate_fn`` is ``adjacent_swap_rate`` for F1 (classified position) or
    ``adjacent_swap_rate_endurance`` for WEC/IMSA (position reconstructed from
    cumulative time)."""
    if not laps_by_race:
        raise ValueError(f"{circuit}: no races supplied")
    rates: list[float] = []
    transitions = 0
    for laps in laps_by_race.values():
        rate, n = rate_fn(laps)
        rates.append(rate)
        transitions += n
    arr = np.array(rates, dtype=float)
    return OvertakingDifficulty(
        circuit=circuit,
        swap_rate=float(arr.mean()),
        sd=float(arr.std()),
        n_races=len(rates),
        n_transitions=transitions,
    )
