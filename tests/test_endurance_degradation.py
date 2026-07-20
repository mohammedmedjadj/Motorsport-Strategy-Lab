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
    frame_diagnostics,
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


def test_field_wide_slow_laps_are_trimmed_even_when_most_of_a_car_is_affected() -> None:
    """Regression test for a real anomaly found in IMSA Road America 2024: laps
    2-3 are field-wide standing-start laps (median ~2x green pace across all
    cars) but flagged "GF" in the source. A per-car quantile trim alone cannot
    catch this in a short race, because the anomaly inflates a large enough
    share of each car's own laps to push its own 90th-percentile cutoff above
    the anomaly (that bug produced a nonsense -0.53 s/lap slope with RMSE
    13.9s before the field-wide filter was added). Reproduced synthetically so
    it does not depend on network access."""
    laps = make_synthetic(n_cars=6, stint_len=30, stints=1, noise_s=0.05)
    # Make laps 2 and 3 field-wide slow for every car (a "standing start").
    laps.loc[laps["lap"].isin([2, 3]), "lap_time_s"] += 100.0
    frame = build_endurance_frame(laps)
    assert not frame["lap"].isin([2, 3]).any()
    fit = fit_endurance_degradation(frame)
    assert fit.net_slope.value == pytest.approx(TRUE_NET, abs=0.02)
    assert fit.rmse_s < 1.0  # not inflated by the field-wide anomaly


def test_road_america_2024_no_longer_an_outlier() -> None:
    """The real race the field-wide trim was built for: before the fix this
    race's slope was -0.53 s/lap with an 13.9s RMSE, wildly inconsistent with
    its own 2023 (-0.02) and 2025 (+0.01) editions. After the fix it must sit
    in the same order of magnitude and RMSE range as ordinary races."""
    laps = EnduranceLoader("imsa").load_laps(2024, "Road America", "GTP")
    fit = fit_endurance_degradation(build_endurance_frame(laps))
    assert fit.rmse_s < 3.0
    assert abs(fit.net_slope.value) < 0.15


def test_frame_diagnostics_accounts_for_every_lap() -> None:
    """Every excluded lap must be attributed to exactly one stage: the stage
    counts plus what's kept must reconstruct the raw total (the data-quality
    reports quote these numbers directly, so the identity must hold exactly)."""
    laps = EnduranceLoader("imsa").load_laps(2023, "Watkins Glen", "GTP")
    d = frame_diagnostics(laps)
    assert d.total_laps == len(laps)
    accounted = (
        d.non_green_or_pit + d.missing_tyre_age + d.field_wide_trimmed
        + d.per_car_trimmed + d.insufficient_car_laps + d.kept
    )
    assert accounted == d.total_laps
    assert d.kept == len(build_endurance_frame(laps))
    assert d.pct_kept == pytest.approx(100.0 * d.kept / d.total_laps)


def test_frame_diagnostics_flags_road_america_2024_as_heavily_trimmed() -> None:
    """The anomalous race (see the field-wide trim tests above) must show up
    here as an outlier on the trim/insufficient columns, not just in the
    fitted slope — this is the number the data-quality report actually cites."""
    laps = EnduranceLoader("imsa").load_laps(2024, "Road America", "GTP")
    d = frame_diagnostics(laps)
    assert d.field_wide_trimmed > 40
    assert d.insufficient_car_laps > 0  # at least one car dropped outright


def test_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="cannot fit an empty frame"):
        fit_endurance_degradation(pd.DataFrame())
    empty = make_synthetic(n_cars=1, stints=1)
    empty["is_green"] = False
    with pytest.raises(ValueError, match="no usable green laps"):
        build_endurance_frame(empty)
