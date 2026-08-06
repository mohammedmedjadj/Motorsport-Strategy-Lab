"""Run the Phase 1 ingestion pipeline for the full MVP scope.

Usage (from the repo root)::

    python scripts/run_ingestion.py

Requires the FastF1 cache (populated by Phase 0's availability check) or
network access for the first run.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fastf1  # noqa: E402

from src.ingestion.pipeline import run_all  # noqa: E402


def main() -> int:
    if os.environ.get("FASTF1_DEBUG"):
        # FastF1 logs a generic "Failed to load X data!" at the default log
        # level for *any* underlying cause, including a RateLimitExceededError
        # (github.com/theOehrly/Fast-F1 issue #748) -- indistinguishable from
        # a real outage without this. Every scheduled post-race-refresh run
        # so far has failed to ingest a single race for reasons that look
        # exactly like this (12+ races x ~8 datasets each, from an
        # effectively-empty CI cache, is enough calls to plausibly hit F1's
        # per-hour cap). Set via the workflow, not a project-wide default.
        fastf1.set_log_level("DEBUG")
    rows = run_all()
    print(f"\nIngested {len(rows)} races.")
    for row in rows:
        print(f"  {row.label}: {row.pace_laps}/{row.total_laps} pace laps ({row.pace_pct:.1f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
