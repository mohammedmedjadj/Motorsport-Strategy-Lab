"""The submission packet quotes results, so its numbers are claims too.

The packet is prose typed by hand, which is exactly the form every drift in
this project has taken. It is not generated from the artifacts the way the
manuscript is: it is pasted into a web form field by field, which no
generator can do. So instead every figure in it is checked against the macros
the manuscript generates, which is the same discipline arriving by a different
route: a number may appear in the letter only if the committed artifacts
produce it.

Dates, the issue year and the ordinal list markers are not results and are
exempt by name.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
LETTER = REPO / "paper" / "submission.md"
NUMBERS = REPO / "paper" / "numbers.tex"

#: Submission dates, the issue year, and the enumerated list markers. None of
#: these is a measurement.
CONTEXT = {
    "16", "2026", "7", "1", "2", "3", "4",
    # The journal's ISSN, which is an identifier rather than a measurement.
    "3070", "4065",
}


def _macros() -> dict[str, str]:
    text = NUMBERS.read_text(encoding="utf-8")
    return dict(re.findall(r"\\newcommand\{\\(\w+)\}\{([^}]*)\}", text))


@pytest.fixture(scope="module")
def packet() -> str:
    if not LETTER.exists():
        pytest.skip("paper/submission.md not present")
    return LETTER.read_text(encoding="utf-8")


def test_every_figure_in_the_packet_comes_from_the_artifacts(packet: str) -> None:
    values = set()
    for value in _macros().values():
        values.add(value)
        values.add(value.lstrip("+"))
        values.add(value.replace(",", ""))
        # A letter writes a percentage as "80%" where the macro holds "80".
        values.add(value.rstrip("%"))

    # URLs and the DOI carry digits that are identifiers, not results.
    body = re.sub(r"<[^>]*>", "", packet)
    body = re.sub(r"https?://\S+", "", body)
    body = re.sub(r"\bR\u00b2\b", "", body)

    offenders = []
    for number in re.findall(r"\u2212?\d[\d,.]*", body):
        cleaned = number.rstrip(".,").replace("\u2212", "-")
        if cleaned in CONTEXT or cleaned.lstrip("-") in CONTEXT:
            continue
        if cleaned in values or cleaned.lstrip("-") in values:
            continue
        offenders.append(cleaned)

    assert not offenders, (
        f"the submission packet states figures the artifacts do not produce: "
        f"{sorted(set(offenders))}. Every number an editor reads has to be one "
        "the repository can regenerate, including in a form field."
    )


def test_the_packet_states_eligibility_and_the_usual_declarations(packet: str) -> None:
    for required in ("high school", "not under review elsewhere",
                     "conflicts of interest"):
        assert required in packet, f"the packet does not state: {required}"
