"""The Phase 5 audit cases: five real decision moments, states rebuilt
from data at runtime.

Case selection rationale (validated with Mohammed at the Phase 5 gate):

- A/B: both sides of the Barcelona 2024 first-stop battle — the leader's
  covering stop that worked and the chaser's extended stint that did not.
- C: the collective "box under the safety car" call at Singapore 2023.
- D: Mercedes' aggressive VSC gamble at Singapore 2023 lap 44 — the most
  discussed strategy call of that season.
- E: Monaco 2024 after the lap-1 red flag — deliberately chosen because
  the model CANNOT see the red-flag free tyre change; it documents the
  model's blind spot instead of hiding it.

Rivals follow their real, historically observed plans (standard audit
convention: the decision under study is ours, the rest of the world is
as it was).
"""

from __future__ import annotations

from dataclasses import dataclass

from src.audit.state import (
    compound_after,
    gap_between,
    load_race_laps,
    pit_stops,
    state_at,
)
from src.simulator.engine import RivalSpec, Scenario


@dataclass(frozen=True)
class AuditCase:
    """One real decision moment plus the model scenario that replays it."""

    case_id: str
    title: str
    slug: str  # race file, e.g. "2024_barcelona"
    driver: str
    real_decision: str
    question: str
    scenario: Scenario
    total_laps: int
    #: The lap actually chosen in reality (0 = stayed out / no further stop).
    real_pit_lap: int = 0


def _rival(laps, name: str, us: str, lap: int, plan_lap: int | None) -> RivalSpec:
    them = state_at(laps, name, lap)
    return RivalSpec(
        name=name,
        gap_s=-gap_between(laps, us, name, lap),  # >0 means rival ahead of us
        compound=them.compound,
        tyre_age=them.tyre_age,
        pit_lap=plan_lap,
        target_compound=compound_after(laps, name, plan_lap) if plan_lap else None,
    )


def build_cases() -> list[AuditCase]:
    cases: list[AuditCase] = []

    # --- A. Barcelona 2024, Verstappen's covering stop (lap 17) -----------
    laps = load_race_laps("2024_barcelona")
    us, lap = "VER", 16
    ver = state_at(laps, us, lap)
    cases.append(
        AuditCase(
            case_id="A",
            real_pit_lap=17,
            title="Barcelona 2024 — Verstappen covers Norris (successful defence)",
            slug="2024_barcelona",
            driver=us,
            real_decision="Pitted lap 17 (SOFT age 20 -> MEDIUM); kept the lead and won.",
            question="Was lap 17 inside the model's optimal window, given Norris's real plan (stop lap 23)?",
            scenario=Scenario(
                circuit="barcelona", current_lap=lap, total_laps=66,
                compound=ver.compound, tyre_age=ver.tyre_age,
                target_compound=compound_after(laps, us, 17),
                rivals=(_rival(laps, "NOR", us, lap, 23),),
            ),
            total_laps=66,
        )
    )

    # --- B. Barcelona 2024, Norris's extended stint (the failed overcut) --
    us = "NOR"
    nor = state_at(laps, us, lap)
    cases.append(
        AuditCase(
            case_id="B",
            real_pit_lap=23,
            title="Barcelona 2024 — Norris's extended stint (failed overcut)",
            slug="2024_barcelona",
            driver=us,
            real_decision="Stayed out until lap 23 on SOFT (to age 23); rejoined behind and finished 2nd, +2.2s.",
            question="Did staying out to lap 23 ever look optimal against Verstappen's real lap-17 stop?",
            scenario=Scenario(
                circuit="barcelona", current_lap=lap, total_laps=66,
                compound=nor.compound, tyre_age=nor.tyre_age,
                target_compound=compound_after(laps, us, 23),
                rivals=(_rival(laps, "VER", us, lap, 17),),
            ),
            total_laps=66,
        )
    )

    # --- C. Singapore 2023, the lap-20 safety car: leader's call ----------
    laps = load_race_laps("2023_singapore")
    us, lap = "SAI", 19
    sai = state_at(laps, us, lap)
    cases.append(
        AuditCase(
            case_id="C",
            real_pit_lap=20,
            title="Singapore 2023 — Sainz boxes under the lap-20 safety car",
            slug="2023_singapore",
            driver=us,
            real_decision="Pitted lap 20 under SC (MEDIUM age 20 -> HARD), as did the whole leading group; won the race.",
            question="Does the model confirm that stopping immediately under the SC dominated staying out?",
            scenario=Scenario(
                circuit="singapore", current_lap=lap, total_laps=62,
                compound=sai.compound, tyre_age=sai.tyre_age,
                target_compound=compound_after(laps, us, 20),
                rivals=(
                    _rival(laps, "RUS", us, lap, 20),
                    _rival(laps, "NOR", us, lap, 20),
                ),
                ongoing=("SC", 0),
            ),
            total_laps=62,
        )
    )

    # --- D. Singapore 2023, Mercedes' lap-44 VSC gamble (Russell) ---------
    us, lap = "RUS", 43
    rus = state_at(laps, us, lap)
    cases.append(
        AuditCase(
            case_id="D",
            real_pit_lap=44,
            title="Singapore 2023 — Mercedes' VSC gamble (Russell, lap 44)",
            slug="2023_singapore",
            driver=us,
            real_decision="Pitted lap 44 under VSC (HARD age 24 -> MEDIUM), dropping P2 -> P4 to attack; caught the leaders but crashed on the last lap fighting for the podium.",
            question="Was surrendering track position for fresh mediums time-optimal, and what does P(ahead) say about the win chance it bought?",
            scenario=Scenario(
                circuit="singapore", current_lap=lap, total_laps=62,
                compound=rus.compound, tyre_age=rus.tyre_age,
                target_compound=compound_after(laps, us, 44),
                rivals=(
                    _rival(laps, "SAI", us, lap, None),  # leaders stayed out
                    _rival(laps, "NOR", us, lap, None),
                ),
                ongoing=("VSC", 0),
                include_no_stop=True,
            ),
            total_laps=62,
        )
    )

    # --- E. Monaco 2024 — the model's declared blind spot -----------------
    laps = load_race_laps("2024_monaco")
    us, lap = "LEC", 40
    lec = state_at(laps, us, lap)
    cases.append(
        AuditCase(
            case_id="E",
            title="Monaco 2024 — Leclerc mid-race (the model's blind spot)",
            slug="2024_monaco",
            driver=us,
            real_decision="Nobody pitted for the entire race: the lap-1 red flag allowed a free tyre change, and Monaco track position beats any pace gain. Leclerc won without stopping.",
            question="What does a time-only model recommend here, and why must its answer be read as a documented limitation rather than advice?",
            scenario=Scenario(
                circuit="monaco", current_lap=lap, total_laps=78,
                compound=lec.compound, tyre_age=lec.tyre_age,
                target_compound="HARD",
                rivals=(_rival(laps, "PIA", us, lap, None),),
                include_no_stop=True,
            ),
            total_laps=78,
        )
    )
    return cases
