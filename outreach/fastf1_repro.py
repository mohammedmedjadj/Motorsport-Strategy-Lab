"""Self-contained reproduction for the FastF1 event-substitution issue.

No project code. Run it against a clean environment:

    pip install fastf1
    python outreach/fastf1_repro.py

Expected output: three requested events that did not run in the requested
season, each returning a different race with only a warning.
"""

from __future__ import annotations

import fastf1

CASES = [
    (2018, "Miami Grand Prix", "Miami was first run in 2022"),
    (2020, "Monaco Grand Prix", "Monaco 2020 was cancelled"),
    (2018, "Las Vegas Grand Prix", "Las Vegas was first run in 2023"),
    # Control: a race that did run, and a rename that should still resolve.
    (2024, "Monaco Grand Prix", "control — this one exists"),
    (2018, "Mexico City Grand Prix", "renamed in 2021; same race, same place"),
]


def main() -> None:
    print(f"fastf1 {fastf1.__version__}\n")
    print(f"{'requested':38s} {'returned':26s} {'location':16s} note")
    for season, requested, note in CASES:
        try:
            session = fastf1.get_session(season, requested, "R")
            event = session.event
            print(
                f"{season} {requested:33s} {str(event['EventName'])[:24]:26s} "
                f"{str(event['Location'])[:14]:16s} {note}"
            )
        except Exception as exc:  # noqa: BLE001 — the point is what does NOT raise
            print(f"{season} {requested:33s} raised {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
