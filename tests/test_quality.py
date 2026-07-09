"""Unit tests for the data quality accounting."""

from __future__ import annotations

import pandas as pd

from src.ingestion.cleaning import EXCLUSION_FLAGS
from src.ingestion.quality import summarise_race, to_markdown


def make_cleaned(n_pace: int, n_in_lap: int) -> pd.DataFrame:
    """Minimal cleaned frame: n_pace pace laps + n_in_lap in-laps."""
    n = n_pace + n_in_lap
    df = pd.DataFrame({flag: [False] * n for flag in EXCLUSION_FLAGS})
    df.loc[: n_in_lap - 1, "is_in_lap"] = True if n_in_lap else False
    df["is_pace_lap"] = ~df[list(EXCLUSION_FLAGS)].any(axis=1)
    df["stint_crosses_red_flag"] = False
    return df


def test_summary_counts_match() -> None:
    row = summarise_race("2024_monaco", make_cleaned(n_pace=70, n_in_lap=8))
    assert row.total_laps == 78
    assert row.pace_laps == 70
    assert row.reason_counts["is_in_lap"] == 8
    assert row.pace_pct == 100.0 * 70 / 78


def test_markdown_report_contains_all_races_and_totals() -> None:
    rows = [
        summarise_race("2024_monaco", make_cleaned(70, 8)),
        summarise_race("2024_suzuka", make_cleaned(50, 3)),
    ]
    report = to_markdown(rows)
    assert "2024_monaco" in report and "2024_suzuka" in report
    assert "120/131" in report  # overall totals line


def test_empty_race_does_not_crash() -> None:
    row = summarise_race("empty", make_cleaned(0, 0))
    assert row.pace_pct == 0.0
