"""A generator writing to a path git does not track is invisible drift.

`.github/scripts/report_drift.sh` used to ask `git diff --quiet`, which answers
"did any *tracked* file change?". The question that matters is "does the working
tree match the repository?", and the gap between the two is exactly a file
nobody committed.

That gap ran for three weeks. `run_endurance_audit_cases.py` wrote
`reports/imsa/audit_cases.md` and `reports/imsa/gt3_audit_cases.md`; git carried
`reports/imsa/gtp/audit_cases.md` and `reports/imsa/gtd/audit_cases.md` instead,
hand-copied once and regenerated never. Every CI run produced untracked files
the check could not see, while the stale tracked copies it could see never moved
— so the job passed green while a published report carried six numbers that had
drifted from the tables printed directly above them.

The drift script now uses `git status --porcelain`, which sees untracked files.
This is the same guarantee, enforced locally and without needing to run the
generators: **every report path a generator writes must be a path git tracks.**

It is a stronger check than "the file exists", because a file can exist on disk
for months without ever entering the repository, and that is precisely what
happened.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

#: Report filenames written from a directory chosen at call time rather than
#: written literally. `write_report` in run_endurance_audit_cases.py takes
#: `out_dir`, so its paths cannot be read off a string literal — they are
#: checked by the duplicate test below instead.
DYNAMIC = frozenset({"audit_cases.md", "gt3_audit_cases.md"})


def _tracked_files() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True
    )
    return {line.replace("\\", "/") for line in result.stdout.splitlines()}


def _generated_report_paths() -> set[str]:
    """Report paths a script writes as a literal `reports/...` string."""
    paths = set()
    sources = list((REPO / "scripts").glob("*.py")) + list((REPO / "src").rglob("*.py"))
    for source in sources:
        text = source.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(r'"(reports/[A-Za-z0-9_/]+\.md)"', text):
            paths.add(match.group(1))
    return paths


@pytest.fixture(scope="module")
def tracked() -> set[str]:
    return _tracked_files()


def test_every_literal_report_path_is_tracked(tracked: set[str]) -> None:
    """A generator's own output path must exist in the repository."""
    untracked = sorted(p for p in _generated_report_paths() if p not in tracked)
    assert not untracked, (
        f"these generators write to paths git does not track: {untracked}. "
        "Nothing downstream reads them — readers, links and the drift check "
        "all see whatever stale copy IS committed. Commit the path, or point "
        "the generator at the one already committed."
    )


def test_no_report_exists_on_disk_without_being_tracked(tracked: set[str]) -> None:
    """The general form, and the one that would have caught the original.

    Catches a generator writing anywhere under reports/ regardless of how its
    path was built, which is what defeated the literal scan above.
    """
    on_disk = {
        str(path.relative_to(REPO)).replace("\\", "/")
        for path in (REPO / "reports").rglob("*.md")
    }
    untracked = sorted(on_disk - tracked)
    assert not untracked, (
        f"these report files exist but are not in the repository: {untracked}. "
        "Either a generator started writing somewhere new and nobody committed "
        "it, or they are leftovers. Both are the same defect: a file a reader "
        "can open locally, cannot open on GitHub, and that no check watches."
    )


def test_the_drift_check_sees_untracked_files() -> None:
    """The CI script must not go back to `git diff`.

    This is the one-line regression that caused it, so it is worth pinning by
    name rather than trusting that nobody simplifies it back.
    """
    script = REPO / ".github" / "scripts" / "report_drift.sh"
    if not script.exists():
        pytest.skip("drift script not present")
    text = script.read_text(encoding="utf-8")
    assert "git status --porcelain" in text, (
        "report_drift.sh no longer uses `git status --porcelain`. If it has "
        "gone back to `git diff`, it is blind to untracked files again — a "
        "generator writing to a new path will drift silently and the job will "
        "pass green, which is exactly how six published numbers went stale."
    )
    assert not re.search(r"^\s*if git diff --quiet", text, re.MULTILINE), (
        "the drift check gates on `git diff --quiet`, which cannot see a file "
        "that was never committed."
    )


def test_no_two_directories_hold_the_same_generated_report(tracked: set[str]) -> None:
    """Per-series and per-class copies are the design; silent duplicates are not.

    `degradation_phase2.md` legitimately exists once per series — that is the
    class-separation rule this project runs on. What is not legitimate is two
    copies of the *same* content in sibling directories, one regenerated and
    one frozen, because a reader has no way to tell which they opened.
    """
    from collections import defaultdict

    by_content: dict[bytes, list[str]] = defaultdict(list)
    for relative in sorted(p for p in tracked if p.startswith("reports/")
                           and p.endswith(".md")):
        path = REPO / relative
        if path.exists():
            by_content[path.read_bytes()].append(relative)

    identical = {
        paths[0]: paths for paths in by_content.values() if len(paths) > 1
    }
    assert not identical, (
        f"byte-identical report files in different directories: {identical}. "
        "One of them is regenerated and the other is a copy that froze the day "
        "it was made. Delete the copy and link to the live one."
    )
