"""Leave-one-race-out CV for the endurance degradation model: synthetic
recovery, leakage guard, and the real 4-circuit result per series."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data.endurance_loader import EnduranceLoader
from src.degradation.endurance import build_endurance_frame
from src.degradation.endurance_validation import (
    leave_one_race_out_endurance,
    mean_r2,
)
from tests.test_endurance_degradation import make_synthetic

IMSA_EVENTS = ("Watkins Glen", "Sebring", "Mosport", "Road America")
WEC_EVENTS = ("Spa", "Fuji", "Bahrain", "Imola")


def _frames(series: str, year: int, events: tuple[str, ...], car_class: str):
    return {
        ev: build_endurance_frame(EnduranceLoader(series).load_laps(year, ev, car_class))
        for ev in events
    }


@pytest.fixture(scope="module")
def imsa_frames():
    return _frames("imsa", 2023, IMSA_EVENTS, "GTP")


@pytest.fixture(scope="module")
def wec_frames():
    return _frames("wec", 2024, WEC_EVENTS, "HYPERCAR")


def test_synthetic_slope_transfers_across_races() -> None:
    """A slope that is truly identical across races must transfer with a
    strongly positive within-stint R2 — the positive control for the method."""
    frames = {
        f"race{i}": build_endurance_frame(make_synthetic(seed=100 + i))
        for i in range(4)
    }
    folds = leave_one_race_out_endurance(frames)
    assert mean_r2(folds) > 0.5
    for f in folds:
        assert f.pooled_slope == pytest.approx(0.08, abs=0.02)


def test_test_race_never_leaks_into_the_pooled_fit(imsa_frames) -> None:
    folds = leave_one_race_out_endurance(imsa_frames)
    assert {f.test_event for f in folds} == set(IMSA_EVENTS)
    assert len(folds) == 4


def test_requires_at_least_two_races() -> None:
    with pytest.raises(ValueError, match="at least 2 races"):
        leave_one_race_out_endurance({"only_one": pd.DataFrame()})


def test_imsa_slopes_do_not_transfer_across_circuits(imsa_frames) -> None:
    """The headline finding: pooled (other-race) slopes predict a held-out
    IMSA race's within-stint shape no better than a flat line."""
    folds = leave_one_race_out_endurance(imsa_frames)
    assert mean_r2(folds) < 0.1
    assert all(f.r2_within < 0.1 for f in folds)


def test_wec_slopes_do_not_transfer_and_can_flip_sign(wec_frames) -> None:
    """WEC is, if anything, worse: pooled and own slopes disagree in sign for
    at least one held-out race (Bahrain/Imola)."""
    folds = leave_one_race_out_endurance(wec_frames)
    assert mean_r2(folds) < 0.1
    sign_flips = [f for f in folds if np.sign(f.pooled_slope) != np.sign(f.own_slope)]
    assert len(sign_flips) >= 1
