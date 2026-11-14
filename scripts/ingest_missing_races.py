"""Ingest only the races whose lap files are not committed yet.

The weekly post-race refresh re-ingests the whole calendar and, from an empty
runner cache, exhausts FastF1's hourly call limit before it reaches the current
season: every scheduled run since October stopped on ``RateLimitExceededError``
and the 2026 races after the twelfth were never ingested. The prospective test
(``paper/prospective_protocol.md``) is scored on exactly those races, and its
frozen models are never refitted, so all it needs is their lap and track-status
files. This script loads the missing races only, newest season first, up to a
cap of *successful* ingestions per run, and writes nothing else. A race that
fails to load (not run yet, or refused) does not count against the cap, so the
next three races on the calendar cannot use up a run before the past ones are
tried.

Since FastF1 3.9 the live-timing archive is behind sign-in: FastF1 requires an
active F1 TV Access/Pro/Premium subscription, whose credentials it reads from
``F1_USERNAME`` and ``F1_PASSWORD`` (repository secrets in CI). Without them
every session loads with no laps and this script says so.

    python scripts/ingest_missing_races.py            # up to 6 races
    python scripts/ingest_missing_races.py --max 3
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ingestion.config import F1_DERIVED_DIR, RACES  # noqa: E402
from src.ingestion.loader import load_race  # noqa: E402
from src.ingestion.pipeline import export_track_status, process_race  # noqa: E402


def missing() -> list:
    todo = [r for r in RACES if not (F1_DERIVED_DIR / f"laps_{r.slug}.csv").exists()]
    # Newest first: the most recent races are the ones the prospective test is
    # waiting for, and older gaps fill in on later runs.
    return sorted(todo, key=lambda r: (-r.season, -RACES.index(r)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=6)
    args = parser.parse_args()
    todo = missing()
    print(f"{len(todo)} races without lap files; ingesting up to {args.max}.")
    if not (os.environ.get("F1_USERNAME") and os.environ.get("F1_PASSWORD")):
        print("F1_USERNAME / F1_PASSWORD not set: FastF1 3.9+ cannot read lap "
              "timing without an F1 TV account, so loads will come back empty.")
    done = 0
    for race in todo:
        if done >= args.max:
            break
        print(f"Ingesting {race.slug} ...", flush=True)
        try:
            raw = load_race(race)
        except Exception as exc:  # not run yet, or the API refused
            print(f"  skipped {race.slug}: {type(exc).__name__}: {exc}", flush=True)
            continue
        process_race(raw).to_csv(F1_DERIVED_DIR / f"laps_{race.slug}.csv", index=False)
        export_track_status(raw).to_csv(F1_DERIVED_DIR / f"track_status_{race.slug}.csv", index=False)
        done += 1
        print(f"  wrote laps_{race.slug}.csv", flush=True)
    print(f"Ingested {done} race(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
