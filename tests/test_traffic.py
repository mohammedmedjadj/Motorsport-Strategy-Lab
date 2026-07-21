"""Inter-class traffic cost: exact counting of other-class cars ahead on a
hand-built field, and the real measured cost + drift guard on the committed
multi-class fields."""

from __future__ import annotations

import glob

import numpy as np
import pandas as pd
import pytest

from src.ingestion.config import ENDURANCE_DERIVED_DIR
from src.simulator.traffic import measure_traffic_cost, traffic_exposure

FIELD_DIR = ENDURANCE_DERIVED_DIR / "field"


def _field(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["flags"] = "GF"
    df["pit_time"] = np.nan
    return df


def test_traffic_exposure_counts_other_class_cars_just_ahead() -> None:
    # Prime P1 crosses the line at 100 and 200. Two GT cars cross just before:
    # G1 at 95 (before lap-1 crossing), G2 at 95 and 190 (before laps 1 and 2).
    field = _field(
        [{"car": "P1", "class": "P", "lap": 1, "lap_time": 100.0},
         {"car": "P1", "class": "P", "lap": 2, "lap_time": 100.0},
         {"car": "G1", "class": "GT", "lap": 1, "lap_time": 95.0},
         {"car": "G2", "class": "GT", "lap": 1, "lap_time": 95.0},
         {"car": "G2", "class": "GT", "lap": 2, "lap_time": 95.0}]  # cross 95, 190
    )
    ex = traffic_exposure(field, prime_class="P", window_s=12.0).set_index("lap")
    assert int(ex.loc[1, "traffic"]) == 2   # G1 and G2 both crossed at 95
    assert int(ex.loc[2, "traffic"]) == 1   # only G2, at 190


def _real_fields() -> dict[str, pd.DataFrame]:
    return {p: pd.read_csv(p) for p in glob.glob(str(FIELD_DIR / "field_*.csv"))}


@pytest.mark.skipif(not glob.glob(str(FIELD_DIR / "field_*.csv")),
                    reason="multi-class field data not materialised")
def test_traffic_slows_prototypes_on_real_data() -> None:
    """Clear-air laps always beat a car's own median, and traffic adds a
    positive per-car cost at most circuits (not every one — a real, honestly
    non-uniform result, weak at Sebring/Imola; see the report)."""
    prime = {"imsa": "GTP", "wec": "HYPERCAR"}
    costs = {}
    for path, field in _real_fields().items():
        series = path.split("field_")[1].split("_")[0]
        t = measure_traffic_cost(field, series, "x", prime[series])
        assert t.clean_air_dev_s < 0           # clear air beats the own median, always
        costs[path] = t.cost_per_car_s
    # The per-car traffic cost is positive at the large majority of circuits.
    assert sum(c > 0 for c in costs.values()) >= 6

    # Spa is the reference case: a large, unambiguous traffic cost.
    spa = measure_traffic_cost(
        pd.read_csv(glob.glob(str(FIELD_DIR / "field_wec_*_spa.csv"))[0]),
        "wec", "spa", "HYPERCAR")
    assert spa.clear_vs_traffic_s > 0.5 and spa.cost_per_car_s > 0.2


@pytest.mark.skipif(not (ENDURANCE_DERIVED_DIR / "endurance_traffic_cost.csv").exists(),
                    reason="traffic artifact not generated")
def test_committed_traffic_artifact_matches_fresh_measurement() -> None:
    art = pd.read_csv(ENDURANCE_DERIVED_DIR / "endurance_traffic_cost.csv")
    assert set(art["series"]) <= {"imsa", "wec"}
    assert (art["clear_vs_traffic_s"] > 0).mean() >= 0.7  # positive at most circuits
    # Drift guard on one row.
    prime = {"imsa": "GTP", "wec": "HYPERCAR"}
    row = art.iloc[0]
    path = glob.glob(str(FIELD_DIR / f"field_{row['series']}_*_{row['circuit']}.csv"))[0]
    fresh = measure_traffic_cost(pd.read_csv(path), row["series"], row["circuit"],
                                 prime[row["series"]])
    assert row["cost_per_car_s"] == pytest.approx(fresh.cost_per_car_s, abs=1e-3)
