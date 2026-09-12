"""What a LaTeX compiler would reject, checked without a LaTeX compiler.

No TeX distribution is installed on the machine this project is developed on,
so `paper/main.tex` has never been run through pdfLaTeX here. Overleaf is the
first thing that will compile it, and by then the author is reading an error
log instead of a paper.

These tests do not prove the document compiles. They cover the failure modes
that are both common and mechanical: an environment opened and not closed, a
`\\ref` to a label that does not exist, a label nothing points at, and
unbalanced inline maths. Everything subtler than that still needs a real
compile, and `paper/README.md` says so.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import pytest

MAIN = Path(__file__).resolve().parents[1] / "paper" / "main.tex"


def _source() -> str:
    if not MAIN.exists():
        pytest.skip("paper/main.tex not present")
    text = MAIN.read_text(encoding="utf-8")
    # Whole-line comments only. A trailing `%` can be an escaped percent sign,
    # and stripping those would corrupt every "80\%" in the manuscript.
    return re.sub(r"(?m)^\s*%.*$", "", text)


def test_every_environment_is_closed() -> None:
    text = _source()
    opened = Counter(re.findall(r"\\begin\{(\w+\*?)\}", text))
    closed = Counter(re.findall(r"\\end\{(\w+\*?)\}", text))
    unbalanced = {
        name: (opened[name], closed[name])
        for name in set(opened) | set(closed)
        if opened[name] != closed[name]
    }
    assert not unbalanced, (
        "environments opened and closed a different number of times "
        f"(name: begin, end): {unbalanced}"
    )


def test_every_reference_points_at_a_label_that_exists() -> None:
    text = _source()
    labels = set(re.findall(r"\\label\{([^}]+)\}", text))
    referenced = set(re.findall(r"\\(?:page)?ref\{([^}]+)\}", text))
    dangling = sorted(referenced - labels)
    assert not dangling, (
        "the paper references labels that are never defined, which compiles to "
        f"a bold '??' in the PDF: {dangling}"
    )


def test_no_label_is_defined_and_never_used() -> None:
    text = _source()
    labels = set(re.findall(r"\\label\{([^}]+)\}", text))
    referenced = set(re.findall(r"\\(?:page)?ref\{([^}]+)\}", text))
    orphans = sorted(labels - referenced)
    assert not orphans, (
        "labels nothing points at. Either the cross-reference was meant to be "
        f"written and was not, or the label is dead weight: {orphans}"
    )


def test_no_label_is_defined_twice() -> None:
    text = _source()
    counts = Counter(re.findall(r"\\label\{([^}]+)\}", text))
    duplicated = sorted(name for name, count in counts.items() if count > 1)
    assert not duplicated, (
        "a duplicated label makes every reference to it resolve to whichever "
        f"came last, silently: {duplicated}"
    )


def test_inline_maths_delimiters_are_balanced() -> None:
    text = _source()
    # Escaped dollars are currency, not maths. Nothing else in this manuscript
    # uses `$` at all.
    dollars = len(re.findall(r"(?<!\\)\$", text))
    assert dollars % 2 == 0, (
        f"{dollars} unescaped '$' delimiters, which is odd -- inline maths is "
        "opened somewhere and never closed"
    )


def test_every_included_graphic_resolves_from_the_paper_directory() -> None:
    text = _source()
    included = re.findall(r"\\includegraphics\[[^\]]*\]\{([^}]+)\}", text)
    assert included, "the paper includes no figures, which is not expected"
    missing = [
        path for path in included
        if not (MAIN.parent / path).resolve().exists()
    ]
    assert not missing, (
        "figures the paper includes do not exist at the path it gives, "
        f"relative to paper/: {missing}"
    )
