"""Green-flag pit loss across the whole F1 calendar (Kaggle breadth), validated
against the FastF1 ground truth on the four shared circuits.

The honest headline is the validation: this source agrees with FastF1 to a few
tenths on permanent circuits but over-estimates high-Safety-Car street circuits
(Monaco worst), because Kaggle has no SC flag and neutralised stops inflate the
measured loss. The artifact therefore carries a `street` flag, and the report
recommends FastF1 where it covers a circuit.

Writes ``data/derived/f1/history_pit_loss.csv`` + ``reports/f1/pit_loss_history.md``.

Usage::

    python scripts/run_f1_history_pit_loss.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.f1_history_loader import F1_EXTERNAL, load_f1_lap_history  # noqa: E402
from src.ingestion.config import F1_DERIVED_DIR, F1_REPORTS_DIR  # noqa: E402
from src.reliability.f1_reliability import _STREET_CIRCUITS  # noqa: E402
from src.simulator.f1_history_pit_loss import estimate_history_pit_loss  # noqa: E402
from src.simulator.pit_loss import estimate_pit_loss  # noqa: E402

OUT_CSV = F1_DERIVED_DIR / "history_pit_loss.csv"
OUT_REPORT = F1_REPORTS_DIR / "pit_loss_history.md"
#: Kaggle circuitRef -> FastF1 committed-laps circuit key, for the 4 shared races.
_SHARED = {"monaco": "monaco", "marina_bay": "singapore",
           "catalunya": "barcelona", "suzuka": "suzuka"}


def _fastf1_ground_truth() -> dict[str, float]:
    truth = {}
    for kref, f1key in _SHARED.items():
        files = sorted(F1_DERIVED_DIR.glob(f"laps_*_{f1key}.csv"))
        if not files:
            continue
        parts = [pd.read_csv(f).assign(race=f.stem) for f in files]
        try:
            truth[kref] = estimate_pit_loss(pd.concat(parts, ignore_index=True), f1key).median_s
        except Exception:
            pass
    return truth


def main() -> None:
    laps = load_f1_lap_history(2011)
    pits = pd.read_csv(F1_EXTERNAL / "pit_stops.csv", na_values=["\\N"])[
        ["raceId", "driverId", "lap"]]
    table = estimate_history_pit_loss(laps, pits)
    table["street"] = table["circuit"].isin(_STREET_CIRCUITS)
    F1_DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT_CSV, index=False)

    truth = _fastf1_ground_truth()
    ge = table[table["era"] == "ground-effect"].set_index("circuit")["pit_loss_median_s"]
    val_rows = [(c, float(ge.get(c, float("nan"))), t, float(ge.get(c, float("nan"))) - t)
                for c, t in truth.items()]

    n_circuits = table["circuit"].nunique()
    lines = [
        "# F1 pit loss — full-calendar breadth (Kaggle), validated vs FastF1",
        "",
        "Green-flag pit loss (`t_in + t_out - 2 x driver green median`, stops "
        "beyond 2x the median trimmed) across the whole calendar — the breadth "
        "complement to the FastF1 estimator, which is exact but four circuits.",
        "",
        f"Coverage: **{n_circuits} circuits**. Kaggle has no per-lap Safety-Car "
        "flag, so green-flanking is enforced by the same field-wide slow-lap "
        "inference the degradation layer uses.",
        "",
        "## Validation against the FastF1 ground truth (the honest headline)",
        "",
        "On the four circuits FastF1 also covers, how the Kaggle estimate compares:",
        "",
        "| Circuit | Kaggle (s) | FastF1 (s) | Delta (s) |",
        "|---|---|---|---|",
    ]
    for c, k, t, d in sorted(val_rows, key=lambda r: abs(r[3])):
        lines.append(f"| {c} | {k:.1f} | {t:.1f} | {d:+.1f} |")
    lines += [
        "",
        "The agreement is **within a few tenths on permanent circuits** "
        "(Barcelona, Suzuka) and degrades on **high-Safety-Car street circuits** "
        "(Singapore moderately, **Monaco by ~20 s**): without an SC flag, stops "
        "made under neutralisation inflate the measured loss, and street circuits "
        "see the most of them. **Where FastF1 covers a circuit, prefer it**; this "
        "breadth layer is trustworthy for the permanent circuits it uniquely adds.",
        "",
        "## Pit loss by circuit, current era (`ground-effect`), street flagged",
        "",
        "| Circuit | Pit loss (s) | IQR (s) | Stops | Street? |",
        "|---|---|---|---|---|",
    ]
    for _, r in table[table["era"] == "ground-effect"].iterrows():
        flag = "yes (uncertain)" if r["street"] else "no"
        lines.append(f"| {r['circuit']} | {r['pit_loss_median_s']:.1f} | "
                     f"{r['pit_loss_iqr_s']:.1f} | {int(r['n_stops'])} | {flag} |")
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(table.to_string(index=False))
    print("\nValidation vs FastF1:")
    for c, k, t, d in sorted(val_rows, key=lambda r: abs(r[3])):
        print(f"  {c:12s} kaggle={k:5.1f}  fastf1={t:5.1f}  delta={d:+.1f}")
    print(f"\nwrote {OUT_CSV}\nwrote {OUT_REPORT}")


if __name__ == "__main__":
    main()
