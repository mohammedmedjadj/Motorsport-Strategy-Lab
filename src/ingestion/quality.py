"""Data quality accounting for cleaned lap data.

Produces the Phase 1 deliverable: for every race, how many laps were
excluded from pace analysis and why. Exclusion reasons are NOT mutually
exclusive (an in-lap can also be inaccurate), so per-reason counts do not
sum to the excluded total; the report states this explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.ingestion.cleaning import EXCLUSION_FLAGS


@dataclass(frozen=True)
class QualityRow:
    """Per-race lap accounting."""

    label: str
    total_laps: int
    pace_laps: int
    reason_counts: dict[str, int]
    red_flag_stint_laps: int

    @property
    def pace_pct(self) -> float:
        """Share of laps kept for pace analysis, in percent."""
        return 100.0 * self.pace_laps / self.total_laps if self.total_laps else 0.0


def summarise_race(label: str, cleaned: pd.DataFrame) -> QualityRow:
    """Compute the quality accounting for one cleaned race DataFrame."""
    return QualityRow(
        label=label,
        total_laps=len(cleaned),
        pace_laps=int(cleaned["is_pace_lap"].sum()),
        reason_counts={f: int(cleaned[f].sum()) for f in EXCLUSION_FLAGS},
        red_flag_stint_laps=int(cleaned["stint_crosses_red_flag"].sum()),
    )


def to_markdown(rows: list[QualityRow]) -> str:
    """Render the full data quality report as markdown."""
    short = {f: f.removeprefix("is_") for f in EXCLUSION_FLAGS}
    header = (
        "| Race | Total | Pace laps | % kept | "
        + " | ".join(short[f] for f in EXCLUSION_FLAGS)
        + " | red-flag stint laps |"
    )
    sep = "|" + "---|" * (4 + len(EXCLUSION_FLAGS) + 1)
    lines = [
        "# Phase 1 — Data quality report",
        "",
        "Lap-level accounting after cleaning (`src/ingestion/`). A lap is kept",
        "for pace analysis (`is_pace_lap`) only if **no** exclusion flag is set.",
        "Exclusion reasons overlap (e.g. an in-lap may also be flagged",
        "inaccurate), so per-reason counts exceed the number of excluded laps.",
        "`red-flag stint laps` is informational, not an exclusion: laps whose",
        "stint contains a red flag (tyre sets may change without a pit stop).",
        "",
        header,
        sep,
    ]
    for r in rows:
        reason_cells = " | ".join(str(r.reason_counts[f]) for f in EXCLUSION_FLAGS)
        lines.append(
            f"| {r.label} | {r.total_laps} | {r.pace_laps} | {r.pace_pct:.1f}% "
            f"| {reason_cells} | {r.red_flag_stint_laps} |"
        )
    total = sum(r.total_laps for r in rows)
    pace = sum(r.pace_laps for r in rows)
    lines += [
        "",
        f"**Overall: {pace}/{total} laps kept for pace analysis "
        f"({100.0 * pace / total:.1f}%).**" if total else "**No laps.**",
        "",
    ]
    return "\n".join(lines)
