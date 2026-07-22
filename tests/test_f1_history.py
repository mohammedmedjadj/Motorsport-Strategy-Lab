"""The Kaggle F1 history loader: stint reconstruction from pit stops (synthetic,
always runs) and a coverage/sanity guard on the real dropped files (skipped when
they are absent, as the multistop artifact test does)."""

from __future__ import annotations

import pandas as pd
import pytest

from src.data.f1_history_loader import F1_EXTERNAL, load_f1_lap_history

_HAS_FILES = (F1_EXTERNAL / "lap_times.csv").exists()


def test_stint_reconstruction_from_pit_laps(tmp_path, monkeypatch) -> None:
    """A driver who pits on lap 3 and lap 7 of an 8-lap race should read as
    three stints with tyre_age resetting to 0 at each — verified end to end
    through the real loader against a tiny hand-built Kaggle-shaped fixture."""
    ext = tmp_path / "f1"
    ext.mkdir()
    monkeypatch.setattr("src.data.f1_history_loader.F1_EXTERNAL", ext)

    (ext / "lap_times.csv").write_text(
        "raceId,driverId,lap,position,time,milliseconds\n"
        + "".join(f"1,7,{lap},1,x,{90000+lap}\n" for lap in range(1, 9))
    )
    (ext / "races.csv").write_text(
        "raceId,year,round,circuitId,name,date\n1,2023,1,10,Test GP,2023-03-01\n")
    (ext / "circuits.csv").write_text(
        "circuitId,circuitRef,name,lat,lng\n10,testring,Test Ring,0.0,0.0\n")
    (ext / "drivers.csv").write_text("driverId,driverRef\n7,tester\n")
    (ext / "pit_stops.csv").write_text(
        "raceId,driverId,stop,lap,time,duration,milliseconds\n"
        "1,7,1,3,x,25.0,25000\n1,7,2,7,x,24.0,24000\n")

    df = load_f1_lap_history(era_start=2011).sort_values("lap")
    assert list(df["stint"]) == [0, 0, 0, 1, 1, 1, 1, 2]   # stops on 3 and 7
    # tyre_age resets at each new stint.
    assert list(df["tyre_age"]) == [0, 1, 2, 0, 1, 2, 3, 0]


@pytest.mark.skipif(not _HAS_FILES, reason="Kaggle F1 files not dropped")
def test_real_history_covers_far_more_than_four_circuits() -> None:
    """The whole point of this source: it lifts F1 physical-layer coverage from
    the 4 FastF1 circuits to the full calendar. Assert the real data delivers it."""
    df = load_f1_lap_history(era_start=2011)
    assert df["circuitRef"].nunique() >= 20        # was 4 via FastF1
    assert df["year"].min() >= 2011                # era filter honoured
    assert (df["tyre_age"] >= 0).all()
    assert df["lap_time_s"].between(50, 300).mean() > 0.95   # sane lap times
