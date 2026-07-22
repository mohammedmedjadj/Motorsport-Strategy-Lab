"""Full-calendar F1 pit loss: the estimator recovers a known green-flag loss,
rejects a Safety-Car-flanked stop it cannot see a flag for, and the committed
artifact carries the street flag with permanent circuits in a sane band."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.ingestion.config import F1_DERIVED_DIR
from src.simulator.f1_history_pit_loss import estimate_history_pit_loss

_ARTIFACT = F1_DERIVED_DIR / "history_pit_loss.csv"


def _race(green: float = 90.0, loss_in: float = 15.0, loss_out: float = 10.0,
          n_drivers: int = 8, race_laps: int = 24, sc_lap: int | None = None):
    """A race where every driver makes one green stop (staggered) costing a known
    loss; optionally one field-wide Safety-Car lap that must be excluded."""
    lap_rows, pit_rows = [], []
    for i in range(n_drivers):
        stop = 8 + i                      # staggered green stops
        for lap in range(1, race_laps + 1):
            t = green
            if lap == stop:
                t = green + loss_in       # in-lap
            elif lap == stop + 1:
                t = green + loss_out      # out-lap
            elif sc_lap is not None and lap == sc_lap:
                t = green * 1.6           # whole field slow (SC)
            lap_rows.append({"raceId": 1, "circuitRef": "testring",
                             "era": "ground-effect", "driverId": i, "lap": lap,
                             "lap_time_s": t})
        pit_rows.append({"raceId": 1, "driverId": i, "lap": stop})
        if sc_lap is not None and i == 0:
            pit_rows.append({"raceId": 1, "driverId": i, "lap": sc_lap})  # SC stop
    return pd.DataFrame(lap_rows), pd.DataFrame(pit_rows)


def test_recovers_a_known_green_pit_loss() -> None:
    laps, pits = _race(loss_in=15.0, loss_out=10.0)
    out = estimate_history_pit_loss(laps, pits)
    assert len(out) == 1
    assert out.iloc[0]["pit_loss_median_s"] == pytest.approx(25.0, abs=0.5)
    assert out.iloc[0]["n_stops"] == 8


def test_safety_car_flanked_stop_is_excluded() -> None:
    """The SC stop's own lap is field-wide slow, so it must not be counted — the
    same stops-only-under-green discipline as the FastF1 estimator, enforced
    without a flag."""
    laps, pits = _race(sc_lap=20)
    out = estimate_history_pit_loss(laps, pits)
    # 8 green stops counted, the one SC-lap stop dropped.
    assert out.iloc[0]["n_stops"] == 8


@pytest.mark.skipif(not _ARTIFACT.exists(), reason="pit-loss artifact not generated")
def test_committed_artifact_flags_streets_and_permanents_are_sane() -> None:
    art = pd.read_csv(_ARTIFACT)
    assert "street" in art.columns
    assert bool(art.loc[art["circuit"] == "monaco", "street"].iloc[0]) is True
    # Permanent circuits agree with real F1 pit lanes: a 15-30 s band.
    perm = art[(~art["street"]) & (art["era"] == "ground-effect")]["pit_loss_median_s"]
    assert perm.between(15, 32).mean() > 0.8
