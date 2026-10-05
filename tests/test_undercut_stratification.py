"""The stratified undercut section has to keep agreeing with its own data.

Charles Thraves asked how the rival in the adversarial replay is chosen, and
the answer turned out to be worse than the question assumed: minimising the
absolute position distance has no unique answer for any car that is not leading
the race, because the cars one place ahead and one place behind are both one
place away. Most of the sample is decided by row order.

Two claims came out of that and both are quoted in
``reports/f1/undercut_hypothesis.md``: that the ambiguity covers most decisions,
and that it did not matter because the two roles it chooses between give the
same answer. The second claim is the one doing the defending, and it is exactly
the sort that stops being true quietly when the audit is rerun on more races.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
REPLAY = REPO / "data" / "derived" / "f1" / "undercut_hypothesis.csv"
REPORT = REPO / "reports" / "f1" / "undercut_hypothesis.md"


@pytest.fixture(scope="module")
def replay():
    pandas = pytest.importorskip("pandas")
    if not REPLAY.exists():
        pytest.skip("the undercut replay has not been generated")
    frame = pandas.read_csv(REPLAY)
    for column in ("relation", "realised", "my_position", "rival_position"):
        if column not in frame.columns:
            pytest.skip(f"{column} missing; rerun scripts/run_undercut_hypothesis.py")
    return frame


@pytest.fixture(scope="module")
def report() -> str:
    if not REPORT.exists():
        pytest.skip("the undercut report has not been generated")
    return REPORT.read_text(encoding="utf-8")


def test_the_two_roles_are_both_represented(replay) -> None:
    """A stratification with an empty side says nothing about either."""
    counts = replay["realised"].value_counts()
    assert set(counts.index) == {"rival ahead", "rival behind"}
    assert counts.min() > 30, (
        f"one role has only {counts.min()} decisions, which is too few to "
        "compare against the other: {dict(counts)}"
    )


def test_the_report_quotes_the_tie_count_it_computes(replay, report: str) -> None:
    ties = int((replay["relation"] == "tie").sum())
    assert f"**{ties} of {len(replay)} decisions** are ties" in report, (
        f"the report should say {ties} of {len(replay)} decisions are ties"
    )


def test_only_the_race_leader_has_an_unambiguous_nearest_rival(replay) -> None:
    """The reason the ties dominate, stated as a property rather than a count."""
    decided = replay[replay["relation"] != "tie"]
    assert (decided["my_position"] == 1).all(), (
        "a decision was treated as having an unambiguous nearest rival while "
        "the audited car was not leading. The claim in the report that only the "
        "leader has one would then be wrong."
    )


def test_the_published_verdict_matches_the_sign_of_both_strata(
    replay, report: str
) -> None:
    """The defence rests on the two roles agreeing. If they stop, the text must."""
    medians = replay.groupby("realised")["closed"].median()
    ahead, behind = medians["rival ahead"], medians["rival behind"]
    opposed = min(ahead, behind) < 0 < max(ahead, behind)

    says_opposed = "**The two roles have opposite signs.**" in report
    says_agreed = "**Both roles point the same way" in report

    assert says_opposed != says_agreed, (
        "the report should state exactly one of the two verdicts"
    )
    assert says_opposed == opposed, (
        f"the report says the roles {'disagree' if says_opposed else 'agree'}, "
        f"but the medians are {ahead:+.1f} (rival ahead) and {behind:+.1f} "
        "(rival behind). The conclusion has to follow the data, not the other "
        "way round."
    )


def test_the_stratified_table_matches_the_replay(replay, report: str) -> None:
    """Every number in the table is recomputed, not trusted."""
    for role in ("rival ahead", "rival behind"):
        part = replay[replay["realised"] == role]
        row = re.search(rf"^\| {role} —.*$", report, re.M)
        assert row, f"no table row for {role!r}"
        cells = [cell.strip() for cell in row.group(0).split("|")[1:-1]]
        expected = [
            str(len(part)),
            f"{part['single_car_error'].median():+.0f}",
            f"{part['adversarial_error'].median():+.0f}",
            str(int((part["closed"] > 0).sum())),
            str(int((part["closed"] < 0).sum())),
            str(int((part["closed"] == 0).sum())),
            f"{part['closed'].median():+.1f}",
        ]
        assert cells[1:] == expected, (
            f"the {role!r} row says {cells[1:]} and the replay says {expected}"
        )


def test_the_pooled_result_is_still_in_the_report(report: str) -> None:
    """The stratification was added beside the published result, not over it."""
    assert "## Verdict: the hypothesis is" in report
    assert report.index("## Verdict: the hypothesis is") < report.index(
        "## Stratified by which car commits first"
    ), "the stratification should follow the pooled verdict, not replace it"


def test_thraves_is_credited(report: str) -> None:
    """An outside question that changed a report is part of the record."""
    assert "Charles Thraves" in report
