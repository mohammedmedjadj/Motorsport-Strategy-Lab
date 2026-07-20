"""Ingestion orchestration: load -> clean -> persist derived datasets.

Outputs (all small enough to be committed, per project rules):

- ``data/derived/f1/laps_{season}_{circuit}.csv`` — cleaned laps with flags
- ``data/derived/f1/track_status_{season}_{circuit}.csv`` — status change log
- ``data/derived/f1/sessions.csv`` — one metadata row per race
- ``reports/f1/data_quality_phase1.md`` — lap accounting per race
"""

from __future__ import annotations

import pandas as pd

from src.ingestion.config import F1_DERIVED_DIR, F1_REPORTS_DIR, RACES, RaceId
from src.ingestion.cleaning import EXCLUSION_FLAGS, clean_laps
from src.ingestion.loader import RawRaceData, load_race
from src.ingestion.quality import QualityRow, summarise_race, to_markdown

#: Columns persisted to the derived laps CSV. Everything a later phase needs,
#: nothing that could leak race outcomes (no final classification data).
LAPS_EXPORT_COLUMNS: tuple[str, ...] = (
    "Driver", "DriverNumber", "Team", "LapNumber", "Stint",
    "Compound", "TyreLife", "FreshTyre", "Position", "TrackStatus",
    "lap_time_s", "time_s", "lap_start_time_s",
    "air_temp_c", "track_temp_c", "humidity_pct", "rainfall",
    *EXCLUSION_FLAGS, "is_pace_lap", "stint_crosses_red_flag",
)


def process_race(raw: RawRaceData) -> pd.DataFrame:
    """Clean one race's laps and return the export-ready DataFrame."""
    cleaned = clean_laps(raw.laps, raw.weather)
    missing = [c for c in LAPS_EXPORT_COLUMNS if c not in cleaned.columns]
    if missing:
        raise ValueError(f"{raw.race.slug}: missing expected columns {missing}")
    return cleaned[list(LAPS_EXPORT_COLUMNS)]


def export_track_status(raw: RawRaceData) -> pd.DataFrame:
    """Track-status change log with float-second timestamps."""
    ts = raw.track_status.copy()
    if not ts.empty and "Time" in ts.columns:
        ts["time_s"] = ts["Time"].dt.total_seconds()
    keep = [c for c in ("time_s", "Status", "Message") if c in ts.columns]
    return ts[keep] if keep else pd.DataFrame(columns=["time_s", "Status", "Message"])


def run_all(races: tuple[RaceId, ...] = RACES) -> list[QualityRow]:
    """Run the full ingestion for all scoped races and persist outputs.

    Races that cannot be loaded are **skipped, not fatal**: a rolling scope
    (see ``SEASONS`` in ``config.py``) includes the current season, whose later
    rounds have not been run yet, so FastF1 will legitimately fail to load them.
    A skip is recorded and reported — the same discipline the SC-history phase
    already applies to cancelled editions — so a partial season never aborts the
    whole refresh or silently drops a round without a trace.
    """
    F1_DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    F1_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    quality_rows: list[QualityRow] = []
    session_meta: list[dict[str, object]] = []
    skipped: list[tuple[str, str]] = []

    for race in races:
        print(f"Ingesting {race.slug} ...", flush=True)
        try:
            raw = load_race(race)
        except Exception as exc:  # not-yet-run round, or a genuine load failure
            reason = f"{type(exc).__name__}: {exc}"
            print(f"  skipped {race.slug}: {reason}", flush=True)
            skipped.append((race.slug, reason))
            continue
        cleaned = process_race(raw)
        cleaned.to_csv(F1_DERIVED_DIR / f"laps_{race.slug}.csv", index=False)
        export_track_status(raw).to_csv(
            F1_DERIVED_DIR / f"track_status_{race.slug}.csv", index=False
        )
        quality_rows.append(summarise_race(race.slug, cleaned))
        session_meta.append(
            {
                "season": race.season,
                "circuit": race.circuit,
                "event_name": raw.event_name,
                "scheduled_laps": raw.total_laps,
                "n_drivers": raw.laps["Driver"].nunique(),
            }
        )

    pd.DataFrame(session_meta).to_csv(F1_DERIVED_DIR / "sessions.csv", index=False)
    report = to_markdown(quality_rows)
    if skipped:
        lines = ["", "## Races skipped (not available at ingest time)", ""]
        lines += [f"- {slug}: {reason}" for slug, reason in skipped]
        report = report + "\n".join(lines) + "\n"
    (F1_REPORTS_DIR / "data_quality_phase1.md").write_text(report, encoding="utf-8")
    return quality_rows
