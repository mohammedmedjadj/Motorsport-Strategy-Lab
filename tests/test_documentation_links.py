"""Every link in the documentation must point at something that exists.

Added after a section was renamed — "Modelling extensions across all three
series" became "across series" once a fourth was modelled — and the navigation
link at the top of the README kept pointing at the old anchor. The page still
rendered; the link silently did nothing.

That is the failure mode this module is for. A broken file link is at least
visible as a 404, but a broken in-page anchor scrolls nowhere and looks like
the reader missed it. Both are cheap to check and neither was being checked,
in a repository whose README is its primary deliverable.

Scoped to the repository's own documents. External URLs are deliberately not
fetched: a test that needs the network to pass will fail for reasons that have
nothing to do with this project.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

#: Markdown inline links, `[label](target)`. Reference-style links and bare
#: URLs are not used anywhere in these documents.
MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")

#: GitHub renders inline HTML in markdown, and this README's navigation bar and
#: badge row are written that way. Checking only markdown syntax would have
#: missed the exact defect that prompted this module: the stale
#: ``#modelling-extensions-across-all-three-series`` anchor lives in an
#: ``<a href>``, not in a ``[]()``.
HTML_LINK = re.compile(r"<a\s[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>",
                       re.IGNORECASE | re.DOTALL)


def _links(document: Path) -> list[tuple[str, str]]:
    """Every (label, target) pair in a document, markdown and HTML alike."""
    text = document.read_text(encoding="utf-8")
    return (
        MARKDOWN_LINK.findall(text)
        + [(label.strip(), target) for target, label in HTML_LINK.findall(text)]
    )

#: GitHub builds an anchor by lowercasing a heading, dropping everything that
#: is not alphanumeric, space or hyphen, then replacing spaces with hyphens.
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)


def _documents() -> list[Path]:
    return sorted(
        [REPO / "README.md", REPO / "CONTRIBUTING.md", REPO / "demo" / "README.md"]
        + list((REPO / "reports").rglob("*.md"))
        + list((REPO / "data").rglob("*.md"))
    )


def _anchor(heading: str) -> str:
    """The anchor GitHub generates for a heading.

    Inline markdown is stripped first: a heading written as ``## The **best**
    result`` anchors as ``the-best-result``, not ``the-result``.
    """
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", heading)  # links -> label
    text = text.replace("`", "").replace("*", "").replace("_", "")
    text = re.sub(r"[^\w\s-]", "", text.lower(), flags=re.UNICODE)
    return re.sub(r"\s+", "-", text.strip())


def _existing(document: Path) -> set[str]:
    return {_anchor(h) for h in HEADING.findall(document.read_text(encoding="utf-8"))}


def test_every_file_link_resolves() -> None:
    """A link to a file this repository does not have is a broken promise.

    These documents cite their own sources constantly — a report links the
    script that produced it, the README links every phase report — so a moved
    or renamed file breaks a claim about provenance, not just navigation.

    Deliberately **not** parametrised per document. There are around 55 of
    them, and three checks would become 165 test cases in a suite whose count
    is quoted in the README as a claim about coverage. The assertion message
    names the offending document, which is the only thing parametrisation
    would have bought.
    """
    broken = []
    for document in _documents():
        for label, target in _links(document):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path, _, _fragment = target.partition("#")
            if not path:
                continue
            if not (document.parent / path).exists():
                broken.append(
                    f"{document.relative_to(REPO).as_posix()}: [{label}]({target})"
                )

    assert not broken, f"links to files that do not exist: {broken}"


def test_every_in_page_anchor_resolves() -> None:
    """An anchor that scrolls nowhere is invisible until a reader clicks it.

    The case that prompted this: the README's own navigation bar pointed at
    ``#modelling-extensions-across-all-three-series`` after the heading was
    renamed to drop the "three", because renaming a heading and updating the
    links to it are two separate acts and only one of them is forced. The same
    pass found a ``[phase 3](#)`` placeholder that had never been filled in.
    """
    broken = []
    for document in _documents():
        anchors = _existing(document)
        broken += [
            f"{document.relative_to(REPO).as_posix()}: [{label}]({target})"
            for label, target in _links(document)
            if target.startswith("#") and _anchor(target[1:]) not in anchors
        ]

    assert not broken, f"anchors pointing at headings that do not exist: {broken}"


def test_cross_document_anchors_resolve() -> None:
    """`other.md#section` has to name a heading in *that* document.

    Checked separately because it fails differently: the file exists, so the
    link works well enough to look fine, and only the scroll position is
    wrong — which nobody notices in review.
    """
    broken = []
    for document in _documents():
        for label, target in _links(document):
            if target.startswith(("http", "mailto:", "#")) or "#" not in target:
                continue
            path, _, fragment = target.partition("#")
            other = document.parent / path
            if not other.exists() or other.suffix != ".md":
                continue
            if _anchor(fragment) not in _existing(other):
                broken.append(
                    f"{document.relative_to(REPO).as_posix()}: [{label}]({target})"
                )

    assert not broken, f"links pointing at headings that do not exist: {broken}"


PHASE_IN_FILENAME = re.compile(r"phase(\d)\.md$")
PHASE_IN_TITLE = re.compile(r"phase\s+(\d)", re.IGNORECASE)


def test_phase_reports_are_titled_with_their_own_phase_number() -> None:
    """A report called ``safety_car_phase3.md`` must not be titled "Phase 2".

    Three of them were. The endurance reports were numbered under an early
    convention where phase 0 did not count, the filenames later adopted the F1
    numbering, and the titles never followed — so ``degradation_phase2.md``
    opened with "Phase 1", ``safety_car_phase3.md`` with "Phase 2", and the
    README's phase table disagreed with every one of them.

    Nobody catches this by reading, because the number is right there in the
    heading and looks authoritative. It is one line of code to check.
    """
    wrong = []
    for report in sorted((REPO / "reports").rglob("*phase?.md")):
        expected = PHASE_IN_FILENAME.search(report.name)
        if not expected:
            continue
        title = report.read_text(encoding="utf-8").splitlines()[0]
        stated = PHASE_IN_TITLE.search(title)
        if stated and stated.group(1) != expected.group(1):
            wrong.append(
                f"{report.relative_to(REPO).as_posix()} is titled "
                f"{title.strip('# ')!r} but its filename says phase "
                f"{expected.group(1)}"
            )

    assert not wrong, f"phase reports whose title contradicts their filename: {wrong}"


def test_no_report_sits_at_the_root_of_reports() -> None:
    """Every report belongs to a series, a class, or the cross-series set.

    ``reports/`` holds one file — its own README, the map. Anything else at
    that level is a document with no stated owner, which is how the layout got
    hard to read in the first place: eight cross-series documents sat beside
    four series directories with nothing saying which was which.

    It also catches a generator whose output path was not updated when its
    report moved. Three scripts kept writing to the old root after the
    reorganisation, silently recreating files next to the ones that had been
    moved — same name, two locations, and the stale copy is the one a reader
    finds first.
    """
    stray = sorted(
        path.name
        for path in (REPO / "reports").glob("*.md")
        # PROVENANCE.md is about the repository as a whole -- who decided
        # what -- so it has no series or class to live under.
        if path.name not in {"README.md", "PROVENANCE.md"}
    )
    assert not stray, (
        f"reports/ should hold only README.md and PROVENANCE.md; found {stray}. Either move the "
        "document into the series, class or cross_series directory it belongs "
        "to, or fix the generator that wrote it there."
    )
