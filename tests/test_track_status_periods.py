"""Unit tests for track-status period counting (Phase 0 availability script).

The period counter is the seed of the Phase 3 SC/VSC model, so its edge cases
are pinned down early: combined status codes, repeated rows within one
period, multiple separate periods, and empty input.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_data_availability import _count_status_periods  # noqa: E402


def _status_df(statuses: list[str]) -> pd.DataFrame:
    return pd.DataFrame({"Status": statuses})


def test_empty_input_has_zero_periods() -> None:
    assert _count_status_periods(_status_df([]), "4") == 0


def test_single_sc_period_with_repeated_rows_counts_once() -> None:
    # Livetiming can emit several rows while the same SC period is active.
    df = _status_df(["1", "4", "4", "4", "1"])
    assert _count_status_periods(df, "4") == 1


def test_two_separate_sc_periods() -> None:
    df = _status_df(["1", "4", "1", "2", "4", "1"])
    assert _count_status_periods(df, "4") == 2


def test_combined_codes_are_detected() -> None:
    # Status strings can combine codes, e.g. "24" = yellow flag + safety car.
    df = _status_df(["1", "24", "1"])
    assert _count_status_periods(df, "4") == 1


def test_period_active_at_end_of_session_still_counts() -> None:
    df = _status_df(["1", "6", "7"])  # VSC deployed, then ending
    assert _count_status_periods(df, "6") == 1


def test_code_absent_returns_zero() -> None:
    df = _status_df(["1", "2", "1"])
    assert _count_status_periods(df, "5") == 0
