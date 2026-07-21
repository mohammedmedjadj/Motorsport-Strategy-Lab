"""Materialise the multi-class field for every in-scope endurance race.

The inter-class traffic and track-position primitives need the *whole field* of
a race (every class, to solve the lapping problem), not just the prime class the
degradation models use. Those field CSVs were originally produced by a one-off
and — alone among the project's derived data — had no committed generator, so
they could neither be refreshed nor audited for drift. This is that generator.

It walks ``ENDURANCE_SCOPE`` (the frozen circuit-season list the rest of the
project already declares) and writes one ``field_<series>_<year>_<event>.csv``
per race under ``data/derived/endurance/field/``. Fault-tolerant like the F1
pipeline: a race absent from the source is reported and skipped, never faked.

Network required (reads the upstream DuckDB). Offline consumers read the
committed CSVs. Re-running reproduces the existing files byte-for-byte.

Usage (from the repo root)::

    python scripts/materialise_endurance_fields.py           # all in-scope races
    python scripts/materialise_endurance_fields.py --missing # only ones not yet on disk
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.endurance_loader import EnduranceLoader, field_path  # noqa: E402
from src.data.endurance_scope import ENDURANCE_SCOPE  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--missing", action="store_true",
                        help="only materialise races whose field CSV is absent")
    args = parser.parse_args()

    written, skipped_existing, failed = [], [], []
    for series, scopes in ENDURANCE_SCOPE.items():
        loader = EnduranceLoader(series)
        for scope in scopes:
            for year in scope.seasons:
                path = field_path(series, year, scope.event)
                if args.missing and path.exists():
                    skipped_existing.append(path.name)
                    continue
                try:
                    loader.materialise_field(year, scope.event)
                    written.append(path.name)
                    print(f"  wrote {path.name}")
                except Exception as exc:  # noqa: BLE001 — report, never fake
                    failed.append(f"{series} {year} {scope.event}: {type(exc).__name__}: {exc}")
                    print(f"  SKIP  {series} {year} {scope.event}: {exc}")

    print(f"\n{len(written)} written, {len(skipped_existing)} already present, "
          f"{len(failed)} skipped")
    if failed:
        print("skipped (absent from source or empty):")
        for f in failed:
            print(f"  - {f}")


if __name__ == "__main__":
    main()
