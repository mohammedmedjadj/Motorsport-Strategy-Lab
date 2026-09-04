"""FastF1 returns a different race when the one you asked for does not exist.

Asking for the 2018 Miami Grand Prix returns the **Italian Grand Prix at
Monza**. Asking for the cancelled 2020 Monaco Grand Prix returns the same.
FastF1 logs a warning and hands back a session, so an analysis that trusts it
silently studies Monza believing it is Monaco.

`event_matches_request` is the guard. Its first version compared event *names*,
which caught the substitutions and also rejected four real races: a Grand Prix
can be renamed without moving, and Mexico ran as the "Mexican Grand Prix"
through 2020 before becoming the "Mexico City Grand Prix". Those four sat in a
skip list of thirty-one, under a heading calling them COVID cancellations, and
nobody was going to read far enough to notice two different kinds of miss had
been folded together.

**A rename keeps the location; a substitution changes it.** That is the property
the guard now tests, and these cases are the ones that taught it.
"""

from __future__ import annotations

import pytest

from src.ingestion.config import CIRCUIT_LOCATIONS, CIRCUITS
from src.ingestion.loader import event_matches_request

#: (requested, resolved name, resolved location, circuit, should match, why)
CASES = [
    ("Mexico City Grand Prix", "Mexican Grand Prix", "Mexico City",
     "mexico_city", True, "renamed in 2021, same race at the same place"),
    ("São Paulo Grand Prix", "Brazilian Grand Prix", "São Paulo",
     "interlagos", True, "renamed in 2021, same race at the same place"),
    ("Miami Grand Prix", "Italian Grand Prix", "Monza",
     "miami", False, "Miami did not exist in 2018; FastF1 substituted Monza"),
    ("Monaco Grand Prix", "Italian Grand Prix", "Monza",
     "monaco", False, "Monaco 2020 was cancelled; FastF1 substituted Monza"),
    ("Monaco Grand Prix", "Monaco Grand Prix", "Monte Carlo",
     "monaco", True, "the ordinary case, with a location spelling variant"),
    ("Spanish Grand Prix", "Spanish Grand Prix", "Madrid",
     "madrid", True, "the 2026 move: same name, new circuit, matched by name"),
]


@pytest.mark.parametrize(
    ("requested", "resolved", "location", "circuit", "expected", "why"),
    CASES,
    ids=[f"{case[3]}-{'match' if case[4] else 'reject'}" for case in CASES],
)
def test_event_matching(
    requested: str, resolved: str, location: str, circuit: str,
    expected: bool, why: str,
) -> None:
    assert event_matches_request(requested, resolved, location, circuit) is expected, why


def test_a_substitution_is_rejected_without_location_too() -> None:
    """The name check still stands alone when no location is available.

    Callers that predate the location argument keep working, and they keep the
    protection that matters most — an unrelated event whose name shares nothing
    with the request.
    """
    assert not event_matches_request("Miami Grand Prix", "Italian Grand Prix")
    assert event_matches_request("Monaco Grand Prix", "Monaco Grand Prix")


def test_every_scoped_circuit_has_a_known_location() -> None:
    """A circuit with no location cannot use the location branch at all.

    It would fall back to the name check and quietly lose the protection, which
    is exactly the silent narrowing this project keeps having to find by hand.
    """
    missing = sorted(set(CIRCUITS) - set(CIRCUIT_LOCATIONS))
    assert not missing, (
        f"circuits in scope with no known location: {missing}. Add them to "
        "CIRCUIT_LOCATIONS, or a renamed event at one of them will be rejected "
        "as a race that never happened."
    )


def test_locations_are_not_shared_between_circuits() -> None:
    """Two circuits claiming one location would let a substitution through.

    Three US circuits and two Spanish ones sit in this scope, so the country is
    not usable as a key and the location has to stay unique.
    """
    seen: dict[str, str] = {}
    clashes = []
    for circuit, locations in CIRCUIT_LOCATIONS.items():
        for location in locations:
            key = location.casefold()
            if key in seen and seen[key] != circuit:
                clashes.append(f"{location!r}: {seen[key]} and {circuit}")
            seen[key] = circuit
    assert not clashes, f"locations claimed by more than one circuit: {clashes}"
