"""Materialise real race-day weather for F1 races from the Open-Meteo archive.

Joins the Kaggle ``races`` (date) to ``circuits`` (lat/lng) — so this is fully
automatic, no hand-entered dates — and writes one row per race with a wet flag.
The strategic payoff: wet races can then be held out of dry-degradation fits
instead of silently contaminating them.

Network (one Open-Meteo call per race). **Resumable**: re-running skips races
already in the output, so a large fetch can be done in passes. Writes
``data/derived/f1/weather.csv``.

Usage::

    python scripts/run_f1_weather.py --from 2011 --limit 20   # a demo pass
    python scripts/run_f1_weather.py --from 2011               # everything
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.f1_history_loader import F1_EXTERNAL  # noqa: E402
from src.ingestion.config import F1_DERIVED_DIR  # noqa: E402
from src.weather.archive import race_weather  # noqa: E402

OUT_CSV = F1_DERIVED_DIR / "weather.csv"


def main() -> None:  # pragma: no cover - network
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", type=int, default=2011)
    ap.add_argument("--limit", type=int, default=0, help="0 = no limit")
    args = ap.parse_args()

    races = pd.read_csv(F1_EXTERNAL / "races.csv", na_values=["\\N"])
    circuits = pd.read_csv(F1_EXTERNAL / "circuits.csv", na_values=["\\N"])
    df = (races[races["year"] >= args.start]
          .merge(circuits[["circuitId", "circuitRef", "lat", "lng"]], on="circuitId")
          .dropna(subset=["date", "lat", "lng"]))

    done = set()
    if OUT_CSV.exists():
        prev = pd.read_csv(OUT_CSV)
        done = set(prev["raceId"])
        rows = prev.to_dict("records")
    else:
        rows = []

    todo = df[~df["raceId"].isin(done)]
    if args.limit:
        todo = todo.head(args.limit)

    for _, r in todo.iterrows():
        try:
            w = race_weather(float(r["lat"]), float(r["lng"]), str(r["date"]))
        except Exception as exc:
            print(f"  skip {int(r['raceId'])} {r['circuitRef']} {r['date']}: {exc}")
            continue
        rows.append({"raceId": int(r["raceId"]), "year": int(r["year"]),
                     "circuitRef": r["circuitRef"], **w.row()})
        tag = "WET " if w.wet else "dry "
        print(f"  [{tag}] {int(r['year'])} {r['circuitRef']:14s} "
              f"precip={w.precip_mm:5.1f}mm temp={w.temp_mean_c:4.1f}C")

    out = pd.DataFrame(rows).sort_values(["year", "circuitRef"])
    F1_DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_CSV, index=False)
    n_wet = int(out["wet"].sum())
    print(f"\n{len(out)} races with weather, {n_wet} wet "
          f"({n_wet / len(out):.0%}). wrote {OUT_CSV}")


if __name__ == "__main__":
    main()
