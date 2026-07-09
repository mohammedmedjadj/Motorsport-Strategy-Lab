"""Run the Phase 1 ingestion pipeline for the full MVP scope.

Usage (from the repo root)::

    python scripts/run_ingestion.py

Requires the FastF1 cache (populated by Phase 0's availability check) or
network access for the first run.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ingestion.pipeline import run_all  # noqa: E402


def main() -> int:
    rows = run_all()
    print(f"\nIngested {len(rows)} races.")
    for row in rows:
        print(f"  {row.label}: {row.pace_laps}/{row.total_laps} pace laps ({row.pace_pct:.1f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
