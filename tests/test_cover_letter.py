"""The submission letter quotes results, so its numbers are claims too.

A cover letter is prose typed by hand, which is exactly the form every drift in
this project has taken. It is not generated from the artifacts the way the
manuscript is, because an editor reads it as a letter and it would be an odd
thing to template. So instead every figure in it is checked against the macros
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
LETTER = REPO / "paper" / "cover_letter.md"
NUMBERS = REPO / "paper" / "numbers.tex"

#: Submission dates, the issue year, and the enumerated list markers. None of
#: these is a measurement.
CONTEXT = {
    "16", "2026", "7", "1", "2", "3", "4",
}


def _macros() -> dict[str, str]:
    text = NUMBERS.read_text(encoding="utf-8")
    return dict(re.findall(r"\\newcommand\{\\(\w+)\}\{([^}]*)\}", text))


@pytest.fixture(scope="module")
def letter() -> str:
    if not LETTER.exists():
        pytest.skip("paper/cover_letter.md not present")
    return LETTER.read_text(encoding="utf-8")


def test_every_figure_in_the_letter_comes_from_the_artifacts(letter: str) -> None:
    values = set()
    for value in _macros().values():
        values.add(value)
        values.add(value.lstrip("+"))
        values.add(value.replace(",", ""))
        # A letter writes a percentage as "80%" where the macro holds "80".
        values.add(value.rstrip("%"))

    # URLs and the DOI carry digits that are identifiers, not results.
    body = re.sub(r"<[^>]*>", "", letter)
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
        f"the cover letter states figures the artifacts do not produce: "
        f"{sorted(set(offenders))}. Every number an editor reads has to be one "
        "the repository can regenerate, including in a letter."
    )


def test_the_letter_declares_the_ai_tool_use(letter: str) -> None:
    """Declared rather than waited for, since the journal publishes no policy."""
    assert "Disclosure of AI tool use" in letter
    assert "under my direction" in letter, (
        "the disclosure should say who directed the work"
    )
    assert "I am responsible" in letter, (
        "the disclosure should place responsibility, which is the part that "
        "matters to an editor"
    )


def test_the_letter_states_eligibility_and_the_usual_declarations(letter: str) -> None:
    for required in ("high school", "not under review elsewhere",
                     "conflicts of interest"):
        assert required in letter, f"the letter does not state: {required}"
