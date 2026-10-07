"""The target journal's hard requirements, checked without a TeX distribution.

The Wharton Sports Analytics Journal publishes a short list of submission
requirements. Most are structural and can be checked from the source. One is a
hard numeric limit the manuscript currently sits one word under, which is the
kind of margin that disappears the first time a generated count gains a digit:
a figure going from 9 to 10 is two characters and one more word.

These are the journal's rules rather than this project's preferences, so the
message on each failure names the rule rather than arguing for it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MAIN = REPO / "paper" / "main.tex"

#: "Less than 250 words in length."
ABSTRACT_LIMIT = 250


@pytest.fixture(scope="module")
def source() -> str:
    if not MAIN.exists():
        pytest.skip("paper/main.tex not present")
    return MAIN.read_text(encoding="utf-8")


def _abstract_words(source: str) -> int:
    """Word count as a copy editor reads it, with each macro as one word.

    A macro stands for the figure it expands to, and every one of them expands
    to something a reader counts as a single word: a number, a percentage, an
    interval. Counting them as zero would understate the abstract against a
    limit it nearly touches.
    """
    body = source[source.index(r"\begin{abstract}"):source.index(r"\end{abstract}")]
    body = re.sub(r"\\[A-Za-z]+\{\}", "X", body)
    body = re.sub(r"\\[A-Za-z]+", "", body)
    body = re.sub(r"[{}$\\%~]", " ", body)
    return len([w for w in body.split() if w.strip("-,.;:()[]")])


def test_the_abstract_is_under_the_limit(source: str) -> None:
    count = _abstract_words(source)
    assert count < ABSTRACT_LIMIT, (
        f"the abstract is {count} words against the journal's limit of "
        f"{ABSTRACT_LIMIT}. A generated figure gaining a digit is enough to do "
        "this, so cut a clause rather than hoping the next refresh is kind."
    )


def test_there_are_no_footnotes(source: str) -> None:
    """"Footnotes are not permitted." A \\thanks renders as one."""
    for command in (r"\footnote", r"\thanks"):
        assert command not in source, (
            f"{command} renders as a footnote, which the journal does not "
            "permit. The repository and DOI links live in the Data and code "
            "availability section for this reason."
        )


def test_the_body_is_double_spaced_with_line_numbers(source: str) -> None:
    """"Double-spaced", and "continuous line numbers" plus page numbers."""
    assert r"\usepackage{setspace}" in source and r"\doublespacing" in source, (
        "the journal asks for double-spaced manuscript text"
    )
    assert r"\usepackage{lineno}" in source and r"\linenumbers" in source, (
        "the journal asks for continuous line numbers in the manuscript file"
    )
    # Page numbers come from the article class; losing them takes an explicit
    # \pagestyle{empty}, so that is what is checked.
    assert r"\pagestyle{empty}" not in source, (
        "page numbers have been switched off, and the journal asks for them"
    )


def test_the_manuscript_is_a_single_column(source: str) -> None:
    assert "twocolumn" not in source, (
        "the journal does not accept multiple-column formatting"
    )


def test_the_references_are_in_apa_shape(source: str) -> None:
    """"Reference style: APA format." Checked on the shape, not the grammar.

    A full APA validator is out of scope. What this catches is a reversion to
    the previous style, where entries opened with given names and carried
    \\newblock separators and bare \\doi commands.
    """
    bib = source[source.index(r"\begin{thebibliography}"):]
    entries = re.findall(r"\\bibitem\[[^\]]*\]\{\w+\}\n(.+?)(?=\n\n|\\end\{thebib)",
                         bib, re.S)
    assert len(entries) >= 15, f"only {len(entries)} entries parsed"
    for entry in entries:
        head = entry.strip().split("\n")[0]
        assert "\\newblock" not in entry, (
            f"an entry still uses \\newblock, which is the pre-APA layout: {head[:60]}"
        )
        # Surnames here contain spaces and particles: "Carrasco Heine",
        # "van Kampen", "de Vries", "van den Eshof".
        assert re.match(r"^[A-Za-z\\\"'{}.~ -]+,", head), (
            f"an entry does not open with a surname and comma: {head[:60]}"
        )
        assert re.search(r"\(\d{4}\)\.", entry), (
            f"an entry has no (Year). element: {head[:60]}"
        )
