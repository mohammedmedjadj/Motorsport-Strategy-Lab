"""Two DOIs, and using the wrong one is a silent, permanent error.

Zenodo mints two identifiers. The *concept* DOI resolves to whatever the newest
version of the deposit is; the *version* DOI is frozen at one release. A badge,
a footer, an email or a paper footnote pointing at the version DOI still works
after v1.1.0 ships -- it just quietly sends every reader to a superseded
archive, and nothing fails to tell anyone.

So the rule is enforced here rather than only written down: a general
pointer to the project uses the concept DOI, and the version DOI appears only
where a formal citation of one release belongs.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

#: Resolves to the newest version, forever. This is the default, and it is the
#: one identifier here that never changes.
CONCEPT_DOI = "10.5281/zenodo.22726130"

ANY_ZENODO_DOI = re.compile(r"10\.5281/zenodo\.(\d+)")

#: Every Zenodo identifier this project has minted, concept and versions. A DOI
#: outside this set belongs to somebody else's deposit -- the paper cites one --
#: and is none of this guard's business. Offline there is no way to tell the two
#: apart except by listing mine, so a release extends this by one line. A
#: release that forgets is caught by the network check at the bottom of this
#: file instead.
OWN_ZENODO_RECORDS = {
    "22726130",   # concept, resolves to the newest version
    "22726131",   # v1.0.0, superseded
    "23220846",   # v1.1.0
}


def _citation() -> dict:
    """CITATION.cff, which is the repository's single statement of the release."""
    yaml = pytest.importorskip("yaml")
    return yaml.safe_load(_read("CITATION.cff"))


def version_doi() -> str:
    """The current version DOI, read rather than hardcoded.

    It used to be a constant in this file, which meant a release bumped the
    constant and the test then confirmed whatever had been typed into it. The
    declaration belongs in CITATION.cff; this reads it, so every other file is
    checked against one authority instead of against a copy.
    """
    doi = str(_citation().get("doi", "")).strip()
    assert ANY_ZENODO_DOI.fullmatch(doi), (
        f"CITATION.cff declares doi: {doi!r}, which is not a Zenodo DOI. "
        "Everything else keys off this value."
    )
    return doi

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
def test_bare_pointers_do_not_use_any_version_doi(relative: str) -> None:
    """A general pointer carries the concept DOI and no other Zenodo identifier.

    Checked against the pattern rather than against the current version DOI,
    because the failure this exists to catch is a *superseded* one left in
    prose -- and by definition nothing declares that value any more.
    """
    text = _read(relative)
    concept_number = ANY_ZENODO_DOI.search(CONCEPT_DOI).group(1)
    strays = {
        number for number in ANY_ZENODO_DOI.findall(text)
        if number in OWN_ZENODO_RECORDS and number != concept_number
    }
    assert not strays, (
        f"{relative} names Zenodo DOIs {sorted(strays)} besides the concept "
        f"DOI. A version DOI is frozen, so a reader following one from here "
        f"lands on a superseded archive once a new release exists. Use "
        f"{CONCEPT_DOI}."
    )


def test_the_citation_file_carries_a_version_doi_that_is_not_the_concept_one() -> None:
    """What GitHub's citation button renders has to name one frozen release."""
    doi = version_doi()
    assert doi != CONCEPT_DOI, (
        "CITATION.cff's `doi` is the concept DOI. That one moves with every "
        "release, so a citation built from it does not identify the state a "
        "result came from. It should be the current version DOI."
    )
    assert f"value: {doi}" in _read("CITATION.cff"), (
        f"CITATION.cff declares doi: {doi} but does not repeat it in "
        "`identifiers`, where the description says which release it freezes."
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


@pytest.mark.parametrize("relative", EXPLAINS_BOTH)
def test_the_explaining_files_name_no_superseded_release(relative: str) -> None:
    """Exempt from the stray check, not from being current.

    These four files describe the two-DOI distinction, so they are allowed to
    print a version DOI alongside the concept one. What they may not print is a
    *superseded* version DOI, and that is exactly what all four did at v1.1.0
    while the suite stayed green: the exemption covered the files most likely
    to be wrong, and the ones it did cover could not go wrong in the first
    place.
    """
    text = _read(relative)
    allowed = {
        ANY_ZENODO_DOI.search(CONCEPT_DOI).group(1),
        ANY_ZENODO_DOI.search(version_doi()).group(1),
    }
    stale = {
        number for number in ANY_ZENODO_DOI.findall(text)
        if number in OWN_ZENODO_RECORDS and number not in allowed
    }
    assert not stale, (
        f"{relative} still names Zenodo DOIs {sorted(stale)}, which belong to "
        f"superseded releases of this project. CITATION.cff declares "
        f"{version_doi()}. A reader comes to this file to learn which "
        "identifier to use, so a stale one here is worse than anywhere else."
    )


def test_every_minted_record_is_accounted_for() -> None:
    """The declared release has to be in the list the stray check reads.

    Without this, a release that updates CITATION.cff but not the list leaves
    the stray check unable to recognise the previous DOI as mine, which is the
    exact failure it exists to catch.
    """
    declared = ANY_ZENODO_DOI.search(version_doi()).group(1)
    assert declared in OWN_ZENODO_RECORDS, (
        f"CITATION.cff declares version DOI ...{declared}, which is missing "
        "from OWN_ZENODO_RECORDS. Add it, or the previous version DOI stops "
        "being recognised as this project's when it is left somewhere."
    )


def test_the_concept_doi_resolves_to_the_release_the_repository_declares() -> None:
    """The only check that catches a release nobody wrote down.

    Everything else here compares the repository against itself, so it is blind
    to a release where I updated nothing: there is no inconsistency to
    find. Zenodo guarantees the concept DOI points at the newest version, so
    asking it is the one authority outside this repository.

    Skipped when the network is unreachable, because being offline is not an
    error. A fetch that succeeds and disagrees is.
    """
    import json
    import urllib.error
    import urllib.request

    concept_number = ANY_ZENODO_DOI.search(CONCEPT_DOI).group(1)
    url = f"https://zenodo.org/api/records/{concept_number}"
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            record = json.load(response)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        pytest.skip(f"Zenodo unreachable ({type(exc).__name__}); nothing to compare")

    newest_doi = str(record.get("doi", ""))
    newest_version = str(record.get("metadata", {}).get("version", "")).lstrip("v")
    declared_version = str(_citation().get("version", "")).lstrip("v")

    assert newest_doi == version_doi(), (
        f"Zenodo's newest version of this deposit is {newest_doi}, and "
        f"CITATION.cff declares {version_doi()}. A release was published and "
        "the repository was not updated to match it."
    )
    assert newest_version == declared_version, (
        f"Zenodo says the newest version is {newest_version!r} and "
        f"CITATION.cff says {declared_version!r}."
    )
