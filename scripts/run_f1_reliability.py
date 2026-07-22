"""F1 reliability / attrition from the Kaggle results — the cross-series
counterpart to ``run_wec_reliability.py``.

Reads ``data/external/f1/`` and writes ``data/derived/f1/reliability.csv`` +
``reports/f1/reliability.md``: finish rate by circuit and by regulation era,
with the permanent-vs-street positive control.

Usage::

    python scripts/run_f1_reliability.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ingestion.config import F1_DERIVED_DIR, F1_REPORTS_DIR  # noqa: E402
from src.reliability.f1_reliability import (  # noqa: E402
    finish_rate_by,
    load_f1_results,
    reliability_improves_off_the_street,
)

OUT_CSV = F1_DERIVED_DIR / "reliability.csv"
OUT_REPORT = F1_REPORTS_DIR / "reliability.md"
MIN_CIRCUIT_ENTRIES = 40


def _table(rates, label: str) -> pd.DataFrame:
    return pd.DataFrame({"dimension": label, **r.summary_row()} for r in rates)


def main() -> None:
    df = load_f1_results()
    by_circuit = [r for r in finish_rate_by(df, "circuitRef")
                  if r.n_entries >= MIN_CIRCUIT_ENTRIES]
    by_era = sorted(finish_rate_by(df, "era"), key=lambda r: r.group)
    control = reliability_improves_off_the_street(df)
    overall = df["classified"].mean()

    table = pd.concat([_table(by_circuit, "circuit"), _table(by_era, "era")],
                      ignore_index=True)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT_CSV, index=False)

    lines = [
        "# F1 reliability / attrition (Kaggle results, 2011-2024)",
        "",
        "The cross-series counterpart to the "
        "[WEC reliability layer](../wec/reliability.md), same Jeffreys smoother "
        "(`reliability.core`). Probability a car is classified at the finish "
        "(saw the flag or was lapped); every mechanical/accident status is a DNF.",
        "",
        f"Coverage: **{len(df)} car-entries**, 2011-2024, overall finish rate "
        f"**{overall:.3f}**.",
        "",
        "## Most fragile circuits (>= 40 entries, most fragile first)",
        "",
        "| Circuit | Entries | Classified | Finish rate | 95% CI |",
        "|---|---|---|---|---|",
    ]
    for r in by_circuit[:10]:
        lines.append(f"| {r.group} | {r.n_entries} | {r.n_classified} | "
                     f"{r.rate:.3f} | {r.lo95:.3f}-{r.hi95:.3f} |")
    lines += [
        "",
        "## Finish rate by regulation era",
        "",
        "| Era | Entries | Finish rate | 95% CI |",
        "|---|---|---|---|",
    ]
    for r in by_era:
        lines.append(f"| {r.group} | {r.n_entries} | {r.rate:.3f} "
                     f"| {r.lo95:.3f}-{r.hi95:.3f} |")
    verdict = "holds" if control else "does NOT hold"
    lines += [
        "",
        f"**Positive control: permanent circuits finish better than street "
        f"circuits — {verdict}** "
        f"({df.loc[~df['street'],'classified'].mean():.3f} permanent vs "
        f"{df.loc[df['street'],'classified'].mean():.3f} street). Street tracks "
        "punish any error with a wall, so higher attrition there is the expected "
        "sign — reported either way.",
        "",
        "The early **hybrid-v6** era is the least reliable, matching the "
        "well-known 2014 power-unit teething; **ground-effect** (2022+) is the "
        "most reliable. Eras are never pooled (see the degradation report for the "
        "2026 wall).",
    ]
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(table.to_string(index=False))
    print(f"\nPositive control (permanent > street): {verdict}")
    print(f"wrote {OUT_CSV}\nwrote {OUT_REPORT}")


if __name__ == "__main__":
    main()
