"""The endurance source ships a `raining` flag. Measure it before trusting it.

The plan's audit asked whether the endurance source had ever been confronted
with anything independent. This is one answer, and it is available offline: the
source carries a per-lap `raining` boolean, so its base rate can be checked
against what endurance racing is actually like.

Measured across all 210 committed lap files — 523,213 laps:

| series | True | False | not populated |
|---|---|---|---|
| WEC | 570 | 82,242 | 1,867 |
| IMSA | **0** | 192,682 | 193,380 |
| ELMS | **0** | 19,522 | 32,950 |

IMSA has run 63 scoped races across five seasons — five Daytona 24 Hours, five
Sebring 12 Hours, Watkins Glen and Road America in high summer — and the flag
reports rain on **not one lap**. ELMS the same over 29 races. That is not a
claim about the weather; it is a field that is populated and uninformative,
which is a different failure from a field that is missing and looks it.

`reports/imsa/data_availability_phase0.md` already records that some IMSA races
carry no weather columns at all. This is the sharper statement: **where IMSA
does populate the column, it is always False.** Missing data announces itself as
NaN and gets handled; a column of `False` looks like a measurement.

Nothing in the project fits on this flag today — the F1 wet exclusion uses the
Open-Meteo layer, not this — so no published result depends on it. These guards
exist so that stays true by decision rather than by luck, and so the number is
on record for the paper's threats-to-validity rather than rediscovered later.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
DERIVED = REPO / "data" / "derived"
ENDURANCE_SERIES = ("imsa", "wec", "elms")

#: Series whose flag has never once reported rain, and so cannot be used to
#: exclude wet running. Measured, not assumed — `test_the_measurement_still_
#: holds` recomputes it.
UNINFORMATIVE = frozenset({"imsa", "elms"})


def _lap_files() -> list[Path]:
    return [
        path
        for series in ENDURANCE_SERIES
        for path in sorted((DERIVED / series).glob("laps_*.csv"))
    ]


def _rain_counts() -> dict[str, dict[str, int]]:
    """True / False / unpopulated laps per series, from the committed files."""
    counts: dict[str, dict[str, int]] = {
        series: {"true": 0, "false": 0, "missing": 0} for series in ENDURANCE_SERIES
    }
    for path in _lap_files():
        column = pd.read_csv(path, usecols=["raining"], low_memory=False)["raining"]
        text = column.astype(str).str.lower()
        bucket = counts[path.parent.name]
        bucket["true"] += int((text == "true").sum())
        bucket["false"] += int((text == "false").sum())
        bucket["missing"] += int(column.isna().sum())
    return counts


@pytest.fixture(scope="module")
def rain_counts() -> dict[str, dict[str, int]]:
    if not _lap_files():
        pytest.skip("no endurance lap files committed")
    return _rain_counts()


def test_the_measurement_still_holds(rain_counts) -> None:
    """Recompute the table in this file's docstring rather than trust it.

    If a series starts reporting rain, that is good news and this test says so
    — but it must be noticed, because the moment the flag becomes informative
    is the moment it becomes worth using, and UNINFORMATIVE stops being true.
    """
    became_useful = sorted(
        series for series in UNINFORMATIVE if rain_counts[series]["true"] > 0
    )
    assert not became_useful, (
        f"{became_useful} now report rain on some laps, where they previously "
        "reported none. That is an improvement in the source, not a failure: "
        "update UNINFORMATIVE and this file's docstring, and reconsider "
        "whether wet-lap exclusion is now possible for those series."
    )

    for series in ENDURANCE_SERIES:
        counts = rain_counts[series]
        assert sum(counts.values()) > 0, f"{series}: no laps read at all"


def test_no_fit_silently_excludes_laps_on_an_uninformative_flag() -> None:
    """Filtering on `raining` would exclude nothing in IMSA and ELMS.

    Worse than useless: it would look like wet running had been handled, in the
    two series where it demonstrably has not been. WEC is a different case —
    570 flagged laps is thin but real — so this watches for the filter, not for
    any mention of the column. The loader is allowed to carry it.
    """
    offenders = []
    for path in sorted((REPO / "src").rglob("*.py")) + sorted((REPO / "scripts").glob("*.py")):
        text = path.read_text(encoding="utf-8", errors="replace")
        # A filter reads like `~df["raining"]`, `df.raining == False`, or
        # `query("not raining")`. Carrying the column through a loader does
        # not, which is why the column list in base_loader.py is not a hit.
        if re.search(r"""(~\s*\w+\[["']raining["']\]|
                          \[["']raining["']\]\s*(==|!=)|
                          query\([^)]*raining|
                          \.raining\s*(==|!=))""",
                     text, re.VERBOSE):
            offenders.append(str(path.relative_to(REPO)))
    assert not offenders, (
        f"these files filter laps on the `raining` flag: {offenders}. The flag "
        "reports rain on zero laps in IMSA and ELMS, so the filter removes "
        "nothing there while making it look as though wet running was "
        "excluded. Use the Open-Meteo layer, or state the limitation."
    )


def test_the_limitation_is_written_down_where_a_reader_would_look(rain_counts) -> None:
    """A measured limitation nobody can find is not documented.

    IMSA's availability report already covers weather coverage; this checks it
    has not lost the part that matters, since the column being *present* is
    what makes the gap easy to miss.
    """
    report = REPO / "reports" / "imsa" / "data_availability_phase0.md"
    if not report.exists():
        pytest.skip("IMSA availability report not present")
    text = report.read_text(encoding="utf-8")
    assert "raining" in text, (
        "the IMSA data-availability report no longer mentions the `raining` "
        f"column, which is populated on {rain_counts['imsa']['false']:,} laps "
        "and True on none of them. A reader will take a column of False for a "
        "measurement."
    )
