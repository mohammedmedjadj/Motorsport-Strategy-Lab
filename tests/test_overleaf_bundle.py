"""The Overleaf bundle carries the current manuscript, not an older one.

The worry this answers is specific and reasonable: the bundle is a zip built by
hand-run command, it is gitignored, and nothing about looking at it says which
revision it holds. Uploading a stale one compiles a paper that no longer
exists, and the compile succeeds, so there is no error to notice.

So the bundle is rebuilt here from whatever is on disk and compared byte for
byte against the sources. Nothing is cached between runs and no previously
built zip is trusted: if the files on disk and the files in a fresh bundle ever
disagree, that is the bug.

The one thing this cannot check is whether the zip the user actually uploaded
was the current one. For that the build prints a sha256, which is what to
compare against.
"""

from __future__ import annotations

import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PAPER = REPO / "paper"
MAIN = PAPER / "main.tex"
SCRIPT = REPO / "scripts" / "make_overleaf_bundle.py"


@pytest.fixture(scope="module")
def bundle(tmp_path_factory):
    """A bundle built now, in a scratch copy, from the sources on disk."""
    if not SCRIPT.exists():
        pytest.skip("scripts/make_overleaf_bundle.py not present")
    sys.path.insert(0, str(REPO))
    import importlib

    module = importlib.import_module("scripts.make_overleaf_bundle")
    importlib.reload(module)
    built = module.build()
    assert built.exists(), "build() reported success without writing a file"
    return built


def test_the_bundle_holds_the_manuscript_currently_on_disk(bundle) -> None:
    """The whole point. A stale member here is a paper compiled from the past."""
    with zipfile.ZipFile(bundle) as archive:
        inside = archive.read("main.tex")
    assert inside == MAIN.read_bytes(), (
        "main.tex inside the bundle differs from paper/main.tex on disk. "
        "Anything uploaded from this bundle compiles a manuscript that is not "
        "the current one, and the compile will succeed anyway."
    )


def test_the_generated_numbers_travel_with_it(bundle) -> None:
    with zipfile.ZipFile(bundle) as archive:
        inside = archive.read("numbers.tex")
    assert inside == (PAPER / "numbers.tex").read_bytes(), (
        "numbers.tex inside the bundle is not the generated one on disk, so "
        "the figures in the compiled PDF are from an earlier run of "
        "scripts/make_paper_numbers.py"
    )


def test_every_figure_the_paper_includes_is_in_the_bundle(bundle) -> None:
    """Overleaf refuses "..", so a missing figure is a grey box, not an error."""
    text = MAIN.read_text(encoding="utf-8")
    included = re.findall(r"\\includegraphics\[[^\]]*\]\{([^}]+)\}", text)
    assert included, "the paper includes no figures, which is not expected"
    with zipfile.ZipFile(bundle) as archive:
        names = set(archive.namelist())
    missing = [name for name in included if f"figures/{name}" not in names]
    assert not missing, (
        f"the bundle is missing {missing}. Those figures would render as "
        "missing-file boxes in the Overleaf PDF without failing the compile."
    )


def test_the_figures_in_the_bundle_are_the_current_ones(bundle) -> None:
    """A regenerated figure that never reaches the zip is the same defect."""
    sys.path.insert(0, str(REPO))
    import importlib

    module = importlib.import_module("scripts.make_overleaf_bundle")
    resolved = module.resolve_figures(MAIN.read_text(encoding="utf-8"))
    with zipfile.ZipFile(bundle) as archive:
        for name, source in resolved.items():
            assert archive.read(f"figures/{name}") == source.read_bytes(), (
                f"{name} in the bundle differs from {source}"
            )


def test_nothing_in_the_bundle_escapes_its_own_directory(bundle) -> None:
    """Overleaf rejects a path with "..", and so should the bundle."""
    with zipfile.ZipFile(bundle) as archive:
        names = archive.namelist()
    offenders = [name for name in names if ".." in name or name.startswith("/")]
    assert not offenders, (
        f"these paths would be rejected by Overleaf: {offenders}"
    )


def test_building_it_twice_gives_the_same_bytes(bundle) -> None:
    """Reproducible, so a differing checksum means a differing manuscript.

    Without this, comparing the sha256 printed by the build against the file
    that was uploaded would prove nothing: two builds of the same sources
    would already differ on their timestamps.
    """
    import hashlib
    import importlib

    first = hashlib.sha256(bundle.read_bytes()).hexdigest()
    module = importlib.import_module("scripts.make_overleaf_bundle")
    again = module.build()
    second = hashlib.sha256(again.read_bytes()).hexdigest()
    assert first == second, (
        "two builds of the same sources produced different bytes, so the "
        "checksum cannot be used to tell a current bundle from a stale one"
    )


def test_the_script_runs_end_to_end_and_prints_a_checksum() -> None:
    """The checksum is how a person tells which bundle they uploaded."""
    if not SCRIPT.exists():
        pytest.skip("scripts/make_overleaf_bundle.py not present")
    done = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=REPO, capture_output=True, text=True,
    )
    assert done.returncode == 0, done.stderr
    assert re.search(r"sha256 [0-9a-f]{64}", done.stdout), (
        f"the build no longer prints a checksum to compare against:\n{done.stdout}"
    )
