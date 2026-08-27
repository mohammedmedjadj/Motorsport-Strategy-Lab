"""Generate the per-class report set for every endurance class.

Four documents per class — lap accounting, fitted degradation, transfer
validation, full-race strategy — each covering **every** race-season of that
class. Run after any refit; the reports are read from the committed CSVs, so
they change in the same commit the data does.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.reporting.class_reports import write_all  # noqa: E402


def main() -> None:
    written = write_all()
    for path in written:
        print(f"wrote {path}")
    print(f"\n{len(written)} reports across {len(written) // 4} classes")


if __name__ == "__main__":
    main()
