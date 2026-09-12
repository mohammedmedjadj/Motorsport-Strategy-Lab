"""The Kaggle notebook is the one artifact here that nothing checked.

It clones this repository and reads `data/derived/` from the clone, so if a
path it wants is renamed or a module it imports moves, the notebook breaks for
every reader and nothing in this suite notices.

The identifier checks below exist because of a specific mistake. The Kaggle
account is `mohammedredamedjadj`; the GitHub one is `mohammedmedjadj`. A dataset
URL written with the GitHub spelling returns 404, which read as "the dataset was
never published" and very nearly had a live, attached dataset detached from its
notebook to fix a problem that did not exist. One character of divergence
between three files, and no way to see it by reading any of them alone.

So: the dataset the kernel attaches, the dataset the notebook links, and the
dataset `data/derived/dataset-metadata.json` publishes must be the same string.
Whether that string resolves is a question for a browser -- what these can do is
make the three agree, which is what turns a typo into a test failure.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
NOTEBOOK = REPO / "notebooks" / "kaggle_demo.ipynb"
KERNEL = REPO / "notebooks" / "kernel-metadata.json"
DATASET = REPO / "data" / "derived" / "dataset-metadata.json"


@pytest.fixture(scope="module")
def notebook() -> dict:
    if not NOTEBOOK.exists():
        pytest.skip("notebooks/kaggle_demo.ipynb not present")
    return json.loads(NOTEBOOK.read_text(encoding="utf-8"))


def _source(notebook: dict, kind: str) -> str:
    return "\n".join(
        "".join(cell["source"])
        for cell in notebook["cells"]
        if cell["cell_type"] == kind
    )


def _json(path: Path) -> dict:
    if not path.exists():
        pytest.skip(f"{path.relative_to(REPO)} not present")
    return json.loads(path.read_text(encoding="utf-8"))


def test_every_data_path_the_notebook_reads_exists(notebook: dict) -> None:
    """The notebook reads from a clone of this repo, so these resolve here."""
    paths = sorted(set(re.findall(
        r'["\'](data/[^"\']+\.(?:csv|parquet|json|duckdb))["\']',
        _source(notebook, "code"),
    )))
    assert paths, "the notebook reads no data files, which is not expected"
    missing = [path for path in paths if not (REPO / path).exists()]
    assert not missing, (
        "the notebook reads files that are not in the repository it clones, so "
        f"it fails partway through for every reader: {missing}"
    )


def test_every_module_the_notebook_imports_exists(notebook: dict) -> None:
    modules = sorted(set(re.findall(
        r"from (src\.[\w.]+) import", _source(notebook, "code")
    )))
    assert modules, "the notebook imports nothing from src/, which is not expected"
    missing = [
        module for module in modules
        if not (REPO / (module.replace(".", "/") + ".py")).exists()
    ]
    assert not missing, (
        f"the notebook imports modules that no longer exist: {missing}"
    )


def test_the_notebook_and_the_kernel_name_the_same_dataset(
    notebook: dict,
) -> None:
    """A link and an attachment that disagree is a typo nobody can see."""
    kernel = _json(KERNEL)
    attached = kernel.get("dataset_sources") or []
    linked = re.findall(
        r"https://www\.kaggle\.com/datasets/([\w-]+/[\w-]+)",
        _source(notebook, "markdown"),
    )
    assert attached, (
        "kernel-metadata.json attaches no dataset. The published notebook is "
        "attached to one, so pushing this detaches it."
    )
    assert linked, (
        "the notebook links no dataset, but the kernel attaches one. A reader "
        "has no way to find the data the kernel declares."
    )
    assert set(linked) == set(attached), (
        f"the notebook links {sorted(set(linked))} and the kernel attaches "
        f"{sorted(set(attached))}. One of them is a typo, and the wrong one "
        "returns 404 without saying which."
    )


def test_the_published_dataset_manifest_matches_what_the_kernel_attaches() -> None:
    """data/derived/ is what gets pushed as the dataset; it must be that dataset."""
    kernel = _json(KERNEL)
    manifest = _json(DATASET)
    attached = kernel.get("dataset_sources") or []
    assert manifest.get("id") in attached, (
        f"data/derived/dataset-metadata.json publishes {manifest.get('id')!r} "
        f"but the kernel attaches {attached}. Pushing the dataset would update "
        "one dataset while the notebook reads another."
    )


def test_the_kaggle_and_github_accounts_are_not_confused(notebook: dict) -> None:
    """One character apart, and the wrong one 404s silently.

    Kaggle URLs must carry the Kaggle account; GitHub URLs the GitHub one.
    """
    prose = _source(notebook, "markdown") + _source(notebook, "code")
    wrong_on_kaggle = re.findall(
        r"https://www\.kaggle\.com/\S*?/mohammedmedjadj/", prose
    ) + re.findall(r"https://www\.kaggle\.com/(?:datasets|code)/mohammedmedjadj\b",
                   prose)
    assert not wrong_on_kaggle, (
        "a Kaggle URL uses the GitHub account name. Kaggle is "
        f"'mohammedredamedjadj': {wrong_on_kaggle}"
    )
    wrong_on_github = re.findall(
        r"https://github\.com/mohammedredamedjadj\b", prose
    )
    assert not wrong_on_github, (
        "a GitHub URL uses the Kaggle account name. GitHub is "
        f"'mohammedmedjadj': {wrong_on_github}"
    )


def test_the_kernel_points_at_the_notebook_beside_it() -> None:
    kernel = _json(KERNEL)
    code_file = kernel.get("code_file", "")
    assert (KERNEL.parent / code_file).exists(), (
        f"kernel-metadata.json names code_file {code_file!r}, which is not there"
    )
