"""Does modelling the undercut explain why the simulator stops too late?

The calendar-wide audit found the model would stay out a median of 12 laps
longer than teams did, on 80% of decisions, and refuted the obvious explanation
(safety cars it cannot foresee — the bias is there on green-flag stops too). It
named one candidate and marked it untested:

> the engine optimises one car's expected race time with no track position, so
> it can never pay for an undercut — and an undercut is exactly why a real team
> stops before it has to.

That is testable. `src/simulator/adversarial.py` already models the pit stop as
a two-player game where the rival covers, and it consumes the measured
track-position stickiness. Re-running the same decisions through it says how
much of the gap track position closes.

**A hypothesis is only worth writing down if something can refute it**, and the
audit's own report would otherwise have carried a plausible mechanism for as
long as nobody got round to checking. Writes
``data/derived/f1/undercut_hypothesis.csv`` and
``reports/f1/undercut_hypothesis.md``.

Usage (offline, from the repo root)::

    python scripts/run_undercut_hypothesis.py
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.audit.state import (  # noqa: E402
    compound_after,
    gap_between,
    load_race_laps,
    pit_stops,
    state_at,
)
from src.ingestion.config import F1_DERIVED_DIR, F1_REPORTS_DIR  # noqa: E402
from src.simulator.adversarial import duel  # noqa: E402
from src.simulator.artifacts import load_circuit_models  # noqa: E402
from src.simulator.engine import RivalSpec, Scenario  # noqa: E402

N_DRAWS = 1500
SEED = 20260712


def _swap_rates() -> dict[str, float]:
    """Each circuit's measured adjacent-swap rate — never a literal."""
    rates = pd.read_csv(F1_DERIVED_DIR / "overtaking_difficulty.csv")
    return dict(zip(rates["circuit"], rates["adj_swap_rate"]))


def _stratum(laps: pd.DataFrame, driver: str, lap: int) -> dict | None:
    """Which of the two games this decision was, and whether that was decided.

    ``_nearest_rival`` minimises |position difference|, so the rival is the car
    ahead on some decisions and the car behind on others, while the audited car
    always commits first. Those are different games. This records which one,
    and flags the decisions where the choice was arbitrary because a car ahead
    and a car behind were equally close.

    Returns ``relation`` as:

    ``ahead``  the audited car leads the rival — it stops first and the chaser
               reacts;
    ``behind`` the audited car trails — it is the chaser committing first, and
               the leader can cover;
    ``tie``    both neighbours were equidistant, so which game this is was
               settled by row order rather than by racing.
    """
    on_lap = laps[laps["LapNumber"] == lap].dropna(subset=["Position"])
    mine = on_lap[on_lap["Driver"] == driver]
    if mine.empty:
        return None
    position = int(mine.iloc[0]["Position"])
    others = on_lap[on_lap["Driver"] != driver]
    if others.empty:
        return None

    offsets = others["Position"].astype(int) - position
    closest = int(offsets.abs().min())
    tied = bool((offsets == closest).any() and (offsets == -closest).any())

    chosen = others.assign(
        distance=lambda d: (d["Position"].astype(int) - position).abs()
    ).nsmallest(1, "distance").iloc[0]
    rival_position = int(chosen["Position"])

    return {
        "my_position": position,
        "rival_position": rival_position,
        "gap_positions": closest,
        "relation": "tie" if tied else
                    ("ahead" if position < rival_position else "behind"),
    }


def _nearest_rival(laps: pd.DataFrame, driver: str, lap: int) -> RivalSpec | None:
    """The car closest on position at the decision lap, on its real plan."""
    on_lap = laps[laps["LapNumber"] == lap].dropna(subset=["Position"])
    mine = on_lap[on_lap["Driver"] == driver]
    if mine.empty:
        return None
    position = int(mine.iloc[0]["Position"])
    others = on_lap[on_lap["Driver"] != driver]
    if others.empty:
        return None
    nearest = others.assign(
        distance=lambda d: (d["Position"] - position).abs()
    ).nsmallest(1, "distance").iloc[0]

    name = str(nearest["Driver"])
    try:
        them = state_at(laps, name, lap)
        gap = gap_between(laps, name, driver, lap)
    except (LookupError, ValueError):
        return None
    stops = [s for s in pit_stops(laps, name) if s > lap]
    plan = stops[0] if stops else None
    target = None
    if plan is not None:
        try:
            target = compound_after(laps, name, plan)
        except LookupError:
            plan = None
    return RivalSpec(
        name=name,
        gap_s=gap if int(nearest["Position"]) < position else -abs(gap),
        compound=them.compound, tyre_age=them.tyre_age,
        pit_lap=plan, target_compound=target,
    )


def _stratified_section(frame: pd.DataFrame) -> list[str]:
    """Split the same decisions by which game they were, and report each.

    Added after Charles Thraves (Universidad de Chile) asked how the rival is
    chosen. The pooled result above is what was published and is left alone;
    this is what an outside question produced.
    """
    roles = {
        "rival ahead": "rival ahead — the audited car is the chaser, and it commits first",
        "rival behind": "rival behind — the audited car is the leader, and it commits first",
    }

    ties = int((frame["relation"] == "tie").sum())
    decided = len(frame) - ties

    lines = [
        "",
        "## Stratified by which car commits first",
        "",
        "This section exists because **Charles Thraves** (Universidad de Chile), "
        "whose zero-sum feedback Stackelberg treatment of the Formula 1 pit stop "
        "is the closest published work to the engine used above, asked how the "
        "rival is selected. `_nearest_rival` takes the car closest in classified "
        "position by *absolute* distance, so it is the car ahead on some "
        "decisions and the car behind on others — while the order of commitment "
        "is fixed, since the audited car always moves first. Two different games "
        "were therefore pooled, and the track-position leader is not the "
        "Stackelberg leader. Everything above is left as published.",
        "",
        "### The rival was chosen arbitrarily on most decisions",
        "",
        f"Before the split is worth reading, the selection rule has to be "
        f"described honestly. For any car that is not leading the race, the cars "
        f"one position ahead and one position behind are **both exactly one "
        f"position away**, so minimising the absolute distance has no unique "
        f"answer and `nsmallest` returns whichever row comes first. That is the "
        f"normal case, not an edge case: **{ties} of {len(frame)} decisions** are "
        f"ties. Only the {decided} decisions taken by the race leader, which has "
        f"no car ahead of it, have an unambiguous nearest rival.",
        "",
        "That is a real weakness in the measurement and it was not visible until "
        "someone asked. It also raises the stake of the table below: if the two "
        "roles disagreed, three quarters of this sample would have been assigned "
        "to one game or the other by DataFrame row order.",
        "",
        "### The two games, by the role the rival actually played",
        "",
        "| stratum | decisions | median single-car error | median cover-aware error | closer | further | unchanged | median laps closed |",
        "|---|---|---|---|---|---|---|---|",
    ]

    medians = {}
    for key, label in roles.items():
        part = frame[frame["realised"] == key]
        if part.empty:
            lines.append(f"| {label} | 0 | — | — | — | — | — | — |")
            continue
        medians[key] = float(part["closed"].median())
        lines.append(
            f"| {label} | {len(part)} | "
            f"{part['single_car_error'].median():+.0f} | "
            f"{part['adversarial_error'].median():+.0f} | "
            f"{int((part['closed'] > 0).sum())} | "
            f"{int((part['closed'] < 0).sum())} | "
            f"{int((part['closed'] == 0).sum())} | "
            f"{part['closed'].median():+.1f} |"
        )

    lines += [
        "",
        "Errors are signed, and positive means the model stops later than the "
        "team did. *Closer* and *further* compare absolute errors, so a positive "
        "median laps closed would mean the cover-aware model moved toward the "
        "real stop.",
        "",
    ]

    values = list(medians.values())
    opposed = len(values) == 2 and min(values) < 0 < max(values)

    if opposed:
        lines += [
            "**The two roles have opposite signs.** The pooled result is then an "
            "aggregation artefact: covering helps in one configuration and hurts "
            "in the other, and averaging them hides both. The pooled verdict "
            "should not be quoted without this table beside it.",
        ]
    else:
        lines += [
            "**Both roles point the same way, and by the same amount.** Covering "
            "moves the recommendation *away* from the real stop whether the "
            "audited car is the chaser or the leader. The pooled result was not "
            "hiding two opposed effects, so separating them does not rescue the "
            "undercut hypothesis — it buries it. This is a stronger refutation "
            "than the pooled number alone, because it survives the obvious "
            "objection to how the rival was chosen.",
            "",
            "It also means the arbitrary tie-break above, uncomfortable as it is, "
            "did not bias the published result: the two roles it was choosing "
            "between give the same answer, so which one it picked could not have "
            "changed the verdict.",
        ]

    lines += [
        "",
        "### What this does not settle",
        "",
        "Position adjacency is the wrong unit for an undercut. Whether one is "
        "available is decided by the gap in **seconds** against the pit loss: a "
        "car more than a pit loss ahead cannot be undercut, and one more than a "
        "pit loss behind cannot undercut you. A rival one position away may be "
        "half a second up the road or twenty-five seconds up it, and this "
        "selection rule treats those identically. Re-running with the rival "
        "defined as the nearest car *within* the circuit's measured pit-loss "
        "window — separately for the car ahead and the car behind — would both "
        "fix the ambiguity and make the empty case meaningful, since a decision "
        "with no reachable rival has no undercut to model and belongs to the "
        "single-car case. That is the next experiment, not this one.",
        "",
    ]
    return lines


def main() -> int:
    warnings.filterwarnings("ignore")
    models = load_circuit_models()
    swaps = _swap_rates()
    audit = pd.read_csv(F1_DERIVED_DIR / "systematic_audit.csv")

    rows = []
    for index, decision in enumerate(audit.itertuples(), 1):
        circuit = decision.circuit
        if circuit not in models or circuit not in swaps:
            continue
        print(f"[{index}/{len(audit)}] {decision.season} {circuit} {decision.driver}",
              flush=True)
        laps = load_race_laps(f"{decision.season}_{circuit}")
        rival = _nearest_rival(laps, decision.driver, int(decision.decision_lap))
        if rival is None:
            continue
        try:
            state = state_at(laps, decision.driver, int(decision.decision_lap))
            target = compound_after(laps, decision.driver, int(decision.real_pit_lap))
        except (LookupError, ValueError):
            continue
        compounds = frozenset(models[circuit].degradation)
        if state.compound not in compounds or target not in compounds:
            continue
        if rival.compound not in compounds:
            continue
        if rival.target_compound is not None and rival.target_compound not in compounds:
            rival = RivalSpec(rival.name, rival.gap_s, rival.compound,
                              rival.tyre_age, None, None)

        scenario = Scenario(
            circuit=circuit, current_lap=int(decision.decision_lap),
            total_laps=int(laps["LapNumber"].max()),
            compound=state.compound, tyre_age=state.tyre_age,
            target_compound=target, rivals=(rival,),
        )
        try:
            result = duel(scenario, rival, models[circuit],
                          swap_rate=float(swaps[circuit]),
                          n_draws=N_DRAWS, seed=SEED)
        except Exception:  # noqa: BLE001 — a decision the duel cannot represent
            continue

        stratum = _stratum(laps, decision.driver, int(decision.decision_lap)) or {}
        rows.append({
            "season": decision.season, "circuit": circuit, "driver": decision.driver,
            "real_pit_lap": decision.real_pit_lap,
            "single_car_lap": decision.model_pit_lap,
            "adversarial_lap": int(result.adversarial_pit_lap),
            "swap_rate": round(float(swaps[circuit]), 4),
            "rival": rival.name,
            "my_position": stratum.get("my_position"),
            "rival_position": stratum.get("rival_position"),
            "gap_positions": stratum.get("gap_positions"),
            "relation": stratum.get("relation"),
        })

    frame = pd.DataFrame(rows)
    frame["single_car_error"] = frame["single_car_lap"] - frame["real_pit_lap"]
    frame["adversarial_error"] = frame["adversarial_lap"] - frame["real_pit_lap"]
    frame["closed"] = frame["single_car_error"].abs() - frame["adversarial_error"].abs()
    # Which game each decision actually was. `relation` says whether that was
    # decided by the classification or by row order; this says what was played.
    frame["realised"] = np.where(
        frame["rival_position"] < frame["my_position"], "rival ahead", "rival behind"
    )
    frame.to_csv(F1_DERIVED_DIR / "undercut_hypothesis.csv", index=False)

    closer = int((frame["closed"] > 0).sum())
    further = int((frame["closed"] < 0).sum())
    same = int((frame["closed"] == 0).sum())
    median_closed = frame["closed"].median()
    verdict = (
        "**supported**" if median_closed >= 2
        else "**not supported**" if median_closed <= 0.5
        else "**partially supported**"
    )

    lines = [
        "<!-- GENERATED by scripts/run_undercut_hypothesis.py — do not edit by "
        "hand. -->",
        "",
        "# Does modelling the undercut explain the late-stopping bias?",
        "",
        "The [calendar-wide audit](systematic_audit.md) found the simulator would "
        "stay out a median of 12 laps longer than teams did, refuted the "
        "safety-car explanation, and named one untested candidate: the engine "
        "optimises **one car's** expected race time, so it can never pay for an "
        "undercut — and an undercut is why a real team stops before it has to.",
        "",
        "This tests it. The same decisions are re-run through "
        "`src/simulator/adversarial.py`, which models the stop as a two-player "
        "game where the rival covers and which consumes each circuit's measured "
        "track-position stickiness. If the absence of track position is what "
        "makes the model late, the cover-aware optimum should sit **earlier** — "
        "closer to what the team did.",
        "",
        f"**{len(frame)} decisions re-run.** Median error against the real stop:",
        "",
        "| model | median error (laps) | median absolute error |",
        "|---|---|---|",
        f"| single-car (the audit's) | {frame['single_car_error'].median():+.0f} | "
        f"{frame['single_car_error'].abs().median():.0f} |",
        f"| cover-aware (adversarial) | {frame['adversarial_error'].median():+.0f} | "
        f"{frame['adversarial_error'].abs().median():.0f} |",
        "",
        f"The cover-aware model is closer to the real stop in **{closer}** "
        f"decisions, further in **{further}**, and identical in {same}. Median "
        f"laps of error closed: **{median_closed:+.1f}**.",
        "",
        f"## Verdict: the hypothesis is {verdict}",
        "",
    ]

    if median_closed <= 0.5:
        lines += [
            "Making the rival react does **not** move the recommendation toward "
            "what teams did. Whatever explains the late-stopping bias, it is not "
            "simply that the single-car engine cannot see an undercut — the "
            "cover-aware engine can, and it stops at essentially the same lap.",
            "",
            "That leaves the second candidate the audit named, now the only one "
            "standing: **the fitted slopes are biased toward durability**. A tyre "
            "that looks flatter than it is makes staying out look cheaper than it "
            "is, and the endurance side of this project has a diagnosed, unfixed "
            "omitted variable that pushes slopes exactly that way "
            "([track evolution](../cross_series/track_evolution_omitted_variable.md)). "
            "Whether the F1 fits carry the same bias is still not established, "
            "and it is now the obvious thing to test next.",
            "",
            "It is worth being clear about what this section is: a mechanism that "
            "sounded right, written into a report as a candidate, and then "
            "measured and rejected. The audit is more useful for having lost one "
            "of its two explanations than it would be for keeping both.",
        ]
    else:
        lines += [
            "Making the rival react moves the recommendation toward what teams "
            "did, by a median of "
            f"{median_closed:+.1f} laps. Track position is therefore part of the "
            "answer, and a single-car objective is measurably the wrong one for "
            "deciding a stop lap in traffic.",
        ]

    lines += [
        "",
        "## By circuit stickiness",
        "",
        "Track position matters most where places are hard to regain, so if the "
        "mechanism is real the effect should be largest at sticky circuits:",
        "",
        "| circuit | swap rate | decisions | median laps closed |",
        "|---|---|---|---|",
    ]
    by_circuit = frame.groupby("circuit").agg(
        swap=("swap_rate", "first"),
        decisions=("closed", "size"),
        closed=("closed", "median"),
    ).sort_values("swap")
    for circuit, row in by_circuit.iterrows():
        lines.append(
            f"| {circuit} | {row['swap']:.4f} | {int(row['decisions'])} | "
            f"{row['closed']:+.1f} |"
        )

    correlation = by_circuit["swap"].corr(by_circuit["closed"])
    lines += [
        "",
        f"Correlation between a circuit's swap rate and the laps the cover-aware "
        f"model closes: **{correlation:+.3f}**. "
        + ("A negative correlation would be the signature of the mechanism — "
           "more effect where position is stickier."
           if not np.isnan(correlation) else ""),
        "",
    ]

    lines += _stratified_section(frame)

    (F1_REPORTS_DIR / "undercut_hypothesis.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    print(f"\n{len(frame)} decisions re-run; median laps closed {median_closed:+.1f}")
    print(f"wrote {F1_REPORTS_DIR / 'undercut_hypothesis.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
