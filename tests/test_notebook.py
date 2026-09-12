"""The Kaggle notebook is the one artifact here that nothing checked.

It clones this repository and reads `data/derived/` from the clone, so if a
path it wants is renamed or a module it imports moves, the notebook breaks for
every reader and nothing in this suite notices. That is how it came to carry a
link announcing a Kaggle dataset that was never published: a false statement in
a document written for researchers, sitting there because no test read the file.

These do not execute the notebook. They check the two things that can rot
without anyone touching the notebook itself -- the paths and imports it depends
on -- and the one thing that was actually wrong.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
NOTEBOOK = REPO / "notebooks" / "kaggle_demo.ipynb"
METADATA = REPO / "notebooks" / "kernel-metadata.json"


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


def test_the_notebook_announces_no_dataset_that_does_not_exist(
    notebook: dict,
) -> None:
    """It linked a Kaggle dataset that was never published, and said so in prose.

    A broken dependency fails loudly. A sentence telling a researcher that data
    is published, next to a link that 404s, fails quietly and damages more.
    """
    prose = _source(notebook, "markdown")
    offenders = [
        url for url in re.findall(r"https://www\.kaggle\.com/datasets/\S+", prose)
    ]
    assert not offenders, (
        "the notebook links a Kaggle dataset. Nothing in this repository "
        "publishes one, and four files under data/derived/ come from sources "
        "whose licence data/external/README.md records as unchecked -- so a "
        f"dataset cannot be published under a declared licence either: {offenders}"
    )


def test_the_kernel_declares_no_dataset_source() -> None:
    """A kernel pointing at a dataset that does not exist cannot be pushed."""
    if not METADATA.exists():
        pytest.skip("notebooks/kernel-metadata.json not present")
    metadata = json.loads(METADATA.read_text(encoding="utf-8"))
    assert not metadata.get("dataset_sources"), (
        "kernel-metadata.json declares a dataset source. The notebook clones "
        "this repository and needs none, and `kaggle kernels push` fails if "
        f"the dataset does not exist: {metadata['dataset_sources']}"
    )


def test_the_kernel_points_at_the_notebook_beside_it() -> None:
    if not METADATA.exists():
        pytest.skip("notebooks/kernel-metadata.json not present")
    metadata = json.loads(METADATA.read_text(encoding="utf-8"))
    code_file = metadata.get("code_file", "")
    assert (METADATA.parent / code_file).exists(), (
        f"kernel-metadata.json names code_file {code_file!r}, which is not there"
    )
