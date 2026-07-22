"""Enumerate every prototype-class race in the upstream DuckDB, so the
degradation / simulator scope can be widened to **verified** event names rather
than hand-picked or guessed ones.

Answers the honest gap flagged by the data audit: the neutralisation model
already uses all ~96 races, but the physical-modelling scope
(``src/data/endurance_scope.py``) covers only 4 IMSA + 4 WEC circuits. This
script lists what is actually available and eligible (enough cars and laps for a
degradation fit), season by season, so widening the scope is a data-driven edit.

Network (hits the Hugging Face DuckDB). Writes
``data/derived/endurance/available_events.csv``. Nothing here is used by a model
directly — it is a scoping aid a human reads before editing the scope file.

Usage::

    python scripts/discover_endurance_events.py --from 2021 --to 2026
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.endurance_loader import EnduranceLoader  # noqa: E402
from src.ingestion.config import ENDURANCE_DERIVED_DIR  # noqa: E402

#: The top prototype class per series (what the current scope models).
PROTOTYPE_CLASS = {"imsa": "GTP", "wec": "HYPERCAR"}

#: Eligibility floor for a degradation fit: at least this many cars, and a race
#: long enough to have within-stint pace to fit. Conservative, honest cut-offs.
MIN_CARS = 4
MIN_LAPS = 40


def _event_summary(loader: EnduranceLoader, year: int, event: str,
                   car_class: str) -> dict | None:  # pragma: no cover - network
    raw = loader.fetch_remote(year, event, car_class)
    if raw.empty:
        return None
    n_cars = raw["car"].nunique()
    max_laps = int(raw.groupby("car")["lap"].max().max())
    return {
        "series": loader.series, "year": year, "event": event,
        "car_class": car_class, "n_cars": int(n_cars), "max_laps": max_laps,
        "eligible": bool(n_cars >= MIN_CARS and max_laps >= MIN_LAPS),
    }


def main() -> None:  # pragma: no cover - network
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", type=int, default=2021)
    ap.add_argument("--to", dest="end", type=int, default=2026)
    args = ap.parse_args()

    rows = []
    for series, car_class in PROTOTYPE_CLASS.items():
        loader = EnduranceLoader(series)
        for year in range(args.start, args.end + 1):
            try:
                events = loader.list_events(year)
            except Exception as exc:  # a year with no data upstream
                print(f"  {series} {year}: skipped ({exc})")
                continue
            for event in events:
                summary = _event_summary(loader, year, event, car_class)
                if summary is not None:
                    rows.append(summary)
                    tag = "ok " if summary["eligible"] else "thin"
                    print(f"  [{tag}] {series} {year} {event}: "
                          f"{summary['n_cars']} cars, {summary['max_laps']} laps")

    table = pd.DataFrame(rows).sort_values(["series", "year", "event"])
    ENDURANCE_DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    out = ENDURANCE_DERIVED_DIR / "available_events.csv"
    table.to_csv(out, index=False)
    eligible = table[table["eligible"]]
    print(f"\n{len(table)} prototype races found, {len(eligible)} eligible "
          f"(>= {MIN_CARS} cars, >= {MIN_LAPS} laps).")
    print(f"wrote {out}")
    print("\nNext: widen src/data/endurance_scope.py to the eligible events, "
          "then run scripts/materialise_endurance_fields.py and "
          "scripts/run_endurance_models.py.")


if __name__ == "__main__":
    main()
