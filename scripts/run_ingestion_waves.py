"""Ingest the whole F1 calendar across FastF1's hourly rate limit.

FastF1's upstream API allows **500 calls an hour**, and one race costs roughly
ten, so a single run gets through about fifty rounds and then skips the rest
with ``RateLimitExceededError``. The scope is 115 rounds, so it takes three
windows.

Already-cached races cost no API calls, so each wave flies through what the
previous one fetched and spends its whole budget on new rounds. The pipeline
already treats an unloadable race as a skip rather than a failure, which is
what makes this safe to repeat: a wave that hits the limit loses nothing.

Run it with ``python scripts/run_ingestion_waves.py``; it stops as soon as a
wave adds no new races, so it costs one extra wave at the end rather than a
fixed number.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ingestion.config import F1_DERIVED_DIR, RACES  # noqa: E402
from src.ingestion.pipeline import run_all  # noqa: E402

#: FastF1's window is an hour; a little over avoids racing the reset.
WAIT_SECONDS = 3900
MAX_WAVES = 6


def ingested() -> set[str]:
    return {p.stem.removeprefix("laps_") for p in F1_DERIVED_DIR.glob("laps_*.csv")}


def main() -> None:
    target = {race.slug for race in RACES}
    for wave in range(1, MAX_WAVES + 1):
        before = ingested()
        remaining = sorted(target - before)
        print(f"\n=== wave {wave}: {len(before)} ingested, "
              f"{len(remaining)} still to fetch ===", flush=True)
        if not remaining:
            print("scope complete")
            return

        run_all()
        after = ingested()
        gained = len(after) - len(before)
        print(f"wave {wave} added {gained} race(s); {len(target - after)} left",
              flush=True)

        if not (target - after):
            print("scope complete")
            return
        if gained == 0:
            # Not the rate limit: the remaining rounds have not been run yet,
            # or genuinely cannot be loaded. Waiting another hour changes
            # nothing, so say so rather than sleeping through it.
            print("no progress this wave — the remaining rounds are not "
                  "rate-limited, they are unavailable:")
            for slug in sorted(target - after):
                print(f"  - {slug}")
            return
        if wave < MAX_WAVES:
            print(f"sleeping {WAIT_SECONDS // 60} min for the rate-limit window",
                  flush=True)
            time.sleep(WAIT_SECONDS)


if __name__ == "__main__":
    main()
