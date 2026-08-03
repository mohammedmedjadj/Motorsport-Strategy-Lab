"""Per-decision retrospective audit for WEC and IMSA — the endurance analogue
of ``src/audit/cases.py``, replaying real stop-timing decisions through
``src.simulator.endurance.simulate`` instead of the F1 engine.

Case selection rationale (the endurance equivalent of the note validated with
Mohammed at the F1 Phase 5 gate): F1's five cases draw on public, well-known
strategy narratives — Verstappen's Barcelona cover, Sainz's Singapore SC stop
— that make "was this a good decision" a question with an independently known
answer to check the model against. Neither WEC HYPERCAR nor IMSA GTP racing
carries that kind of public narrative record at this project's scope, so cases
here are instead selected by a measurable criterion applied the same way at
every circuit, not by which race happened to be famous:

- **An opportunistic stop** — pitted on the exact lap a neutralisation (FCY or
  Safety Car) begins, verified from the flag column itself
  (``GF`` the lap before, ``FCY``/``SF`` the lap of the stop). The endurance
  analogue of F1 Case C (Sainz's SC stop): does boxing the instant the caution
  falls actually dominate waiting?
- **A routine stop** — taken under green flag, at a circuit whose degradation
  fit is clearly non-zero, testing whether a real fuel/tyre trade-off lines up
  with the model's recommendation with no neutralisation timing involved.
- Both circuits per series span the range this project has already measured:
  WEC pairs Bahrain (steep, significant slope) with Imola (anomalous negative
  slope); IMSA pairs Road America (significant in every season) with Mosport
  (flat, single-season) — the same contrast the WEC/IMSA Phase 2 reports draw.

Every state (tyre age, laps since refuel, the flag transition, the real stop
lap) is measured from the committed derived laps via ``endurance_case_state``,
never quoted from memory. The studied car in each case is the one that
completed the most laps in its class — this project's standing convention for
"the winner" (``src/audit/endurance_state.py::winning_car``).
"""

from __future__ import annotations

from dataclasses import dataclass

from src.audit.endurance_case_state import (
    build_case_model,
    load_case_laps,
    race_length,
    state_at,
)
from src.simulator.endurance import EnduranceRaceModel, EnduranceScenario


@dataclass(frozen=True)
class EnduranceAuditCase:
    """One real endurance stop decision plus the model scenario that replays it."""

    case_id: str
    series: str
    title: str
    car: str
    real_decision: str
    question: str
    scenario: EnduranceScenario
    model: EnduranceRaceModel
    real_pit_lap: int


def _case(
    case_id: str,
    series: str,
    year: int,
    event: str,
    car_class: str,
    car: str,
    real_pit_lap: int,
    title: str,
    real_decision: str,
    question: str,
) -> EnduranceAuditCase:
    laps = load_case_laps(series, year, event, car_class)
    current_lap = real_pit_lap - 1
    state = state_at(laps, car, current_lap)
    total_laps = race_length(laps, car)
    model = build_case_model(series, year, event, car_class)
    scenario = EnduranceScenario(
        current_lap=current_lap,
        total_laps=total_laps,
        tyre_age=state.tyre_age,
        laps_since_refuel=state.laps_since_refuel,
    )
    return EnduranceAuditCase(
        case_id=case_id, series=series, title=title, car=car,
        real_decision=real_decision, question=question,
        scenario=scenario, model=model, real_pit_lap=real_pit_lap,
    )


def build_wec_cases() -> list[EnduranceAuditCase]:
    cases = []

    # --- W-A: Bahrain 2025 — an opportunistic Safety Car stop -------------
    cases.append(_case(
        "W-A", "wec", 2025, "Bahrain", "HYPERCAR", "009", 216,
        title="Bahrain 2025 — car 009's Safety Car-onset stop (lap 216)",
        real_decision=(
            "Car 009 (this race's class winner by laps completed) pitted lap "
            "216 — the exact lap the flag turned from GF to SF (Safety Car "
            "called) — its ninth and final stop of the race."
        ),
        question=(
            "Does boxing the instant the Safety Car is called dominate the "
            "model's own recommendation, at a circuit (Bahrain) with a steep, "
            "significant degradation slope?"
        ),
    ))

    # --- W-B: Bahrain 2024 — a routine green-flag stop ---------------------
    cases.append(_case(
        "W-B", "wec", 2024, "Bahrain", "HYPERCAR", "15", 125,
        title="Bahrain 2024 — car 15's routine green-flag stop (lap 125)",
        real_decision=(
            "Car 15 (the class winner) pitted lap 125 under green flag — its "
            "fourth of eight stops, with no neutralisation involved."
        ),
        question=(
            "At the circuit with the steepest measured degradation in either "
            "series, does a routine, fuel-clock-driven green-flag stop match "
            "the model's fuel/tyre trade-off?"
        ),
    ))

    # --- W-C: Imola 2024 — an opportunistic SC stop at the anomalous circuit
    cases.append(_case(
        "W-C", "wec", 2024, "Imola", "HYPERCAR", "5", 130,
        title="Imola 2024 — car 5's Safety Car-onset stop (lap 130), the anomalous-slope circuit",
        real_decision=(
            "Car 5 (the class winner) pitted lap 130 — the exact lap the flag "
            "turned from GF to SF — its fifth of seven stops."
        ),
        question=(
            "Imola is the one circuit in scope with a measured negative "
            "degradation slope (Phase 2, reported as anomalous rather than "
            "smoothed over). Does an opportunistic SC stop still read as "
            "correct there, or does the odd slope produce a different verdict?"
        ),
    ))
    return cases


def build_imsa_cases() -> list[EnduranceAuditCase]:
    cases = []

    # --- I-A: Watkins Glen 2024 — an opportunistic FCY stop ----------------
    cases.append(_case(
        "I-A", "imsa", 2024, "Watkins Glen", "GTP", "01", 90,
        title="Watkins Glen 2024 — car 01's FCY-onset stop (lap 90)",
        real_decision=(
            "Car 01 (the class winner) pitted lap 90 — the exact lap the flag "
            "turned from GF to FCY — its fourth of eight stops."
        ),
        question=(
            "IMSA's FCY pace ratio (2.03 at Watkins Glen) is far slower than "
            "an F1 SC; does boxing the instant the yellow falls dominate the "
            "model's recommendation as clearly as that ratio would suggest?"
        ),
    ))

    # --- I-B: Road America 2024 — a routine green-flag stop ----------------
    cases.append(_case(
        "I-B", "imsa", 2024, "Road America", "GTP", "10", 29,
        title="Road America 2024 — car 10's routine green-flag stop (lap 29)",
        real_decision=(
            "Car 10 (the class winner) pitted lap 29 under green flag — its "
            "first of two stops in this 62-lap sprint."
        ),
        question=(
            "Road America has the strongest, most consistently significant "
            "degradation signal of any IMSA circuit in scope. Does a routine "
            "first stop line up with the model's fuel/tyre trade-off here?"
        ),
    ))

    # --- I-C: Mosport 2023 — an opportunistic FCY stop, the flat circuit ---
    cases.append(_case(
        "I-C", "imsa", 2023, "Mosport", "GTP", "10", 85,
        title="Mosport 2023 — car 10's FCY-onset stop (lap 85), the flat-signal circuit",
        real_decision=(
            "Car 10 (the class winner) pitted lap 85 — the exact lap the flag "
            "turned from GF to FCY — its third of three stops."
        ),
        question=(
            "Mosport has only one GTP season and a degradation slope "
            "confidence interval that covers zero (Phase 2's flattest read in "
            "either series). Does the model still recommend the same window "
            "when degradation gives it almost nothing to arbitrate?"
        ),
    ))
    return cases


def build_cases(series: str) -> list[EnduranceAuditCase]:
    """All audit cases for one series ('wec' or 'imsa')."""
    if series == "wec":
        return build_wec_cases()
    if series == "imsa":
        return build_imsa_cases()
    raise ValueError(f"unknown series {series!r}; expected 'wec' or 'imsa'")
