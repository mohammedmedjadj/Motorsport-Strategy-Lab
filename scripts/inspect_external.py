"""Report the schema of every CSV dropped under ``data/external/``.

So a new external source is built against its *real* columns, never guessed:
drop the files, run this, and it prints each file's shape, columns and a few
sample rows. Read-only; touches nothing else.

Usage::

    python scripts/inspect_external.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ingestion.config import REPO_ROOT  # noqa: E402

EXTERNAL = REPO_ROOT / "data" / "external"


def main() -> None:
    csvs = sorted(EXTERNAL.rglob("*.csv"))
    if not csvs:
        print(f"No CSVs under {EXTERNAL}. Drop the Kaggle files there and re-run.")
        return
    for csv in csvs:
        rel = csv.relative_to(REPO_ROOT)
        try:
            df = pd.read_csv(csv, nrows=2000)
        except Exception as exc:
            print(f"\n=== {rel} — UNREADABLE: {exc}")
            continue
        print(f"\n=== {rel}  ({len(df)} rows sampled, {df.shape[1]} cols)")
        print("columns:", list(df.columns))
        print(df.head(3).to_string(index=False))


if __name__ == "__main__":
    main()
