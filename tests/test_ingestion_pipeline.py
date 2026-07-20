"""Ingestion orchestration resilience: a rolling scope includes the current
season, whose later rounds have not been run yet, so ``run_all`` must skip a
race it cannot load rather than aborting the whole refresh."""

from __future__ import annotations

from src.ingestion import pipeline
from src.ingestion.config import RaceId


def test_run_all_skips_unavailable_races_and_records_them(monkeypatch, tmp_path) -> None:
    # Redirect outputs so the test never touches committed data.
    monkeypatch.setattr(pipeline, "F1_DERIVED_DIR", tmp_path / "derived")
    monkeypatch.setattr(pipeline, "F1_REPORTS_DIR", tmp_path / "reports")

    def not_run_yet(race: RaceId):
        raise LookupError(f"{race.slug}: session not available")

    monkeypatch.setattr(pipeline, "load_race", not_run_yet)

    races = (
        RaceId(season=2026, gp_name="Singapore", circuit="singapore"),
        RaceId(season=2026, gp_name="Japanese", circuit="suzuka"),
    )
    rows = pipeline.run_all(races)

    # No crash, nothing ingested, and every skip is reported by slug + reason.
    assert rows == []
    report = (tmp_path / "reports" / "data_quality_phase1.md").read_text(encoding="utf-8")
    assert "skipped" in report.lower()
    assert "2026_singapore" in report and "2026_suzuka" in report
    assert (tmp_path / "derived" / "sessions.csv").exists()
