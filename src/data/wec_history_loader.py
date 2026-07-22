"""Loader for the results-level WEC history (Kaggle ``wec_data.csv``).

This is **results** data — one row per car per race, 2011-2023, every class and
every round — not lap-by-lap. It therefore cannot feed the degradation or
neutralisation models (which need per-lap times / flags). What it *does* unlock,
uniquely, is a long-baseline **reliability / attrition** signal: whether a car
was classified at the finish, across 13 seasons and every class. See
``src/reliability/wec_reliability.py``.

Same discipline as every other loader here: **validate the schema and surface
the messy fields, never impute.** The raw file has two dirty columns handled
explicitly below (mixed ``season`` labels, five distinct ``status`` values).
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from src.ingestion.config import REPO_ROOT

#: Where the user drops the Kaggle export. Kept out of the derived tree because
#: it is an external raw source, not something this repo generates.
WEC_HISTORY_CSV = REPO_ROOT / "data" / "external" / "wec" / "wec_data.csv"

#: The exact header of the Kaggle file, asserted on load so a schema change is
#: caught loudly rather than silently mis-parsed.
EXPECTED_COLUMNS: tuple[str, ...] = (
    "car", "overall_position", "class_position", "team", "vehicle", "class",
    "group", "race", "event_duration", "season", "laps", "total_time",
    "gap_first", "gap_car_ahead", "tyres", "status", "fl_lap_number",
    "fl_time", "fl_kph_average", "driver_1", "driver_2", "driver_3",
)

#: A car counts as having reached the finish only if officially *Classified*.
#: "Not classified" (ran but under the distance minimum), "Retired", "Excluded"
#: and "Not started" are all non-finishes for an attrition model.
_FINISH_STATUS = "Classified"


def _normalise_class(name: str) -> str:
    """Collapse the 2011-2013 spaced class names onto the later convention, so
    the same class is not split in two: ``LM P1`` -> ``LMP1``,
    ``LM GTE Pro`` -> ``LMGTE Pro``. Genuinely distinct experimental categories
    (CDNT, INNOVATIVE CAR) are left untouched."""
    s = str(name).strip()
    s = re.sub(r"^LM GTE\b", "LMGTE", s)
    s = re.sub(r"^LM P(\d)", r"LMP\1", s)
    return s


def _season_end_year(label: str) -> int:
    """Normalise the mixed ``season`` column to a single integer.

    The file carries both plain years (``2014``) and WEC "super-season" labels
    that straddle a winter (``2018-2019``, ``2019-2020``). We key on the season's
    *ending* year, so a super-season sorts and groups with the calendar year it
    concludes in — the convention WEC itself uses for its championship.
    """
    text = str(label).strip()
    return int(text.split("-")[-1]) if "-" in text else int(text)


def load_wec_history(path: Path | None = None) -> pd.DataFrame:
    """Load, validate and lightly normalise the results-level WEC history.

    Adds three derived columns without touching the raw ones:
    ``season_end`` (int), ``classified`` (bool), ``duration_h`` (numeric hours).
    Raises if the file is missing or its schema drifted.
    """
    csv = path or WEC_HISTORY_CSV
    if not csv.exists():
        raise FileNotFoundError(
            f"WEC history CSV not found at {csv}. Drop the Kaggle 'wec_data.csv' "
            f"there (see src/data/wec_history_loader.py)."
        )
    raw = pd.read_csv(csv)
    missing = [c for c in EXPECTED_COLUMNS if c not in raw.columns]
    if missing:
        raise ValueError(f"WEC history CSV is missing expected columns: {missing}")

    df = raw.copy()
    df["class"] = df["class"].map(_normalise_class)
    df["season_end"] = df["season"].map(_season_end_year)
    df["classified"] = df["status"].astype(str).str.strip().eq(_FINISH_STATUS)
    df["duration_h"] = pd.to_numeric(df["event_duration"], errors="coerce")
    return df
