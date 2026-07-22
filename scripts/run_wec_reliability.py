"""WEC reliability / attrition from the results-level Kaggle history.

Reads ``data/external/wec/wec_data.csv`` (drop the Kaggle export there), computes
finish-rate by class and by race duration with Jeffreys credible intervals, and
writes the derived table + a report. Offline apart from the one raw file.

Usage::

    python scripts/run_wec_reliability.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.wec_history_loader import load_wec_history  # noqa: E402
from src.ingestion.config import DERIVED_DIR, REPORTS_DIR  # noqa: E402
from src.reliability.wec_reliability import (  # noqa: E402
    attrition_holds_with_duration,
    finish_rate_by,
    finish_rate_by_duration,
)

OUT_CSV = DERIVED_DIR / "wec" / "reliability.csv"
OUT_REPORT = REPORTS_DIR / "wec" / "reliability.md"


def _table(rates, label: str) -> pd.DataFrame:
    rows = [{"dimension": label, **r.summary_row()} for r in rates]
    return pd.DataFrame(rows)


def main() -> None:
    df = load_wec_history()
    seasons = sorted(df["season_end"].unique())
    by_class = finish_rate_by(df, "class")
    by_duration = finish_rate_by_duration(df)
    control = attrition_holds_with_duration(df)

    table = pd.concat(
        [_table(by_class, "class"), _table(by_duration, "duration")],
        ignore_index=True,
    )
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT_CSV, index=False)

    lines = [
        "# WEC reliability / attrition (results-level, 2011-2023)",
        "",
        "From the Kaggle results history (one row per car per race, every class "
        "and round). Not lap-level, so this is the one primitive results data "
        "supports better than telemetry: **the probability a car reaches the "
        "classified finish**, over a 13-season baseline.",
        "",
        f"Coverage: **{len(df)} car-entries**, seasons "
        f"{seasons[0]}-{seasons[-1]}. Finish = official *Classified* status; "
        "*Not classified / Retired / Excluded / Not started* all count as "
        "non-finishes. Rates use the same Jeffreys `Beta(0.5,0.5)` smoother as "
        "the calibration backtest — small classes get a wide interval, never a "
        "false 0/100%.",
        "",
        "## Finish rate by class (most fragile first)",
        "",
        "| Class | Entries | Classified | Finish rate | 95% CI |",
        "|---|---|---|---|---|",
    ]
    for r in by_class:
        lines.append(
            f"| {r.group} | {r.n_entries} | {r.n_classified} | "
            f"{r.rate:.3f} | {r.lo95:.3f}-{r.hi95:.3f} |"
        )
    lines += [
        "",
        "## Finish rate by race duration (the positive control)",
        "",
        "The falsifiable prediction: attrition rises with race length, so a 24 h "
        "finish rate should sit **below** a 6 h one. If it did not, the model "
        "would be wrong — reported either way.",
        "",
        "| Duration | Entries | Classified | Finish rate | 95% CI |",
        "|---|---|---|---|---|",
    ]
    for r in by_duration:
        lines.append(
            f"| {r.group} | {r.n_entries} | {r.n_classified} | "
            f"{r.rate:.3f} | {r.lo95:.3f}-{r.hi95:.3f} |"
        )
    verdict = ("holds" if control else "does NOT hold")
    lines += [
        "",
        f"**Positive control: attrition-rises-with-duration {verdict}** "
        f"(longest-race finish rate {'<' if control else '>='} shortest-race).",
        "",
        "## What this does and does not add",
        "",
        "- Adds a measured attrition prior absent from every lap-level model here.",
        "- Does **not** feed degradation or neutralisation models (no per-lap "
        "data); it is a separate, complementary layer.",
        "- Results-level only: it cannot say *when* in a race a car failed, only "
        "whether it was classified.",
    ]
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(table.to_string(index=False))
    print(f"\nPositive control (attrition rises with duration): {verdict}")
    print(f"wrote {OUT_CSV}\nwrote {OUT_REPORT}")


if __name__ == "__main__":
    main()
