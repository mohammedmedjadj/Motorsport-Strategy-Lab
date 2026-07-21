"""Track-position value: exact recovery on synthetic orders with known swap
counts, the physically-correct real-circuit ordering, the season-to-season
stability finding, and a drift guard on the committed artifact."""

from __future__ import annotations

import glob

import numpy as np
import pandas as pd
import pytest

from src.ingestion.config import F1_DERIVED_DIR
from src.simulator.track_position import (
    adjacent_swap_rate,
    hold_probability,
    measure_circuit,
)


def _race(order_per_lap: list[list[str]]) -> pd.DataFrame:
    """A green race whose classified order on each lap is given explicitly."""
    rows = []
    for lap, order in enumerate(order_per_lap, start=1):
        for pos, drv in enumerate(order, start=1):
            rows.append({
                "Driver": drv, "LapNumber": lap, "Position": pos,
                "TrackStatus": "1", "is_in_lap": False, "is_out_lap": False,
            })
    return pd.DataFrame(rows)


def test_static_order_has_zero_swaps() -> None:
    order = ["A", "B", "C", "D", "E"]
    rate, n = adjacent_swap_rate(_race([order, order, order]))
    assert rate == 0.0 and n == 2
    assert hold_probability(rate, 30) == 1.0


def test_one_adjacent_swap_per_lap_is_measured_exactly() -> None:
    # 5 cars, the middle adjacent pair (C,D) swaps every lap -> 1 of 4 adjacent
    # pairs swaps => rate 0.25 on each transition.
    laps = _race([
        ["A", "B", "C", "D", "E"],
        ["A", "B", "D", "C", "E"],
        ["A", "B", "C", "D", "E"],
    ])
    rate, n = adjacent_swap_rate(laps)
    assert n == 2
    assert rate == pytest.approx(0.25)


def test_hold_probability_is_first_order_geometric() -> None:
    assert hold_probability(0.0, 15) == 1.0
    assert hold_probability(0.04, 15) == pytest.approx((1 - 0.04) ** 15)
    assert hold_probability(0.5, 0) == 1.0  # zero laps -> certain hold


def test_too_few_cars_and_non_green_are_skipped() -> None:
    laps = _race([["A", "B", "C"], ["A", "C", "B"]])  # only 3 cars < MIN_CARS
    with pytest.raises(ValueError, match="no usable"):
        adjacent_swap_rate(laps)
    # Non-green laps must be excluded, leaving nothing to measure.
    green = _race([["A", "B", "C", "D"], ["A", "B", "C", "D"]])
    green["TrackStatus"] = "4"  # safety car
    with pytest.raises(ValueError, match="no usable"):
        adjacent_swap_rate(green)


def _real(circuit: str) -> dict[str, pd.DataFrame]:
    return {
        p.split("_")[1]: pd.read_csv(p)
        for p in glob.glob(str(F1_DERIVED_DIR / f"laps_*_{circuit}.csv"))
    }


def test_monaco_is_stickier_than_barcelona_on_real_data() -> None:
    monaco = measure_circuit(_real("monaco"), "monaco")
    barca = measure_circuit(_real("barcelona"), "barcelona")
    # Overtaking is far harder at Monaco: position is worth much more there.
    assert monaco.swap_rate < barca.swap_rate
    assert monaco.hold_probability(15) > 0.90
    assert barca.hold_probability(15) < 0.70


def test_overtaking_difficulty_is_stable_across_seasons() -> None:
    """The headline finding: unlike degradation, overtaking difficulty transfers
    between seasons (it is set by track geometry). SD across races is tiny."""
    for circuit in ("monaco", "barcelona", "singapore"):
        diff = measure_circuit(_real(circuit), circuit)
        assert diff.n_races >= 3
        # Season-to-season spread is a small fraction of the level itself.
        assert diff.sd < 0.5 * diff.swap_rate + 0.005


def test_committed_artifact_matches_a_fresh_measurement() -> None:
    """Drift guard: the committed overtaking_difficulty.csv must still equal a
    fresh recomputation, so the number the report/strategy layer cite cannot go
    stale."""
    committed = pd.read_csv(F1_DERIVED_DIR / "overtaking_difficulty.csv").set_index("circuit")
    for circuit in committed.index:
        fresh = measure_circuit(_real(circuit), circuit)
        assert committed.loc[circuit, "adj_swap_rate"] == pytest.approx(
            round(fresh.swap_rate, 4), abs=1e-4
        )
