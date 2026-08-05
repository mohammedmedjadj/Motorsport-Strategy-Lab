"""Tests for the leave-one-race-out pit-loss validator."""

from __future__ import annotations

import pandas as pd
import pytest

from src.simulator.pit_loss_validation import leave_one_race_out_pit_loss, mean_rmse
from tests.test_pit_loss import make_race_laps


def _multi_season_laps(pit_loss_by_season: dict[str, float]) -> pd.DataFrame:
    frames = []
    for season, loss in pit_loss_by_season.items():
        for driver in ("AAA", "BBB", "CCC"):
            frames.append(make_race_laps(driver=driver, pit_loss_s=loss, race=season))
    return pd.concat(frames, ignore_index=True)


def test_stable_pit_loss_gives_low_rmse() -> None:
    """When the true pit loss is the same every season, the pooled median
    from the other seasons should predict the held-out season closely."""
    laps = _multi_season_laps({"2023_synth": 21.0, "2024_synth": 21.0, "2025_synth": 21.0})
    folds = leave_one_race_out_pit_loss(laps, "synth")
    assert len(folds) == 3
    assert mean_rmse(folds) < 1.0


def test_drifting_pit_loss_gives_higher_rmse() -> None:
    """When the true pit loss genuinely changes season to season (e.g. a pit
    lane speed limit change), LORO must show it as *worse* transfer, not
    silently average it away."""
    stable = _multi_season_laps({"2023_synth": 21.0, "2024_synth": 21.0, "2025_synth": 21.0})
    drifting = _multi_season_laps({"2023_synth": 15.0, "2024_synth": 21.0, "2025_synth": 27.0})

    stable_rmse = mean_rmse(leave_one_race_out_pit_loss(stable, "synth"))
    drifting_rmse = mean_rmse(leave_one_race_out_pit_loss(drifting, "synth"))
    assert drifting_rmse > stable_rmse


def test_leakage_assertion_holds() -> None:
    """The held-out race's own rows must never reach the training median --
    exercised indirectly: a season with a wildly different loss must not
    silently leak into its own fold's training estimate."""
    laps = _multi_season_laps({"2023_synth": 21.0, "2024_synth": 21.0, "2025_synth": 999.0})
    folds = leave_one_race_out_pit_loss(laps, "synth")
    fold_2025 = next(f for f in folds if f.test_race == "2025_synth")
    # trained only on 2023+2024 (both 21.0s) -- must not be pulled toward 999.
    assert fold_2025.train_median_s == pytest.approx(21.0, abs=0.5)


def test_too_few_seasons_returns_empty_or_single_fold() -> None:
    laps = _multi_season_laps({"2023_synth": 21.0})
    folds = leave_one_race_out_pit_loss(laps, "synth")
    assert folds == []  # one season alone has no "other seasons" to train on
