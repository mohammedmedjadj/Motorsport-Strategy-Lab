"""Tests for SC/VSC event extraction and the Bayesian occurrence/rate models."""

from __future__ import annotations

import pandas as pd
import pytest

from src.safety_car.dataset import (
    KIND_PREDICATES,
    extract_periods,
    lap_start_boundaries,
    time_to_lap,
)
from src.safety_car.model import (
    duration_summary,
    occurrence_probability,
    per_lap_rate,
)


def status_log(rows: list[tuple[float, str]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Time": [pd.to_timedelta(t, unit="s") for t, _ in rows],
            "Status": [s for _, s in rows],
        }
    )


class TestExtractPeriods:
    def test_single_sc_period(self) -> None:
        log = status_log([(0, "1"), (100, "24"), (200, "1")])
        periods = extract_periods(log, KIND_PREDICATES["SC"], 500)
        assert periods == [(100.0, 200.0)]

    def test_period_open_at_end_is_closed_at_session_end(self) -> None:
        log = status_log([(0, "1"), (300, "4")])
        periods = extract_periods(log, KIND_PREDICATES["SC"], 450)
        assert periods == [(300.0, 450.0)]

    def test_vsc_deploying_and_ending_codes_are_one_period(self) -> None:
        log = status_log([(0, "1"), (50, "6"), (80, "7"), (90, "1")])
        periods = extract_periods(log, KIND_PREDICATES["VSC"], 500)
        assert periods == [(50.0, 90.0)]

    def test_two_separate_periods(self) -> None:
        log = status_log([(0, "1"), (10, "4"), (30, "1"), (60, "4"), (70, "1")])
        periods = extract_periods(log, KIND_PREDICATES["SC"], 500)
        assert len(periods) == 2

    def test_empty_log(self) -> None:
        assert extract_periods(pd.DataFrame(), KIND_PREDICATES["SC"], 500) == []


class TestLapMapping:
    def test_time_maps_to_containing_lap(self) -> None:
        laps = pd.DataFrame(
            {
                "LapNumber": [1, 1, 2, 2, 3],
                "Driver": ["VER", "LEC", "VER", "LEC", "VER"],
                "LapStartTime": [
                    pd.to_timedelta(t, unit="s") for t in (0, 1, 90, 92, 180)
                ],
            }
        )
        bounds = lap_start_boundaries(laps)
        assert time_to_lap(45, bounds) == 1
        assert time_to_lap(90, bounds) == 2
        assert time_to_lap(179, bounds) == 2
        assert time_to_lap(5000, bounds) == 3  # clipped to last lap
        assert time_to_lap(-10, bounds) == 1  # clipped to first lap


class TestOccurrenceProbability:
    def test_never_exactly_zero_or_one(self) -> None:
        low = occurrence_probability(0, 8)
        high = occurrence_probability(8, 8)
        assert 0 < low.mean < 0.1
        assert 0.9 < high.mean < 1
        assert low.ci_high > low.mean  # interval is real

    def test_half_gives_half(self) -> None:
        est = occurrence_probability(4, 8)
        assert est.mean == pytest.approx(0.5)
        assert est.ci_low < 0.5 < est.ci_high

    def test_interval_narrows_with_more_data(self) -> None:
        small = occurrence_probability(4, 8)
        large = occurrence_probability(40, 80)
        assert (large.ci_high - large.ci_low) < (small.ci_high - small.ci_low)

    def test_invalid_inputs_raise(self) -> None:
        with pytest.raises(ValueError):
            occurrence_probability(5, 4)
        with pytest.raises(ValueError):
            occurrence_probability(0, 0)


class TestPerLapRate:
    def test_rate_matches_frequency_at_scale(self) -> None:
        est = per_lap_rate(10, 1000)
        assert est.mean == pytest.approx(0.0105, abs=1e-4)  # (10+0.5)/1000
        assert est.ci_low < est.mean < est.ci_high

    def test_zero_events_gives_positive_uncertain_rate(self) -> None:
        est = per_lap_rate(0, 500)
        assert est.mean > 0
        assert est.ci_high > 3 * est.mean  # wide interval, honestly wide

    def test_invalid_exposure_raises(self) -> None:
        with pytest.raises(ValueError):
            per_lap_rate(1, 0)


def test_duration_summary_empty_and_filled() -> None:
    empty = duration_summary([])
    assert empty["n"] == 0
    full = duration_summary([3, 5, 4])
    assert full == {"n": 3, "mean": 4.0, "min": 3, "max": 5}


class TestEventMatchValidation:
    """Guards against FastF1's silent fuzzy matching (Monaco 2020 -> Monza)."""

    def test_exact_and_substring_matches_pass(self) -> None:
        from src.ingestion.loader import event_matches_request

        assert event_matches_request("Monaco", "Monaco Grand Prix")
        assert event_matches_request("Spanish", "Spanish Grand Prix")
        assert event_matches_request("  singapore ", "SINGAPORE GRAND PRIX")

    def test_wrong_event_is_rejected(self) -> None:
        from src.ingestion.loader import event_matches_request

        assert not event_matches_request("Monaco", "Italian Grand Prix")
        assert not event_matches_request("Singapore", "Hungarian Grand Prix")
