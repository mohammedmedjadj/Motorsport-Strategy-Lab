"""Materialise laps (and multi-class fields) for every circuit-season in the
(now widened) endurance scope, from the upstream DuckDB.

Network. **Idempotent and fault-tolerant**: skips anything already materialised,
and reports-and-continues past any race the source cannot return, so one bad
event never aborts the whole run. Run once after widening
``src/data/endurance_scope.py``; the model scripts then read the committed CSVs.

Usage::

    python scripts/materialise_endurance.py            # laps + fields
    python scripts/materialise_endurance.py --laps-only
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.endurance_loader import (  # noqa: E402
    EnduranceLoader,
    derived_path,
    field_path,
    slugify,
)
from src.data.endurance_scope import ENDURANCE_SCOPE  # noqa: E402


def main() -> None:  # pragma: no cover - network
    ap = argparse.ArgumentParser()
    ap.add_argument("--laps-only", action="store_true")
    args = ap.parse_args()

    wrote, skipped, failed = [], [], []
    for series, circuits in ENDURANCE_SCOPE.items():
        loader = EnduranceLoader(series)
        for cs in circuits:
            for year in cs.seasons:
                tag = f"{series} {year} {cs.event} {cs.car_class}"
                lap_path = derived_path(series, year, cs.event, cs.car_class)
                if lap_path.exists():
                    skipped.append(tag)
                else:
                    try:
                        loader.materialise(year, cs.event, cs.car_class)
                        wrote.append(tag)
                        print(f"  [laps] {tag}")
                    except Exception as exc:
                        failed.append((tag, str(exc)))
                        print(f"  [FAIL laps] {tag}: {exc}")
                        continue
                if args.laps_only:
                    continue
                fld = field_path(series, year, cs.event)
                if fld.exists():
                    continue
                try:
                    loader.materialise_field(year, cs.event)
                    print(f"  [field] {series} {year} {cs.event}")
                except Exception as exc:
                    failed.append((f"{tag} FIELD", str(exc)))
                    print(f"  [FAIL field] {tag}: {exc}")

    print(f"\nmaterialised {len(wrote)} new, skipped {len(skipped)} existing, "
          f"{len(failed)} failed.")
    for tag, exc in failed:
        print(f"  FAILED: {tag}: {exc}")


if __name__ == "__main__":
    main()
