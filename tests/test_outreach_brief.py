"""The brief is the one document here that goes to a named researcher.

Everything else in `outreach/` is a template I fill in before sending. This one
is generated with the numbers already in it, and it was written because Wytze
de Vries asked for the correlation data behind Result 2. A stale figure in it
would be wrong in front of someone who works on exactly this problem.

So the numbers on the page are checked against the artifacts they claim to come
from, and the committed PDF is checked against a fresh build. The generator
omits the PDF CreationDate for that second check to mean anything: it is the
only byte that varies between runs, and a timestamp says nothing about the
brief.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
BRIEF = REPO / "outreach" / "pit_loss_rule_brief.pdf"
GENERATOR = REPO / "scripts" / "make_outreach_brief.py"


def _module():
    if not GENERATOR.exists():
        pytest.skip("scripts/make_outreach_brief.py not present")
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    spec = importlib.util.spec_from_file_location("_outreach_brief", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def facts() -> dict:
    return _module()._facts()


def test_the_correlation_matches_the_formal_test(facts: dict) -> None:
    """The page quotes r and its interval; both come from one artifact."""
    pandas = pytest.importorskip("pandas")
    tests = pandas.read_csv(
        REPO / "data" / "derived" / "cross_series" / "formal_tests.csv"
    )
    row = tests[tests["result"].str.contains(r"\(r\)", regex=True)].iloc[0]
    assert facts["r"] == pytest.approx(float(row["estimate"]))
    assert facts["ci"] == (
        pytest.approx(float(row["ci_low"])),
        pytest.approx(float(row["ci_high"])),
    )


def test_the_scope_matches_the_multistop_plans(facts: dict) -> None:
    pandas = pytest.importorskip("pandas")
    plans = pandas.read_csv(
        REPO / "data" / "derived" / "endurance" / "multistop_plans.csv"
    )
    limited = plans["optimal_stops"] != plans["min_stops"]
    assert facts["n_race_seasons"] == len(plans)
    assert facts["n_limited"] == int(limited.sum())
    assert len(facts["by_class"]) == plans.groupby(
        ["series", "car_class"]
    ).ngroups


def test_the_rule_the_brief_states_still_holds(facts: dict) -> None:
    """Above the edge, nothing is tyre-limited. The brief says so in bold."""
    assert facts["n_limited_above"] == 0, (
        "the brief states that no race-season above the cheap-stop edge is "
        f"tyre-limited, and {facts['n_limited_above']} now is. The claim, not "
        "the wording, has to change."
    )
    assert facts["n_above"] > 0


def test_the_thin_evidence_the_brief_admits_is_still_the_thin_evidence(
    facts: dict,
) -> None:
    """The page volunteers that one race sets the edge. It has to be true."""
    assert facts["runner_up"] < facts["edge"]
    assert 0 < facts["drop_pct"] < 100
    report = (REPO / "reports" / "cross_series" / "thin_evidence.md").read_text(
        encoding="utf-8"
    )
    assert f"{facts['edge']:.1f}" in report, (
        "the brief and thin_evidence.md disagree about the cheap-stop edge"
    )


def test_the_committed_brief_is_not_stale() -> None:
    """A regenerated brief must equal the one that would be attached to an email."""
    if not BRIEF.exists():
        pytest.skip("the brief has not been generated")
    before = BRIEF.read_bytes()
    result = subprocess.run(
        [sys.executable, str(GENERATOR)],
        cwd=REPO, capture_output=True, text=True,
    )
    assert result.returncode == 0, f"the generator failed:\n{result.stderr}"
    assert BRIEF.read_bytes() == before, (
        "outreach/pit_loss_rule_brief.pdf is out of date with the artifacts. "
        "Run scripts/make_outreach_brief.py and commit the result before "
        "sending it to anyone."
    )


def test_the_brief_is_one_page() -> None:
    """Asked for one page. The generator refuses to overflow; this confirms it."""
    if not BRIEF.exists():
        pytest.skip("the brief has not been generated")
    body = BRIEF.read_bytes()
    pages = body.count(b"/Type /Page") - body.count(b"/Type /Pages")
    assert pages == 1, f"the brief is {pages} pages"
