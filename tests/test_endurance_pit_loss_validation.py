"""Tests for the leave-one-season-out endurance pit-loss validator."""

from __future__ import annotations

import pandas as pd
import pytest

from src.simulator.endurance_pit_loss_validation import (
    leave_one_race_out_pit_loss_endurance,
    mean_rmse,
)


def make_endurance_laps(
    pace_s: float = 90.0,
    pit_loss_s: float = 60.0,
    n_laps: int = 30,
    car: str = "1",
    pit_lap: int | None = 15,
) -> pd.DataFrame:
    """One car's race with a known embedded green-flag pit loss (split
    in/out), in the schema ``raw_pit_loss_events``/``estimate_pit_loss``
    (``src/simulator/endurance.py``) expect."""
    rows = []
    for lap in range(1, n_laps + 1):
        is_in = pit_lap is not None and lap == pit_lap
        is_out = pit_lap is not None and lap == pit_lap + 1
        t = pace_s
        if is_in:
            t += pit_loss_s / 2
        if is_out:
            t += pit_loss_s / 2
        rows.append(
            {
                "car": car,
                "lap": lap,
                "lap_time_s": t,
                "is_pit_lap": is_in,
                "is_green": True,
                "flag": "GF",
            }
        )
    return pd.DataFrame(rows)


def _season(pit_loss_s: float, cars: tuple[str, ...] = ("1", "2", "3")) -> pd.DataFrame:
    return pd.concat(
        [make_endurance_laps(car=c, pit_loss_s=pit_loss_s) for c in cars],
        ignore_index=True,
    )


def test_stable_pit_loss_gives_low_rmse() -> None:
    laps_by_season = {"2023": _season(60.0), "2024": _season(60.0), "2025": _season(60.0)}
    folds = leave_one_race_out_pit_loss_endurance(laps_by_season, "wec", "synth")
    assert len(folds) == 3
    assert mean_rmse(folds) < 1.0


def test_drifting_pit_loss_gives_higher_rmse() -> None:
    stable = {"2023": _season(60.0), "2024": _season(60.0), "2025": _season(60.0)}
    drifting = {"2023": _season(40.0), "2024": _season(60.0), "2025": _season(80.0)}

    stable_rmse = mean_rmse(leave_one_race_out_pit_loss_endurance(stable, "wec", "synth"))
    drifting_rmse = mean_rmse(leave_one_race_out_pit_loss_endurance(drifting, "wec", "synth"))
    assert drifting_rmse > stable_rmse


def test_reused_car_number_across_seasons_does_not_contaminate_baseline() -> None:
    """Car "1" runs at a very different green pace in 2024 than in 2023/2025.
    If the training pool fused "1"'s laps across seasons (no season
    qualifier), its 2024 pace would drag the baseline used to compute every
    other season's losses too. It must not."""
    fast_car_one_season = make_endurance_laps(car="1", pace_s=200.0, pit_loss_s=60.0)
    normal = _season(60.0)
    laps_by_season = {
        "2023": normal,
        "2024": pd.concat([fast_car_one_season, _season(60.0, cars=("2", "3"))], ignore_index=True),
        "2025": normal,
    }
    folds = leave_one_race_out_pit_loss_endurance(laps_by_season, "wec", "synth")
    fold_2023 = next(f for f in folds if f.held_out == "2023")
    # trained on 2024 + 2025: car "1"'s 2024 laps must be keyed separately
    # from car "1"'s 2025 laps, so the pooled median still recovers 60s.
    assert fold_2023.train_median_s == pytest.approx(60.0, abs=1.0)


def test_too_few_seasons_returns_no_folds() -> None:
    laps_by_season = {"2023": _season(60.0)}
    folds = leave_one_race_out_pit_loss_endurance(laps_by_season, "wec", "synth")
    assert folds == []
