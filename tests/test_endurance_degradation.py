"""Endurance degradation: synthetic recovery of a known net slope, the real-race
results, and the collinearity guard that stops the model claiming a
fuel/degradation split the data cannot support."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data.base_loader import LAP_COLUMNS
from src.data.endurance_loader import EnduranceLoader
from src.degradation.endurance import (
    build_endurance_frame,
    fit_endurance_degradation,
)

TRUE_NET = 0.08  # s per lap of tyre age


def make_synthetic(n_cars: int = 6, stint_len: int = 25, stints: int = 4,
                   noise_s: float = 0.10, seed: int = 7) -> pd.DataFrame:
    """Cars pitting every ``stint_len`` laps, tyres changed at every stop, with
    a known net within-stint slope. Mirrors the normalised lap schema."""
    rng = np.random.default_rng(seed)
    rows: list[dict[str, object]] = []
    for c in range(n_cars):
        base = 100.0 + 0.5 * c
        lap = 0
        for s in range(stints):
            driver = f"D{c}{s % 2}"
            for age in range(stint_len):
                lap += 1
                is_pit = age == 0 and s > 0
                rows.append({
                    "series": "imsa", "year": 2023, "event": "Synthetic",
                    "circuit": "Synthetic", "car": f"C{c}", "car_class": "GTP",
                    "driver": driver, "lap": lap,
                    "driver_stint": s + 1, "driver_stint_lap": age,
                    "lap_time_s": base + TRUE_NET * age + rng.normal(0, noise_s),
                    "pit_time_s": 30.0 if is_pit else np.nan,
                    "is_pit_lap": is_pit,
                    "flag": "GF", "is_green": True,
                    "tyre_age": float(age), "is_tyre_change": is_pit,
                    "air_temp_c": 20.0, "track_temp_c": 30.0,
                    "humidity_pct": 50.0, "raining": False,
                    "race_duration_min": 360,
                })
    return pd.DataFrame(rows)[list(LAP_COLUMNS)]


def test_recovers_a_known_net_slope() -> None:
    fit = fit_endurance_degradation(build_endurance_frame(make_synthetic()))
    assert fit.net_slope.value == pytest.approx(TRUE_NET, abs=0.02)
    assert fit.net_slope.ci_low <= TRUE_NET <= fit.net_slope.ci_high


def test_frame_drops_non_green_and_pit_laps_and_resets_fuel_counter() -> None:
    laps = make_synthetic(n_cars=2, stints=3)
    # Neutralise a handful of laps; they must not reach the fit.
    laps.loc[laps["lap"].between(5, 8), "flag"] = "FCY"
    laps.loc[laps["lap"].between(5, 8), "is_green"] = False
    frame = build_endurance_frame(laps)
    assert frame["is_green"].all()
    assert not frame["is_pit_lap"].any()
    # laps_since_refuel restarts at each pit visit, so it never runs away.
    assert frame["laps_since_refuel"].max() < len(laps)
    assert (frame["laps_since_refuel"] >= 0).all()
    # The car-driver fixed-effect key exists and splits drivers within a car.
    assert frame["unit"].str.contains("::").all()


def test_real_races_are_not_separable_and_only_net_is_quoted() -> None:
    """On both real races fuel and tyre age are ~collinear after fixed effects,
    so the model must refuse to present the decomposition as identified."""
    for series, year, event, cls in (
        ("imsa", 2023, "Watkins Glen", "GTP"),
        ("wec", 2024, "Spa", "HYPERCAR"),
    ):
        laps = EnduranceLoader(series).load_laps(year, event, cls)
        fit = fit_endurance_degradation(build_endurance_frame(laps))
        assert fit.fuel_deg_correlation > 0.9
        assert fit.separable is False
        assert fit.n_laps > 500 and fit.rmse_s < 3.0


def test_spa_has_measurable_net_degradation_watkins_glen_does_not() -> None:
    """Two contrasting regimes, both honest: at Spa the net slope is clearly
    positive; at Watkins Glen the fuel gain cancels the tyre loss and the
    interval covers zero."""
    spa = fit_endurance_degradation(build_endurance_frame(
        EnduranceLoader("wec").load_laps(2024, "Spa", "HYPERCAR")))
    glen = fit_endurance_degradation(build_endurance_frame(
        EnduranceLoader("imsa").load_laps(2023, "Watkins Glen", "GTP")))
    assert spa.net_slope.ci_low > 0  # significantly positive
    assert glen.net_slope.ci_low < 0 < glen.net_slope.ci_high  # covers zero


def test_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="cannot fit an empty frame"):
        fit_endurance_degradation(pd.DataFrame())
    empty = make_synthetic(n_cars=1, stints=1)
    empty["is_green"] = False
    with pytest.raises(ValueError, match="no usable green laps"):
        build_endurance_frame(empty)
