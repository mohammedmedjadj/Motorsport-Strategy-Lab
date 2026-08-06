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


def test_run_all_refuses_to_overwrite_committed_data_on_total_failure(
    monkeypatch, tmp_path
) -> None:
    """A total ingest failure (every race unavailable) must not silently wipe
    sessions.csv when it already holds real, previously-ingested rows -- this
    happened for real on 2026-08-06 when FastF1 fell back to a livetiming
    mirror and reported SessionNotAvailableError for every race, including
    seasons finished years ago, and the empty result got auto-committed over
    good data (commit 1ae78a4, reverted in 0ddce0c)."""
    derived_dir = tmp_path / "derived"
    derived_dir.mkdir()
    monkeypatch.setattr(pipeline, "F1_DERIVED_DIR", derived_dir)
    monkeypatch.setattr(pipeline, "F1_REPORTS_DIR", tmp_path / "reports")

    existing = derived_dir / "sessions.csv"
    existing.write_text("season,circuit,event_name,scheduled_laps,n_drivers\n2023,monaco,Monaco Grand Prix,78,20\n")

    def all_unavailable(race: RaceId):
        raise LookupError(f"{race.slug}: SessionNotAvailableError")

    monkeypatch.setattr(pipeline, "load_race", all_unavailable)

    races = (RaceId(season=2023, gp_name="Monaco", circuit="monaco"),)
    try:
        pipeline.run_all(races)
        assert False, "expected RuntimeError on a total-failure overwrite attempt"
    except RuntimeError as exc:
        assert "already ingested" in str(exc)

    # The pre-existing file must be untouched, not overwritten with an empty one.
    assert "2023,monaco" in existing.read_text()
