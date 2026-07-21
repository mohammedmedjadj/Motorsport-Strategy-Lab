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
    """Clear-air laps beat a car's own median at all but one of the 21
    race-seasons (WEC Bahrain 2023 is a marginal +0.03 s exception, where a
    HYPERCAR rarely saw genuinely clear air), and traffic adds a positive
    per-car cost at the large majority — a real, honestly non-uniform result."""
    prime = {"imsa": "GTP", "wec": "HYPERCAR"}
    costs, clean_devs = {}, []
    for path, field in _real_fields().items():
        series = path.split("field_")[1].split("_")[0]
        t = measure_traffic_cost(field, series, "x", prime[series])
        costs[path] = t.cost_per_car_s
        clean_devs.append(t.clean_air_dev_s)
    # Clear air beats the own median at nearly every race; any exception is tiny.
    assert sum(d < 0 for d in clean_devs) >= len(clean_devs) - 1
    assert max(clean_devs) < 0.05
    # The per-car traffic cost is positive at the large majority of races
    # (21 race-seasons; a handful flip sign — the honestly non-uniform result).
    assert sum(c > 0 for c in costs.values()) >= 0.75 * len(costs)

    # Spa is the reference case: the largest traffic cost measured. Averaged
    # across its three seasons (each measured on its own field — the same car
    # numbers recur season to season, so the fields must not be pooled), it is
    # unambiguous, while one season alone swings 0.25-0.95.
    spa = [measure_traffic_cost(pd.read_csv(p), "wec", "spa", "HYPERCAR")
           for p in sorted(glob.glob(str(FIELD_DIR / "field_wec_*_spa.csv")))]
    assert np.mean([s.clear_vs_traffic_s for s in spa]) > 0.3
    assert np.mean([s.cost_per_car_s for s in spa]) > 0.2


@pytest.mark.skipif(not (ENDURANCE_DERIVED_DIR / "endurance_traffic_cost.csv").exists(),
                    reason="traffic artifact not generated")
def test_committed_traffic_artifact_matches_fresh_measurement() -> None:
    art = pd.read_csv(ENDURANCE_DERIVED_DIR / "endurance_traffic_cost.csv")
    assert set(art["series"]) <= {"imsa", "wec"}
    assert (art["clear_vs_traffic_s"] > 0).mean() >= 0.7  # positive at most races
    # Drift guard on one race, reconstructed by its exact (series, year, circuit).
    prime = {"imsa": "GTP", "wec": "HYPERCAR"}
    row = art.iloc[0]
    path = FIELD_DIR / f"field_{row['series']}_{int(row['year'])}_{row['circuit']}.csv"
    fresh = measure_traffic_cost(pd.read_csv(path), row["series"], row["circuit"],
                                 prime[row["series"]])
    assert row["cost_per_car_s"] == pytest.approx(fresh.cost_per_car_s, abs=1e-3)


@pytest.mark.skipif(not (ENDURANCE_DERIVED_DIR / "endurance_traffic_stability.csv").exists(),
                    reason="traffic stability artifact not generated")
def test_traffic_stability_summarises_every_circuit_across_its_seasons() -> None:
    """The cross-season stability table has one row per circuit, its season count
    matches the per-race table, and Spa is the strongest mean traffic cost —
    while carrying real season-to-season spread (SD > 0), the honest finding."""
    per_race = pd.read_csv(ENDURANCE_DERIVED_DIR / "endurance_traffic_cost.csv")
    stab = pd.read_csv(ENDURANCE_DERIVED_DIR / "endurance_traffic_stability.csv")
    assert len(stab) == per_race.groupby(["series", "circuit"]).ngroups
    counts = per_race.groupby(["series", "circuit"]).size().rename("n").reset_index()
    merged = stab.merge(counts, on=["series", "circuit"])
    assert (merged["n_seasons"] == merged["n"]).all()
    spa = stab.set_index("circuit").loc["spa"]
    assert spa["clear_vs_traffic_mean_s"] == stab["clear_vs_traffic_mean_s"].max()
    assert spa["clear_vs_traffic_sd_s"] > 0   # genuinely varies season to season
