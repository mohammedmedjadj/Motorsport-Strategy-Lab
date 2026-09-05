"""What goes into a DOI cannot be corrected afterwards.

`.zenodo.json` is read once, at the moment a tagged release is archived, and
whatever it says then is what the permanent record says. Every other document
here can be fixed with a commit. This one cannot.

So the numbers in its abstract are recomputed from the committed artifacts and
required to appear in it, the same way `tests/test_paper_claims.py` guards the
reports. Run before tagging.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
DERIVED = REPO / "data" / "derived"
METADATA = REPO / ".zenodo.json"


@pytest.fixture(scope="module")
def zenodo() -> dict:
    if not METADATA.exists():
        pytest.skip(".zenodo.json not present")
    return json.loads(METADATA.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def prose(zenodo: dict) -> str:
    return f"{zenodo['title']} {zenodo['description']}"


def _plans() -> pd.DataFrame:
    frame = pd.read_csv(DERIVED / "endurance" / "multistop_plans.csv")
    frame["tyre_limited"] = frame["optimal_stops"] != frame["min_stops"]
    return frame


def _formal(name: str) -> pd.Series:
    frame = pd.read_csv(DERIVED / "cross_series" / "formal_tests.csv")
    return frame[frame["result"] == name].iloc[0]


def _claims() -> list[tuple[str, str]]:
    """(what the abstract should say, why it matters) computed fresh."""
    plans = _plans()
    loro = pd.read_csv(DERIVED / "endurance" / "endurance_degradation_loro.csv")
    mean = loro[loro["held_out_season"].astype(str) == "MEAN"].dropna(
        subset=["r2_within"]
    )
    f1 = pd.read_csv(DERIVED / "f1" / "systematic_audit.csv")
    endurance = pd.read_csv(DERIVED / "endurance" / "systematic_audit.csv")
    edge = plans.loc[plans["tyre_limited"], "pit_loss_s"].max()
    diff = _formal("GT3 minus prototype")
    correlation = _formal("pit loss vs tyre-limited share (r)")
    late = f1[f1["delta_laps"] > 1]

    return [
        (f"{len(f1) + len(endurance):,}", "replayed decisions"),
        (f"{len(mean)} circuit-classes", "transfer scope"),
        (f"only {int((mean['r2_within'] > 0.2).sum())} reach", "how few transfer"),
        (f"{len(plans)} race-seasons", "endurance scope"),
        (f"&minus;{abs(correlation['estimate']):.3f}", "the pit-loss correlation"),
        (f"{int((plans['pit_loss_s'] > edge).sum())} race-seasons above",
         "races above the cheap-stop edge"),
        (f"{edge:.1f}&nbsp;s", "the cheap-stop edge itself"),
        (f"{diff['estimate']:+.3f}", "the transfer difference"),
        (f"[{diff['ci_low']:+.3f}, {diff['ci_high']:+.3f}]", "its interval"),
        (f"p = {float(diff['p_value']):.4f}", "its permutation p-value"),
        (f"{100 * len(late) / len(f1):.0f}% of Formula 1", "the late-stop share"),
        (f"median of {late['delta_laps'].median():.0f} laps", "how late"),
    ]


@pytest.mark.parametrize(
    ("value", "what"), _claims(), ids=[what for _, what in _claims()]
)
def test_the_abstract_states_the_current_figure(
    prose: str, value: str, what: str
) -> None:
    assert value in prose, (
        f"the Zenodo abstract does not state the current figure for {what} "
        f"({value}). A DOI is permanent: whatever this file says when the "
        "release is tagged is what the record says forever."
    )


def test_the_licence_matches_the_repository(zenodo: dict) -> None:
    """A wrong licence in the deposit is a legal claim, not a typo."""
    licence = (REPO / "LICENSE").read_text(encoding="utf-8", errors="replace")
    assert zenodo["license"] == "cc-by-nc-sa-4.0", (
        f"the deposit declares {zenodo['license']!r}"
    )
    assert "NonCommercial" in licence and "ShareAlike" in licence, (
        "LICENSE is not the CC BY-NC-SA text the deposit declares"
    )


def test_the_related_dois_are_the_two_verified_ones(zenodo: dict) -> None:
    """Only references checked against the real publication record.

    The project's own notes once carried five candidate papers presented as
    established. Two survived verification. A deposit citing a paper that does
    not exist as described is worse than one citing nothing.
    """
    identifiers = {r["identifier"] for r in zenodo.get("related_identifiers", [])}
    assert "10.1016/j.ejor.2024.07.011" in identifiers, "Aguad & Thraves missing"
    assert "arXiv:2512.00640" in identifiers, "Cappello & Hoegh missing"
    dois = {i for i in identifiers if i.startswith("10.") or i.startswith("arXiv")}
    assert len(dois) == 2, (
        f"the deposit cites {len(dois)} works but only two have been verified "
        f"against the publication record: {sorted(dois)}"
    )
