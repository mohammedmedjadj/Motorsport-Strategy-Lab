"""The Streamlit demo, driven headlessly.

Until this existed, "the demo works" was the one claim in this repository
backed by nothing: ``demo/app.py`` was the only module no test imported, so a
rename in ``src/simulator`` could break the shop window while all 250 tests
stayed green. ``AppTest`` runs the real script in-process and lets us press the
real button, so a broken demo now fails the suite like anything else.

Draw counts are set to the smallest option in each panel: this is testing that
the wiring holds and the recommendation is well-formed, not re-testing the
estimators, which have their own suites.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip(
    "streamlit",
    reason="streamlit is a demo-only dependency (pip install -r demo/requirements.txt)",
)

from streamlit.testing.v1 import AppTest  # noqa: E402

#: Absolute: ``AppTest.from_file`` resolves relative paths against the *caller*
#: file, i.e. against tests/, not against the repository root.
APP = str(Path(__file__).resolve().parents[1] / "demo" / "app.py")
TIMEOUT = 600  # the endurance panels fit a race model before they can render


def _app(series: str) -> AppTest:
    """The demo, switched to one series' panel."""
    at = AppTest.from_file(APP, default_timeout=TIMEOUT).run()
    assert not at.exception, [str(e.value) for e in at.exception]
    at.sidebar.radio[0].set_value(series).run()
    assert not at.exception, [str(e.value) for e in at.exception]
    return at


def _simulate(at: AppTest) -> AppTest:
    """Press the panel's Simulate button and re-run."""
    button = next(b for b in at.button if b.label == "Simulate")
    button.click().run()
    assert not at.exception, [str(e.value) for e in at.exception]
    return at


def test_every_class_is_offered_separately() -> None:
    """No two classes share a panel.

    The unit is the class, not the series: IMSA runs GTP, GTD and GTD PRO at
    the same rounds and their measured tyre-change premiums are 8.7 s, 17.6 s
    and 16.9 s. A panel keyed on series alone would show one class's model
    under another's name, which is the same pooling error this project has
    already had to correct in the artifacts twice.
    """
    at = AppTest.from_file(APP, default_timeout=TIMEOUT).run()
    options = at.sidebar.radio[0].options
    assert options == [
        "Formula 1",
        "WEC — Hypercar",
        "IMSA — GTP",
        "IMSA — GTD (GT3 Pro/Am)",
        "IMSA — GTD PRO (GT3 all-pro)",
        "ELMS — LMP2",
        "ELMS — LMP2 Pro/Am",
    ]


def test_f1_panel_produces_a_ranked_recommendation() -> None:
    at = _simulate(_app("Formula 1"))
    labels = [m.label for m in at.metric]
    assert "P(best) pit lap" in labels
    table = at.dataframe[-1].value
    assert set(table.columns) >= {"Candidate", "Median (s)", "P(best)"}
    assert len(table) > 1
    # A probability distribution over candidates, so it must sum to ~100%.
    assert table["P(best)"].sum() == pytest.approx(100.0, abs=1.0)


def test_f1_excludes_no_stop_until_two_dry_compounds_have_been_used() -> None:
    """F1's sporting regulations require two different dry compounds in a dry
    race. The engine optimises time and knows nothing about that, so the demo
    has to enforce it: before the box is ticked, running to the flag is a
    disqualification rather than a strategy, and the new set must differ from
    the current one.
    """
    at = _simulate(_app("Formula 1"))
    candidates = set(at.dataframe[-1].value["Candidate"])
    assert "No stop" not in candidates
    current = next(s for s in at.sidebar.selectbox if s.label == "Current compound")
    target = next(s for s in at.sidebar.selectbox if s.label == "Compound if we stop")
    assert current.value not in target.options

    ticked = next(c for c in at.sidebar.checkbox if "Two dry compounds" in c.label)
    at = _simulate(ticked.set_value(True).run())
    assert "No stop" in set(at.dataframe[-1].value["Candidate"])


@pytest.mark.parametrize(
    "series",
    ["WEC — Hypercar", "IMSA — GTP", "IMSA — GTD (GT3 Pro/Am)", "ELMS — LMP2"],
)
def test_endurance_panels_report_a_measured_model_and_a_full_race_plan(series: str) -> None:
    at = _simulate(_app(series))
    labels = [m.label for m in at.metric]
    # The measured card comes first: nothing in an endurance panel is assumed.
    for label in ("Green pace", "Pit loss", "Fuel range", "Degradation"):
        assert label in labels
    assert "P(best) next stop" in labels
    # ... and the exact dynamic program is shown alongside the simulation.
    assert "Optimal stops" in labels and "Fuel-minimum stops" in labels

    plans = at.dataframe[-1].value
    assert set(plans["Plan"]) == {"Optimal plan", "Fuel-minimum plan"}


@pytest.mark.parametrize("series", ["WEC — Hypercar", "IMSA — GTP"])
def test_endurance_candidates_never_exceed_the_fuel_range(series: str) -> None:
    """Running the tank dry is not a strategy, so no candidate stop may fall
    beyond the lap the fuel clock allows."""
    at = _simulate(_app(series))
    fuel_range = int(next(m for m in at.metric if m.label == "Fuel range").value.split()[0])
    current_lap = next(s for s in at.sidebar.slider if "Current lap" in s.label).value
    since_refuel = next(s for s in at.sidebar.slider if "refuelling" in s.label).value

    candidates = at.dataframe[-2].value["Candidate"]  # -1 is the full-race plan table
    stops = [int(c.split()[1]) for c in candidates if c != "No stop"]
    assert stops, "no stop candidate was offered at all"
    assert max(stops) <= current_lap + (fuel_range - since_refuel)


def test_the_two_endurance_series_do_not_share_a_model() -> None:
    """WEC and IMSA are different neutralisation regimes (44 Safety Cars vs
    none), so the two panels must not be able to show the same race model."""
    wec = _app("WEC — Hypercar")
    imsa = _app("IMSA — GTP")

    def card(at: AppTest) -> dict[str, str]:
        return {m.label: m.value for m in at.metric if m.label in
                ("Green pace", "Pit loss", "Fuel range")}

    assert card(wec) != card(imsa)


# --- the demo must offer everything the project models -----------------------


def test_every_scoped_class_has_a_panel() -> None:
    """The demo is the shop window, and it was showing two of six classes.

    ``available_races`` used to read ``available_events.csv`` — a
    network-derived scoping aid that enumerates one prototype class per series
    and has never known about GTD, GTD PRO, ELMS or LMP2 Pro/Am. So the demo
    silently offered WEC Hypercar and IMSA GTP only, and would have drifted
    again at the next widening.

    The fix was to derive from ``ENDURANCE_SCOPE`` instead, which cannot go
    stale against the scope by construction. This test is the guard that would
    have caught the original defect: every scoped class must be reachable in
    the demo, or the window is describing a smaller project than exists.
    """
    from src.data.endurance_scope import ENDURANCE_SCOPE

    at = AppTest.from_file(APP, default_timeout=TIMEOUT).run()
    assert not at.exception, [str(e.value) for e in at.exception]
    offered = " | ".join(at.sidebar.radio[0].options)

    scoped = {(s, cs.car_class) for s, circuits in ENDURANCE_SCOPE.items()
              for cs in circuits}
    missing = [
        f"{series}/{car_class}" for series, car_class in sorted(scoped)
        if series.upper() not in offered.upper()
        or car_class.upper().replace("GTDPRO", "GTD PRO") not in offered.upper()
    ]
    assert not missing, (
        f"scoped classes with no demo panel: {missing}. The demo derives its "
        "race list from the scope, so a new class needs a panel or it is "
        "modelled and invisible."
    )
    # F1 plus one panel per endurance class.
    assert len(at.sidebar.radio[0].options) == 1 + len(scoped)


def test_available_races_covers_the_whole_scope() -> None:
    """The demo's race list must be the scope, not a subset of it.

    Checked separately from the panel test because the two failure modes are
    different: a class can have a panel that then offers no races, which looks
    like a data problem and is really a catalogue one.
    """
    from src.data.endurance_scope import scoped_race_seasons
    from src.simulator.endurance_models import available_races

    races = available_races()
    scoped = {(s, y, e, c) for s, e, c, y in scoped_race_seasons()}
    offered = set(
        zip(races["series"], races["year"], races["event"], races["car_class"])
    )
    assert offered == scoped, (
        f"offered but not scoped: {sorted(offered - scoped)[:3]}; "
        f"scoped but not offered: {sorted(scoped - offered)[:3]}"
    )
