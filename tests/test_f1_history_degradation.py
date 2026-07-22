"""The full-calendar F1 degradation fit: the fuel/tyre decoupling recovers a
known tyre slope from a known fuel trend (the Mistral-#2 solution), single-stint
races are correctly flagged non-separable, and the committed artifact carries the
decomposition."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.degradation.f1_history import _fit_slope, fit_history_degradation
from src.ingestion.config import F1_DERIVED_DIR

_ARTIFACT = F1_DERIVED_DIR / "history_degradation.csv"


def _synthetic_race(tyre: float, fuel: float, n_stint: int = 40,
                    seed: int = 0) -> pd.DataFrame:
    """One race, two drivers, two stints each, where the true model is
    ``lap_time = 90 + tyre*tyre_age + fuel*lap + small noise``. Two stints of
    different phase make tyre_age and absolute lap non-collinear, so the fit can
    separate them."""
    rng = np.random.default_rng(seed)
    rows = []
    for driver in (1, 2):
        lap = 1
        for stint in (0, 1):
            for age in range(n_stint):
                rows.append({
                    "raceId": 1, "year": 2023, "era": "ground-effect",
                    "circuitRef": "testring", "circuit": "Test",
                    "driverRef": f"d{driver}", "driverId": driver,
                    "lap": lap, "stint": stint, "tyre_age": age,
                    "lap_time_s": 90.0 + tyre * age + fuel * lap
                    + rng.normal(0, 0.02),
                })
                lap += 1
    return pd.DataFrame(rows)


def test_decoupling_recovers_a_known_tyre_slope_from_a_fuel_trend() -> None:
    # true tyre wear +0.08 s/lap, fuel/evolution -0.05 s/lap.
    race = _synthetic_race(tyre=0.08, fuel=-0.05)
    net, tyre, fuel_evo, n, rmse = _fit_slope(race)
    # The naive net slope is badly biased by fuel; the decoupled tyre term is not.
    assert tyre == pytest.approx(0.08, abs=0.02)
    assert fuel_evo == pytest.approx(-0.05, abs=0.02)
    assert net < tyre           # fuel drags the net below the true tyre wear
    assert rmse < 0.1


def test_single_stint_race_is_flagged_non_separable() -> None:
    """With one stint, tyre_age == lap-1 (collinear) so tyre/fuel can't be
    identified — they must come back NaN, never a fabricated split."""
    rng = np.random.default_rng(1)
    rows = [{
        "raceId": 1, "year": 2023, "era": "ground-effect",
        "circuitRef": "testring", "circuit": "Test", "driverRef": "d1",
        "driverId": 1, "lap": age + 1, "stint": 0, "tyre_age": age,
        "lap_time_s": 90 + 0.05 * age + rng.normal(0, 0.02),
    } for age in range(60)]
    net, tyre, fuel_evo, n, rmse = _fit_slope(pd.DataFrame(rows))
    assert not np.isnan(net)          # the net slope is still well-defined
    assert np.isnan(tyre) and np.isnan(fuel_evo)


def test_fit_history_returns_one_row_per_circuit_season() -> None:
    df = pd.concat([_synthetic_race(0.08, -0.05, seed=1),
                    _synthetic_race(0.03, -0.04, seed=2).assign(circuitRef="other")])
    out = fit_history_degradation(df)
    assert set(out["circuit"]) == {"testring", "other"}   # dataclass field name
    assert {"net_slope_s", "tyre_slope_s", "fuel_evo_slope_s"} <= set(out.columns)


@pytest.mark.skipif(not _ARTIFACT.exists(), reason="history artifact not generated")
def test_committed_artifact_has_tyre_wear_positive_in_the_majority() -> None:
    """The headline: once fuel is removed, isolated tyre wear is positive in most
    real races — the physically-correct result the net slope hides."""
    art = pd.read_csv(_ARTIFACT)
    tyre = art["tyre_slope_s"].dropna()
    assert (tyre > 0).mean() > 0.7
    assert set(art["era"]).issubset(
        {"v8-blown", "hybrid-v6", "wide-aero", "ground-effect",
         "2026-nextgen", "pre-2011"})
