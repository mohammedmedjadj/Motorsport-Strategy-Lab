"""Tests for the data-derived pit loss and neutralisation pace ratios."""

from __future__ import annotations

import pandas as pd
import pytest

from src.simulator.pit_loss import (
    estimate_pace_ratios,
    estimate_pit_loss,
    green_median_pace,
)


def make_race_laps(
    pace_s: float = 90.0,
    pit_loss_s: float = 21.0,
    n_laps: int = 30,
    race: str = "2024_synth",
    driver: str = "AAA",
    sc_laps: tuple[int, ...] = (),
    vsc_laps: tuple[int, ...] = (),
    pit_in_lap: int | None = 15,
) -> pd.DataFrame:
    """One driver's race with a known embedded pit loss (split in/out)."""
    rows = []
    for lap in range(1, n_laps + 1):
        status = "4" if lap in sc_laps else ("6" if lap in vsc_laps else "1")
        t = pace_s * {"4": 1.4, "6": 1.2, "1": 1.0}[status]
        is_in = pit_in_lap is not None and lap == pit_in_lap
        is_out = pit_in_lap is not None and lap == pit_in_lap + 1
        if is_in:
            t += pit_loss_s / 2
        if is_out:
            t += pit_loss_s / 2
        rows.append(
            {
                "race": race,
                "Driver": driver,
                "LapNumber": lap,
                "lap_time_s": t,
                "TrackStatus": status,
                "is_in_lap": is_in,
                "is_out_lap": is_out,
                "is_pace_lap": (status == "1") and not is_in and not is_out,
            }
        )
    return pd.DataFrame(rows)


def test_pit_loss_recovers_known_value() -> None:
    laps = pd.concat(
        [make_race_laps(driver=d, pit_loss_s=21.0) for d in ("AAA", "BBB", "CCC")],
        ignore_index=True,
    )
    est = estimate_pit_loss(laps, "synth")
    assert est.median_s == pytest.approx(21.0, abs=0.5)
    assert est.n_events == 3


def test_pit_event_under_sc_is_excluded() -> None:
    clean = make_race_laps(driver="AAA")
    dirty = make_race_laps(driver="BBB", sc_laps=(15, 16))  # stop under SC
    est = estimate_pit_loss(pd.concat([clean, dirty], ignore_index=True), "synth")
    assert est.n_events == 1  # only the green-flag stop counts


def test_no_pit_events_raises_instead_of_inventing() -> None:
    laps = make_race_laps(pit_in_lap=None)
    with pytest.raises(ValueError):
        estimate_pit_loss(laps, "synth")


def test_pace_ratios_measured_and_pooled_fallback() -> None:
    with_sc = make_race_laps(sc_laps=(20, 21, 22), vsc_laps=(25, 26), pit_in_lap=None)
    without = make_race_laps(pit_in_lap=None)
    ratios = estimate_pace_ratios({"has_sc": with_sc, "clean": without})

    assert ratios["has_sc"].sc_ratio == pytest.approx(1.4, abs=0.02)
    assert not ratios["has_sc"].used_pooled_sc
    # The clean circuit never saw an SC: it must borrow the pooled ratio
    # and say so.
    assert ratios["clean"].used_pooled_sc
    assert ratios["clean"].sc_ratio == pytest.approx(1.4, abs=0.02)


def test_green_median_pace_ignores_non_pace_laps() -> None:
    laps = make_race_laps(sc_laps=(5, 6))
    assert green_median_pace(laps) == pytest.approx(90.0)
