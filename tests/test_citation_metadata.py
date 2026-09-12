"""Two DOIs, and using the wrong one is a silent, permanent error.

Zenodo mints two identifiers. The *concept* DOI resolves to whatever the newest
version of the deposit is; the *version* DOI is frozen at one release. A badge,
a footer, an email or a paper footnote pointing at the version DOI still works
after v1.1.0 ships -- it just quietly sends every reader to a superseded
archive, and nothing fails to tell anyone.

So the rule the project owner set is enforced here rather than only written
down: a general pointer to the project uses the concept DOI, and the version DOI
appears only where a formal citation of one release belongs.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

#: Resolves to the newest version, forever. This is the default.
CONCEPT_DOI = "10.5281/zenodo.22726130"

#: Frozen at v1.0.0. Only for citing that exact state.
VERSION_DOI = "10.5281/zenodo.22726131"

#: Everything that sends a reader to the archive. All of these must carry the
#: concept DOI, because all of them outlive v1.0.0.
GENERAL_POINTERS = [
    "README.md",
    "docs/index.html",
    "paper/main.tex",
    "outreach/one_pager.md",
    "outreach/emails.md",
    "outreach/targets.md",
    "outreach/README.md",
]

#: Files that explain the difference between the two DOIs, or give a formal
#: citation of one release. Naming the frozen DOI there is the point, so the
#: strict check below skips them -- what it guards is the other case, a bare
#: link that happens to have been written with the version DOI.
EXPLAINS_BOTH = [
    "CITATION.cff",
    "README.md",
    "docs/index.html",
    "paper/README.md",
]


def _read(relative: str) -> str:
    path = REPO / relative
    if not path.exists():
        pytest.skip(f"{relative} not present")
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize("relative", GENERAL_POINTERS)
def test_general_pointers_use_the_concept_doi(relative: str) -> None:
    text = _read(relative)
    if CONCEPT_DOI not in text and VERSION_DOI not in text:
        pytest.skip(f"{relative} names no DOI")
    assert CONCEPT_DOI in text, (
        f"{relative} points at the project but does not carry the concept DOI "
        f"{CONCEPT_DOI}, which is the one that keeps resolving after a new "
        "version is released"
    )


@pytest.mark.parametrize(
    "relative", [f for f in GENERAL_POINTERS if f not in EXPLAINS_BOTH]
)
def test_bare_pointers_do_not_use_the_version_doi(relative: str) -> None:
    text = _read(relative)
    assert VERSION_DOI not in text, (
        f"{relative} names the v1.0.0 DOI {VERSION_DOI}. That one is frozen, so "
        "readers of this file will be sent to a superseded archive as soon as "
        f"there is a v1.1.0. Use the concept DOI {CONCEPT_DOI} instead."
    )


def test_the_citation_file_carries_the_version_doi() -> None:
    """A citation names the state a result came from, not a moving target."""
    text = _read("CITATION.cff")
    assert re.search(rf"(?m)^doi:\s*{re.escape(VERSION_DOI)}\s*$", text), (
        "CITATION.cff's top-level `doi` is what GitHub's Cite this repository "
        f"button renders. It should be the frozen v1.0.0 DOI {VERSION_DOI}."
    )


def test_the_citation_file_also_declares_the_concept_doi() -> None:
    text = _read("CITATION.cff")
    assert CONCEPT_DOI in text, (
        "CITATION.cff should also list the concept DOI under `identifiers`, so "
        "a reader can find the pointer that tracks future versions"
    )


def test_the_citation_file_has_what_github_needs_to_render_a_citation() -> None:
    """A CFF missing a required key renders no button at all, silently."""
    yaml = pytest.importorskip("yaml")
    data = yaml.safe_load(_read("CITATION.cff"))

    for key in ("cff-version", "message", "title", "authors"):
        assert key in data, f"CITATION.cff is missing the required key {key!r}"

    assert data["cff-version"] == "1.2.0", (
        f"CITATION.cff declares cff-version {data['cff-version']!r}; GitHub "
        "renders 1.2.0"
    )
    assert isinstance(data["authors"], list) and data["authors"], (
        "CITATION.cff has no authors, so there is nobody to cite"
    )
    for author in data["authors"]:
        assert "family-names" in author and "given-names" in author, (
            f"an author entry is missing a name field: {author}"
        )

    # A citation without these renders, but renders wrong: no year, no version.
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(data.get("date-released", ""))), (
        "CITATION.cff needs `date-released` as YYYY-MM-DD, or the citation "
        "GitHub renders carries no year"
    )
    assert str(data.get("version", "")), "CITATION.cff needs a `version`"


def test_the_release_the_citation_names_matches_the_version_doi() -> None:
    """If the version bumps and the DOI does not, the citation points at the wrong archive."""
    yaml = pytest.importorskip("yaml")
    data = yaml.safe_load(_read("CITATION.cff"))
    paper_readme = _read("paper/README.md")
    version = str(data["version"])
    assert f"v{version}" in paper_readme, (
        f"CITATION.cff declares version {version!r}, but paper/README.md does "
        "not mention that release. One of the two was updated and the other "
        "was not, and the DOI table is the thing a reader trusts."
    )
