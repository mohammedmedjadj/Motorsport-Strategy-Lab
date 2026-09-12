"""No invisible characters anywhere in the repository.

There is no watermark in text written by an AI assistant — no hidden marker
exists to find. But "trust me" is not evidence, and a reviewer who wondered
would have no way to check without doing this themselves. So the repository
checks itself, on every run.

What this catches is real regardless of where the text came from. Zero-width
characters and bidirectional overrides get into files through copied web pages,
some editors, and a handful of genuine attacks: a right-to-left override inside
an identifier can make source read one way and execute another
(CVE-2021-42574, "Trojan Source"). None of that belongs in a repository whose
whole argument is that it can be checked.

Non-breaking and thin spaces are handled separately because they are typography
rather than a hazard. They are flagged in source files, where they break
tooling, and left alone in LaTeX, where `1,280~decisions` is correct.

Every character below is written as a code point rather than typed. The first
version of this file used literals and failed on itself, which was fair.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

#: Renders as nothing.
INVISIBLE = {
    0x200B: "zero-width space",
    0x200C: "zero-width non-joiner",
    0x200D: "zero-width joiner",
    0x2060: "word joiner",
    0xFEFF: "byte-order mark / zero-width no-break space",
    0x00AD: "soft hyphen",
    0x180E: "Mongolian vowel separator",
    0x2061: "function application",
    0x2062: "invisible times",
    0x2063: "invisible separator",
    0x2064: "invisible plus",
}

#: Reorders what follows. This is how Trojan Source works.
BIDI = {
    0x202A: "left-to-right embedding",
    0x202B: "right-to-left embedding",
    0x202C: "pop directional formatting",
    0x202D: "left-to-right override",
    0x202E: "right-to-left override",
    0x2066: "left-to-right isolate",
    0x2067: "right-to-left isolate",
    0x2068: "first strong isolate",
    0x2069: "pop directional isolate",
}

#: Visible, but not an ordinary space. Fine in LaTeX, a nuisance in code.
EXOTIC_SPACES = {
    0x00A0: "non-breaking space",
    0x202F: "narrow non-breaking space",
    0x2007: "figure space",
    0x2009: "thin space",
}

TEXT_SUFFIXES = frozenset({
    ".md", ".tex", ".py", ".html", ".css", ".yml", ".yaml",
    ".cff", ".json", ".txt", ".sh", ".ipynb", ".toml", ".cfg",
})

SKIP_DIRECTORIES = frozenset({
    ".git", ".venv", "venv", "__pycache__", "node_modules",
    ".pytest_cache", ".mypy_cache", "graphify-out",
})


def _tracked() -> set[Path] | None:
    """What git tracks, or None if this is not a working clone."""
    try:
        listing = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=REPO, capture_output=True, check=True, text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return {
        (REPO / name).resolve()
        for name in listing.stdout.split("\0") if name
    }


def _text_files() -> list[Path]:
    """Every text file in the repository.

    Tracked files only. An uncommitted scratch copy in the working directory is
    not part of what anyone receives, and one of them -- a local export of the
    manuscript carrying a UTF-8 byte-order mark -- used to fail this scan for a
    reason that had nothing to do with what the repository publishes. When git
    is unavailable the walk falls back to the filesystem, which is stricter and
    never less safe.
    """
    tracked = _tracked()
    return [
        path for path in REPO.rglob("*")
        if path.is_file()
        and path.suffix in TEXT_SUFFIXES
        and not SKIP_DIRECTORIES.intersection(path.parts)
        and (tracked is None or path.resolve() in tracked)
    ]


def _scan(characters: dict[int, str], paths: list[Path]) -> list[str]:
    found = []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for code, name in characters.items():
            character = chr(code)
            count = text.count(character)
            if count:
                line = text[:text.index(character)].count("\n") + 1
                found.append(
                    f"{path.relative_to(REPO)}:{line} — {name} "
                    f"(U+{code:04X}) x{count}"
                )
    return sorted(found)


@pytest.fixture(scope="module")
def text_files() -> list[Path]:
    paths = _text_files()
    assert len(paths) > 100, (
        f"only {len(paths)} text files found; the scan is not reaching the "
        "repository and would pass on nothing"
    )
    return paths


def test_no_invisible_characters(text_files: list[Path]) -> None:
    """Nothing that renders as nothing."""
    found = _scan(INVISIBLE, text_files)
    assert not found, (
        "invisible characters found:\n  " + "\n  ".join(found) + "\n\n"
        "These render as nothing and are usually pasted in by accident. "
        "Remove them."
    )


def test_no_bidirectional_overrides(text_files: list[Path]) -> None:
    """Nothing that can make source read differently from how it executes."""
    found = _scan(BIDI, text_files)
    assert not found, (
        "bidirectional control characters found:\n  " + "\n  ".join(found) +
        "\n\nThese reorder how text displays without changing what it means to "
        "a compiler, which is the Trojan Source attack (CVE-2021-42574). "
        "Remove them."
    )


def test_no_exotic_spaces_in_source(text_files: list[Path]) -> None:
    """Typographic spaces belong in LaTeX, not in code or config.

    `1,280~decisions` is right in a manuscript. A non-breaking space inside a
    Python string or a YAML key is a bug that is very hard to see.
    """
    source = [
        path for path in text_files
        if path.suffix in {".py", ".yml", ".yaml", ".json", ".sh", ".cfg", ".toml"}
    ]
    found = _scan(EXOTIC_SPACES, source)
    assert not found, (
        "non-standard spaces in source files:\n  " + "\n  ".join(found) +
        "\n\nThese look like ordinary spaces and are not. Replace with U+0020."
    )
