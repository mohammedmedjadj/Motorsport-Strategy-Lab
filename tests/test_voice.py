"""One person writes this project, and the prose says so.

Two failures this guards against, both of which had spread across the
repository before anyone read for them.

The first is describing myself from outside — "the project owner", "the
author", or a note recording an instruction received rather than a decision
taken. A repository written that way reads as though somebody else built it and
reported back.

The second is the editorial plural. "We fit the GP", "our own sweep": there is
no we. It creeps in because technical prose defaults to it, and it is precisely
the register that makes a solo project sound like a lab.

What is deliberately not flagged:

- `paper/main.tex`. The editorial "we" is a convention of the form in a paper,
  and changing it there is a writing decision, not a correctness one.
- Identifiers and interface strings. `us` in `src/audit/cases.py` names the car
  being simulated, `our_time` in the engine is the subject car's lap times, and
  "Compound if we stop" is a pit wall speaking. Python files are read for their
  comments and docstrings only, so none of those is examined.
"""

from __future__ import annotations

import ast
import io
import re
import subprocess
import tokenize
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

#: Speaking about myself in the third person, or recording an instruction
#: instead of a decision. Checked in every text file, this one excepted.
OUTSIDE_VOICE = [
    r"\bthe owner\b",
    r"\bproject owner\b",
    r"\bthe author\b",
    r"\bthe student\b",
    # "the assistant found X" is the third person and is banned. "I built this
    # project with an AI coding assistant" is me saying what I used, and it
    # opens reports/PROVENANCE.md on purpose.
    r"\bthe assistant\b",
    r"\bvalidated with [A-Z]\w+",
    r"\bas (?:I was )?instructed\b",
    r"\bI was asked\b",
    r"\bwas asked to\b",
    r"\basked me to\b",
]

#: The editorial plural, in prose only.
PLURAL_VOICE = [r"\bwe\b", r"\bour\b", r"\bours\b"]

PROSE_SUFFIXES = {".md", ".html"}
TEXT_SUFFIXES = PROSE_SUFFIXES | {".py", ".tex", ".cff", ".toml", ".yml", ".yaml"}

#: The editorial "we" belongs in a manuscript. Everything else here is checked.
PLURAL_EXEMPT = {"paper/main.tex"}


def _tracked() -> list[Path]:
    listing = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPO, capture_output=True, text=True, check=True
    )
    return [
        REPO / name
        for name in listing.stdout.split("\0")
        if name and Path(name).suffix in TEXT_SUFFIXES
    ]


def _relative(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def _prose(path: Path) -> str:
    """Everything a reader reads, and nothing a machine reads.

    For Python that means comments and docstrings. Identifiers, string literals
    that reach a user interface, and test fixtures are not prose and are not
    where this defect lives.
    """
    text = path.read_text(encoding="utf-8")
    if path.suffix != ".py":
        return text

    pieces: list[str] = []
    try:
        for token in tokenize.generate_tokens(io.StringIO(text).readline):
            if token.type == tokenize.COMMENT:
                pieces.append(token.string)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass

    try:
        tree = ast.parse(text)
    except SyntaxError:
        return "\n".join(pieces)
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            doc = ast.get_docstring(node, clean=False)
            if doc:
                pieces.append(doc)
    return "\n".join(pieces)


def _offenders(patterns: list[str], plural: bool) -> list[str]:
    found: list[str] = []
    for path in _tracked():
        relative = _relative(path)
        if relative == "tests/test_voice.py":
            continue
        if plural and relative in PLURAL_EXEMPT:
            continue
        prose = _prose(path)
        for pattern in patterns:
            for match in re.finditer(pattern, prose, re.IGNORECASE):
                line = prose[: match.start()].count("\n") + 1
                context = prose.splitlines()[line - 1].strip()[:90]
                found.append(f"{relative}: {match.group(0)!r} in {context!r}")
    return sorted(found)


def test_nothing_describes_this_project_from_outside() -> None:
    offenders = _offenders(OUTSIDE_VOICE, plural=False)
    assert not offenders, (
        "these describe me in the third person, or record an instruction "
        "received rather than a decision taken. This project has one author "
        "and the prose says so:\n  " + "\n  ".join(offenders)
    )


def test_prose_does_not_use_the_editorial_plural() -> None:
    offenders = _offenders(PLURAL_VOICE, plural=True)
    assert not offenders, (
        "there is no we. Rewrite in the first person singular, or in the "
        "passive where the actor does not matter:\n  " + "\n  ".join(offenders)
    )


def test_the_exemption_list_still_points_at_something() -> None:
    """An exemption for a file that has moved silently stops exempting anything."""
    missing = [name for name in PLURAL_EXEMPT if not (REPO / name).exists()]
    assert not missing, (
        f"PLURAL_EXEMPT names files that do not exist: {missing}. Either fix "
        "the path or drop the exemption."
    )


def test_the_guard_reads_a_real_body_of_prose() -> None:
    """A tokenizer failure would make every test above pass on nothing."""
    total = sum(len(_prose(path)) for path in _tracked())
    assert total > 200_000, (
        f"only {total} characters of prose were read; the scan is not reaching "
        "the repository and would pass on an empty string"
    )
