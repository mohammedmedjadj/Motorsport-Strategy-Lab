"""The manuscript quotes no number it did not derive, and none that is missing.

`paper/main.tex` deliberately contains no digits. Every quantity is a macro
expanded from `paper/numbers.tex`, which `scripts/make_paper_numbers.py`
generates from the committed artifacts. That makes the paper the one document in
this project that structurally cannot drift — regenerate the artifacts,
regenerate the macros, and the manuscript is either correct or CI fails.

It also creates one new failure mode, and it is a bad one: a macro used in the
manuscript but never defined does not produce a wrong number, it produces a
LaTeX error, and if the author is not the one compiling it that error surfaces
at the worst possible moment. These guards run without LaTeX installed.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PAPER = REPO / "paper"
MAIN = PAPER / "main.tex"
NUMBERS = PAPER / "numbers.tex"

#: Commands from the document class and loaded packages. The manuscript uses
#: these legitimately and they are not expected in numbers.tex.
LATEX_BUILTINS = frozenset("""
documentclass usepackage input title large author thanks url date begin end
maketitle abstract section subsection paragraph textbf textit emph texttt
includegraphics caption label ref cite citet citep centering toprule midrule
bottomrule bibliographystyle bibitem newblock doi today item newcommand
graphicspath hidelinks textwidth
""".split())


def _defined() -> set[str]:
    if not NUMBERS.exists():
        pytest.skip("paper/numbers.tex not generated")
    return set(re.findall(r"\\newcommand\{\\(\w+)\}", NUMBERS.read_text(encoding="utf-8")))


def _used() -> set[str]:
    if not MAIN.exists():
        pytest.skip("paper/main.tex not present")
    text = MAIN.read_text(encoding="utf-8")
    text = re.sub(r"(?m)^\s*%.*$", "", text)  # strip whole-line comments
    return set(re.findall(r"\\(\w+)", text)) - LATEX_BUILTINS


def test_every_macro_the_paper_uses_is_defined() -> None:
    """An undefined macro is a compile error, not a wrong number."""
    generated = _defined()
    # Only macros that look like ours: our generator emits CamelCase names, and
    # LaTeX's own commands are overwhelmingly lowercase.
    ours = {name for name in _used() if name[:1].isupper()}
    missing = sorted(ours - generated)
    assert not missing, (
        f"main.tex uses these macros but numbers.tex defines none of them: "
        f"{missing}. Either add them to scripts/make_paper_numbers.py or stop "
        "quoting the quantity — a number typed directly into the manuscript is "
        "the exact failure this arrangement exists to prevent."
    )


def test_the_paper_contains_no_bare_numbers_in_its_claims() -> None:
    """A digit in the prose is a number that will not recompute.

    Deliberately narrow: years, package options, font sizes and the
    bibliography carry digits legitimately. What this catches is a decimal or a
    multi-digit count sitting in a sentence, which is where every drift in this
    project has lived.
    """
    if not MAIN.exists():
        pytest.skip("paper/main.tex not present")
    offenders = []
    inside_bibliography = False
    for number, line in enumerate(MAIN.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith(r"\begin{thebibliography}"):
            inside_bibliography = True
        if stripped.startswith(r"\end{thebibliography}"):
            inside_bibliography = False
        if inside_bibliography or stripped.startswith("%") or stripped.startswith("\\"):
            continue
        # A decimal, or a run of 2+ digits that is not a year. Two exemptions,
        # both narrow. A confidence level written "95\%" is a convention label
        # whose interval is already a macro, and a figure attributed to a cited
        # paper is that paper's result rather than ours — forcing either into a
        # generated macro would be theatre, not rigour.
        for match in re.finditer(r"(?<![\w\\])(\d+\.\d+|\d{2,})(?![\w])", stripped):
            value = match.group(1)
            if re.fullmatch(r"(19|20)\d\d", value):
                continue
            if stripped[match.end():].lstrip().startswith(r"\%"):
                continue
            if r"\citet" in stripped or r"\citep" in stripped:
                continue
            offenders.append(f"line {number}: {value!r} in {stripped[:80]!r}")
    assert not offenders, (
        "the manuscript contains numbers that are not macros, so they will not "
        f"move when the data does: {offenders}. Add them to "
        "scripts/make_paper_numbers.py instead."
    )


def test_every_figure_the_paper_includes_exists() -> None:
    """A missing figure fails the build, and does so only on the compiler."""
    if not MAIN.exists():
        pytest.skip("paper/main.tex not present")
    text = MAIN.read_text(encoding="utf-8")
    missing = []
    for match in re.finditer(r"\\includegraphics\[[^\]]*\]\{([^}]+)\}", text):
        target = (PAPER / match.group(1)).resolve()
        if not target.exists():
            missing.append(match.group(1))
    assert not missing, (
        f"main.tex includes figures that do not exist: {missing}. They are "
        "generated by scripts/make_headline_figures.py and "
        "scripts/make_supporting_figures.py."
    )


def test_every_citation_resolves_to_a_bibliography_entry() -> None:
    """An unresolved \\citet renders as a bold [?] in the PDF.

    Worth pinning here because this manuscript's bibliography is deliberately
    short: it holds only references whose title, authors and venue were checked
    against the actual publication record, not ones recalled from memory.
    """
    if not MAIN.exists():
        pytest.skip("paper/main.tex not present")
    text = MAIN.read_text(encoding="utf-8")
    keys = set(re.findall(r"\\bibitem\[[^\]]*\]\{([^}]+)\}", text))
    cited = set()
    for command in ("citet", "citep", "cite"):
        cited |= set(re.findall(rf"\\{command}\{{([^}}]+)\}}", text))
    cited = {key.strip() for group in cited for key in group.split(",")}
    unresolved = sorted(cited - keys)
    assert not unresolved, (
        f"these citations have no bibliography entry: {unresolved}"
    )


def test_no_reference_is_cited_without_being_used() -> None:
    """An entry nobody cites is usually one that was pasted, not read."""
    if not MAIN.exists():
        pytest.skip("paper/main.tex not present")
    text = MAIN.read_text(encoding="utf-8")
    keys = set(re.findall(r"\\bibitem\[[^\]]*\]\{([^}]+)\}", text))
    cited = set()
    for command in ("citet", "citep", "cite"):
        cited |= {
            key.strip()
            for group in re.findall(rf"\\{command}\{{([^}}]+)\}}", text)
            for key in group.split(",")
        }
    unused = sorted(keys - cited)
    assert not unused, (
        f"bibliography entries nobody cites: {unused}. Either cite them or "
        "remove them — an uncited reference in a short bibliography reads as "
        "padding, and this one is short on purpose."
    )
