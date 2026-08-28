"""The safety-car layer reaches back to 2018, and event names change.

A Grand Prix can be renamed without moving. Mexico ran as the "Mexican Grand
Prix" through 2020 and as the "Mexico City Grand Prix" from 2021; Brazil as the
"Brazilian Grand Prix" through 2020 and as "São Paulo" from 2021. The frozen
calendar starts in 2022, so every earlier season inherits the *current* name —
and four real editions were requested under a name that did not exist yet,
skipped with "edition most likely not held that season", and lost.

They were lost in a report that lists every skip, under a heading that says
these are COVID cancellations. Nothing was hidden and nobody was going to read
thirty-one lines to notice that two of them were a different kind of miss.

This is the same defect as mapping the 2026 Spanish Grand Prix onto Barcelona,
running backwards in time instead of forwards, and it is the second time it has
appeared. The guards below are per-case rather than general because the general
version needs the network: only FastF1's own schedule knows whether a race
happened at a track under some other name.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
REPORT = REPO / "reports" / "f1" / "safety_car_phase3.md"

#: Editions that exist and must never appear in the skip list again. Each was
#: skipped because the request used a name the season did not use.
RECOVERED = [
    ("2018", "mexico_city"),
    ("2019", "mexico_city"),
    ("2018", "interlagos"),
    ("2019", "interlagos"),
]


def _skipped() -> list[str]:
    """The editions the safety-car run could not load, from its own report."""
    if not REPORT.exists():
        pytest.skip("safety-car report not generated")
    text = REPORT.read_text(encoding="utf-8")
    if "## Editions not included" not in text:
        return []
    section = text.split("## Editions not included", 1)[1]
    section = section.split("\n## ", 1)[0]
    return [line[2:] for line in section.splitlines() if line.startswith("- ")]


@pytest.mark.parametrize(("season", "circuit"), RECOVERED,
                         ids=lambda value: str(value))
def test_renamed_editions_are_not_skipped(season: str, circuit: str) -> None:
    """A race that happened must not be recorded as one that did not."""
    slug = f"{season}_{circuit}"
    offending = [
        line for line in _skipped()
        if line.startswith(f"{slug}:")
        # Only a *naming* failure counts. FastF1 fuzzy-matching the request to
        # some other event means the name was wrong for that season; a
        # DataNotLoadedError or a timeout means the name resolved and the fetch
        # failed, which is transient and a different problem entirely. Folding
        # the two together would make this guard fire on a bad network day and
        # get muted.
        and ("fuzzy-matched" in line or "LookupError" in line)
    ]
    assert not offending, (
        f"{slug} is in the skip list as a naming failure: {offending}. That "
        "edition was run, under a different event name that season. Add the "
        "historical name to RENAMED_FROM in scripts/run_safety_car.py rather "
        "than accepting the skip."
    )


def test_every_skip_states_a_reason() -> None:
    """A bare slug in the skip list is a gap nobody can evaluate."""
    bare = [line for line in _skipped() if ":" not in line]
    assert not bare, f"skipped editions with no stated reason: {bare}"


def test_the_skip_list_is_mostly_cancellations_not_naming() -> None:
    """Most skips should be races that genuinely did not happen.

    A fuzzy match to a *different* event is ambiguous on its own: it means
    either the race did not exist (Jeddah in 2018) or it existed under another
    name (Mexico in 2018). This does not try to tell those apart — it watches
    the *count*. The 2020 and 2021 seasons lost rounds to COVID, so a large
    skip list is expected; a skip list that grows much beyond that is the
    signature of a naming problem, and is worth a human reading it.
    """
    skipped = _skipped()
    if not skipped:
        return
    seasons = [int(match.group(1))
               for line in skipped
               if (match := re.match(r"(\d{4})_", line))]
    covid = sum(1 for season in seasons if season in (2020, 2021))
    assert covid >= len(seasons) * 0.4, (
        f"only {covid} of {len(seasons)} skipped editions are from the "
        "COVID-affected 2020-2021 seasons. The rest are circuits absent from a "
        "calendar or names that changed — read the list rather than trusting "
        "the heading."
    )
