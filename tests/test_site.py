"""The published site must show the same numbers as everything else.

`docs/index.html` is what GitHub Pages serves, and it is the one document here
most likely to be read by someone who reads nothing else. It is also hand-written
HTML, which puts it squarely in the category that has failed repeatedly in this
project: prose carrying numbers that cannot recompute.

Generating the whole page from artifacts would be disproportionate — it is one
page with a dozen quantities. Guarding those quantities is not. So every number
the site states about a result is recomputed here and required to appear on the
page, exactly as `tests/test_paper_claims.py` does for the reports.

The figure directory is guarded too. Pages serves `docs/` as the site root, so
it cannot reference `../reports/figures/`; the images are copied by
`scripts/make_supporting_figures.py`. A copy that nothing refreshes is the
stale-duplicate defect this project has already had once, in
`reports/imsa/gtp/`, and it went unnoticed for three weeks.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
SITE = REPO / "docs" / "index.html"
SITE_FIGURES = REPO / "docs" / "figures"
REPORT_FIGURES = REPO / "reports" / "figures"
DERIVED = REPO / "data" / "derived"


@pytest.fixture(scope="module")
def page() -> str:
    if not SITE.exists():
        pytest.skip("docs/index.html not present")
    return SITE.read_text(encoding="utf-8")


def _plans() -> pd.DataFrame:
    frame = pd.read_csv(DERIVED / "endurance" / "multistop_plans.csv")
    frame["tyre_limited"] = frame["optimal_stops"] != frame["min_stops"]
    return frame


def test_the_site_figures_match_the_generated_ones() -> None:
    """Byte-identical, or the site is showing an older result than the repo."""
    if not SITE_FIGURES.exists():
        pytest.skip("site figures not generated")
    upstream = {p.name: p.read_bytes() for p in REPORT_FIGURES.glob("*.png")}
    published = {p.name: p.read_bytes() for p in SITE_FIGURES.glob("*.png")}

    missing = sorted(set(upstream) - set(published))
    orphaned = sorted(set(published) - set(upstream))
    stale = sorted(
        name for name in set(upstream) & set(published)
        if upstream[name] != published[name]
    )
    assert not missing, (
        f"figures generated but never copied to the site: {missing}. Run "
        "`python scripts/make_supporting_figures.py`."
    )
    assert not orphaned, (
        f"figures on the site that no generator produces: {orphaned}. They "
        "will never update again."
    )
    assert not stale, (
        f"the site is serving older versions of: {stale}. The page and the "
        "repository are showing different results to different readers."
    )


def test_every_image_the_site_references_exists(page: str) -> None:
    """A broken image on the one page most people will actually open."""
    import re

    missing = [
        src for src in re.findall(r'src="([^"]+\.png)"', page)
        if not (SITE / ".." / src).resolve().exists()
    ]
    assert not missing, f"site references images that do not exist: {missing}"


def test_the_site_quotes_the_current_transfer_result(page: str) -> None:
    loro = pd.read_csv(DERIVED / "endurance" / "endurance_degradation_loro.csv")
    mean = loro[loro["held_out_season"].astype(str) == "MEAN"].dropna(
        subset=["r2_within"]
    )
    best = f"+{mean['r2_within'].max():.3f}"
    above = f"{int((mean['r2_within'] > 0.2).sum())} of {len(mean)}"
    for value, what in ((best, "best transfer"), (above, "circuit-classes above 0.2")):
        assert value in page, (
            f"the site does not state the current {what} ({value}). It is the "
            "page a reader who reads nothing else will read."
        )


def test_the_site_quotes_the_current_pit_loss_rule(page: str) -> None:
    plans = _plans()
    by_class = plans.groupby(["series", "car_class"]).agg(
        pit_loss=("pit_loss_s", "median"), share=("tyre_limited", "mean")
    )
    correlation = f"{by_class['pit_loss'].corr(by_class['share']):.3f}".replace("-", "−")
    edge = plans.loc[plans["tyre_limited"], "pit_loss_s"].max()
    above = int((plans["pit_loss_s"] > edge).sum())

    assert correlation in page, f"the site's correlation is stale; it is now {correlation}"
    assert f"{edge:.1f} s" in page, f"the site's cheap-stop edge is stale; it is now {edge:.1f} s"
    assert str(above) in page, f"the site's count above the edge is stale; it is now {above}"


def test_the_site_quotes_the_current_audit_scale(page: str) -> None:
    f1 = pd.read_csv(DERIVED / "f1" / "systematic_audit.csv")
    endurance = pd.read_csv(DERIVED / "endurance" / "systematic_audit.csv")
    total = f"{len(f1) + len(endurance):,}"
    assert total in page, (
        f"the site says a different number of replayed decisions than the "
        f"artifacts hold ({total})"
    )
    assert f"{len(f1)} F1 decisions" in page or f"all {len(f1)} F1" in page, (
        f"the site's F1 decision count is stale; it is now {len(f1)}"
    )


def test_the_site_baseline_table_matches_the_comparison(page: str) -> None:
    """The table that says a rule of thumb beats the optimiser.

    The most quotable claim on the page, so the one most worth pinning.
    """
    frames = [
        pd.read_csv(DERIVED / series / "baseline_comparison.csv")
        for series in ("f1", "endurance")
        if (DERIVED / series / "baseline_comparison.csv").exists()
    ]
    if not frames:
        pytest.skip("baseline comparison not generated")
    scored = pd.concat(frames, ignore_index=True)

    wrong = []
    for series in ("f1", "imsa", "wec", "elms"):
        subset = scored[scored["series"] == series]
        if subset.empty:
            continue
        for column, label in (("model_pit_lap", "optimiser"), ("b1_lap", "B1"),
                              ("b2_lap", "B2"), ("b3_lap", "B3")):
            errors = (subset[column] - subset["real_pit_lap"]).abs().dropna()
            if not len(errors):
                continue
            cell = f'<td class="num">{errors.median():.0f}</td>'
            win = f'<td class="num win">{errors.median():.0f}</td>'
            if cell not in page and win not in page:
                wrong.append(f"{series} {label} = {errors.median():.0f}")
    assert not wrong, (
        f"these baseline results do not appear anywhere in the site's table: "
        f"{wrong}. The page is showing a comparison the data no longer supports."
    )


def test_the_site_states_the_test_count_it_can_back_up(page: str) -> None:
    """A test-count claim that has drifted is worse than no claim.

    Bounded by a relationship rather than a tolerance. The first version allowed
    the claim to sit within 60 of the number of `def test_` lines, and failed
    the moment parameterisation legitimately turned 380 definitions into 446
    collected cases — an arbitrary margin either fires on honest change or never
    fires at all.

    What must hold instead: pytest collects at least one case per test function,
    so a claim *below* the definition count is plainly wrong, and a claim more
    than double it would mean parameterisation had grown past anything this
    suite does. Between those the number is not checkable without running
    pytest, and this file is meant to run in a second.
    """
    import re

    match = re.search(r"(\d{3})\s*</strong>\s*tests|<strong>(\d{3}) tests", page)
    if not match:
        pytest.skip("the site states no test count")
    claimed = int(match.group(1) or match.group(2))
    defined = sum(
        len(re.findall(r"^def test_", path.read_text(encoding="utf-8"), re.M))
        for path in (REPO / "tests").glob("test_*.py")
    )
    assert defined <= claimed <= 2 * defined, (
        f"the site claims {claimed} tests against {defined} test functions. "
        "Collection yields at least one case per function, so a lower claim is "
        "wrong outright and a claim past double means this bound needs "
        "rethinking rather than widening."
    )
