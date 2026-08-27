"""The F1 core scope: structurally sound offline, and true to the real calendar.

This module exists because the scope was four circuits for most of the
project's life, and widening it to the whole calendar exposed a defect that had
been one race away from firing.

**The Madrid trap.** The scope used to map an event *name* to a circuit slug:
``("Spanish", "barcelona")``. In 2026 the Spanish Grand Prix moves to **Madrid**
while Barcelona keeps a round of its own under a new name. FastF1's fuzzy
matcher resolves "Spanish" to the Spanish Grand Prix correctly — and the
pipeline would then have written Madrid's laps to ``laps_2026_barcelona.csv``.
A different track, the same key, no error, and a degradation model that pools
two circuits into one fit. The race is scheduled for 2026-09-13.

The lesson generalises past this one case: a circuit is not a property of an
event name, it is a property of an event *in a season*. The scope is keyed that
way now, and the checks below are what keep it honest.

The network check is separated and skipped when FastF1 cannot reach the
schedule, so the suite still passes offline — but when it does run it is the
only thing that can catch the *next* Madrid.
"""

from __future__ import annotations

import collections

import pytest

from src.ingestion.config import (
    CIRCUITS,
    PRE_ERA_SEASONS,
    RACES,
    SEASONS,
    _SEASON_EVENTS,
    breadth_key,
)


def test_every_season_has_a_calendar() -> None:
    """A season in SEASONS with no events is a silent hole in the scope.

    ``SEASONS`` is rolling — it extends to the current year automatically — so
    a new season arrives with no calendar until someone adds one. That should
    be visible, because every downstream model quietly narrows when it happens.
    """
    missing = [s for s in SEASONS if not _SEASON_EVENTS.get(s)]
    assert not missing, (
        f"seasons in scope with no calendar: {missing}. Add their rounds to "
        "_SEASON_EVENTS, or narrow SEASONS."
    )


def test_no_season_files_two_events_under_one_circuit() -> None:
    """Two rounds at one circuit in one season would collide on the file name.

    Derived files are named ``laps_{season}_{circuit}.csv``, so a duplicate key
    means the second ingestion silently overwrites the first. This is the
    check that makes the Madrid split *necessary* rather than merely tidy: in
    2026 Barcelona and Madrid are two rounds in Spain, and mapping both to
    ``barcelona`` would lose one of them entirely.
    """
    for season, events in _SEASON_EVENTS.items():
        counts = collections.Counter(circuit for _, circuit in events)
        duplicated = {c: n for c, n in counts.items() if n > 1}
        assert not duplicated, (
            f"{season}: {duplicated} — two rounds share a circuit slug, so one "
            f"would overwrite the other's derived file"
        )


def test_madrid_and_barcelona_are_separate_circuits() -> None:
    """The specific defect, pinned so it cannot come back.

    Named explicitly rather than left to the general duplicate check, because
    the general check only fires once both rounds are in the calendar. This one
    states the fact: the 2026 Spanish Grand Prix is not run at Barcelona.
    """
    events_2026 = dict(_SEASON_EVENTS.get(2026, ()))
    if "Spanish Grand Prix" not in events_2026:
        pytest.skip("2026 calendar not in scope")
    assert events_2026["Spanish Grand Prix"] == "madrid", (
        "the 2026 Spanish Grand Prix is at Madrid; mapping it to Barcelona "
        "files two different circuits under one key"
    )
    assert events_2026.get("Barcelona Grand Prix") == "barcelona"


def test_race_identities_are_unique() -> None:
    """(season, circuit) is the identity every derived artifact groups on."""
    counts = collections.Counter((r.season, r.circuit) for r in RACES)
    duplicated = [key for key, n in counts.items() if n > 1]
    assert not duplicated, f"duplicate race identities: {duplicated}"


def test_the_scope_is_the_whole_calendar_not_a_sample() -> None:
    """The core scope must not silently shrink back toward a handful of tracks.

    For most of this project's life it was four circuits — Monaco, Singapore,
    Barcelona, Suzuka — while the Kaggle breadth layer carried 35. Four circuits
    received per-compound degradation with cluster-robust intervals, a
    neutralisation posterior, track position, the simulator and the decision
    audits; the other 31 received two numbers each. Nothing technical justified
    it: a round costs about 40 seconds to fetch, once.

    This asserts the shape of the fix rather than an exact count, so adding or
    losing a round does not fail the suite for no reason.
    """
    assert len(CIRCUITS) >= 20, (
        f"the core scope is down to {len(CIRCUITS)} circuits ({sorted(CIRCUITS)}). "
        "It covers the whole calendar by design; a narrower scope means most "
        "circuits get a fraction of the treatment the rest get."
    )
    for season in PRE_ERA_SEASONS:
        rounds = len(_SEASON_EVENTS.get(season, ()))
        assert rounds >= 20, (
            f"{season} carries only {rounds} rounds; a completed F1 season has "
            "at least 20"
        )


def test_breadth_aliases_point_at_real_breadth_circuits() -> None:
    """The two F1 layers measure the same net slope from independent sources.

    That cross-check only works if the keys line up, and they were chosen years
    apart: the core calls Barcelona ``barcelona`` and the Kaggle layer calls it
    ``catalunya``. An alias that points at nothing silently drops the circuit
    from every comparison instead of failing.
    """
    pd = pytest.importorskip("pandas")
    from src.ingestion.config import F1_DERIVED_DIR

    history = F1_DERIVED_DIR / "history_degradation.csv"
    if not history.exists():
        pytest.skip("breadth layer not materialised")
    known = set(pd.read_csv(history)["circuit"])

    from src.ingestion.config import BREADTH_CIRCUIT_ALIASES

    dangling = {
        core: mapped
        for core, mapped in BREADTH_CIRCUIT_ALIASES.items()
        if mapped not in known
    }
    assert not dangling, (
        f"aliases pointing at circuits the breadth layer does not have: "
        f"{dangling}. Known: {sorted(known)}"
    )


def test_breadth_key_is_identity_where_the_layers_already_agree() -> None:
    """No alias needed for monaco, monza, spa, suzuka and the rest."""
    assert breadth_key("monaco") == "monaco"
    assert breadth_key("barcelona") == "catalunya"


@pytest.mark.network
def test_the_frozen_calendar_still_matches_the_real_one() -> None:
    """The only check that can catch the *next* Madrid.

    The scope is frozen in code on purpose — derived file names depend on it,
    and a scope that changes because an upstream calendar was revised is not a
    scope. The cost of freezing is that it can drift out of date, so this is
    what converts a real calendar change into a failing test and a deliberate
    edit, rather than into a wrong file name.

    Skipped when FastF1 cannot reach the network, so the suite stays offline.
    """
    fastf1 = pytest.importorskip("fastf1")
    from src.ingestion.config import CACHE_DIR

    try:
        fastf1.Cache.enable_cache(str(CACHE_DIR))
        schedules = {
            season: fastf1.get_event_schedule(season, include_testing=False)
            for season in _SEASON_EVENTS
        }
    except Exception as exc:  # offline, or the upstream API is down
        pytest.skip(f"F1 schedule unavailable: {exc}")

    drifted = []
    for season, events in _SEASON_EVENTS.items():
        real = set(schedules[season]["EventName"])
        scoped = {name for name, _ in events}
        for name in sorted(scoped - real):
            drifted.append(f"{season}: {name!r} is in the scope but not the calendar")
        for name in sorted(real - scoped):
            drifted.append(f"{season}: {name!r} is on the calendar but not in scope")

    assert not drifted, (
        "the frozen calendar has drifted from the real one:\n  "
        + "\n  ".join(drifted)
    )
