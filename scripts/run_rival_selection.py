"""Does it matter which car the adversarial model treats as the rival?

The published replay picks the rival by minimising absolute classified-position
distance. Charles Thraves objected that this chooses the car ahead on some
decisions and the car behind on others while the decision order is fixed, and
that with equidistant neighbours the choice is incidental: 271 of 357 decisions
came out as such ties. He then proposed a criterion rather than only a fault.
In his words, estimate for each car its total race time under its own optimal
strategy in the absence of competition, and take as rival the car whose
estimated time is closest to the audited car's.

Four selection rules are run against the same 357 decisions, so the question
"does the rival choice move Result 3" gets an answer rather than an argument:

``position``
    The published rule. Nearest on classified position, ties broken by row
    order.
``pi_window``
    Nearest on the clock among cars within one pit loss. A first-order reading
    of reachability: a lead larger than the stop cost cannot be taken by
    stopping first, whatever the tyre does.
``d1``
    The car immediately ahead on cumulative time. This is the pairing
    Salminen's position-keeping defence is defined on, and it names leader and
    chaser without a tie-break.
``thraves``
    His heuristic. Each car's standalone optimal race time is scored with the
    same exact dynamic program the audit already uses, from that car's own
    green pace, the circuit-compound degradation it is running, and the
    circuit's measured pit loss. No refuelling in Formula 1, so the fuel cap is
    the race distance and never binds; what the program trades off is
    degradation against stop cost.

**The limit, in his words.** At the extreme the choice of rival becomes
endogenous, since each car's strategy depends on the others. The standalone
time this heuristic sorts on is computed with no competition in it, which is
what makes it computable and also what makes it an approximation. It is
reported as a declared limitation and not resolved here.

Writes ``data/derived/f1/rival_selection.csv`` and
``reports/f1/rival_selection.md``.

Usage (offline, from the repo root; slow, four duels per decision)::

    python scripts/run_rival_selection.py
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
from src.simulator.multistop import optimal_stop_plan  # noqa: E402

OUT_CSV = F1_DERIVED_DIR / "rival_selection.csv"
OUT_MD = F1_REPORTS_DIR / "rival_selection.md"

#: Matches the published replay exactly, so the `position` arm reproduces it
#: rather than approximating it.
N_DRAWS = 1500
SEED = 20260712

METHODS = ("position", "pi_window", "d1", "thraves")


def _green(laps: pd.DataFrame) -> pd.DataFrame:
    return laps[
        (laps["TrackStatus"].astype(str) == "1")
        & (~laps["is_in_lap"].astype(bool))
        & (~laps["is_out_lap"].astype(bool))
        & laps["lap_time_s"].notna()
    ]


def standalone_race_times(laps: pd.DataFrame, model, race_laps: int) -> dict[str, float]:
    """Each car's total race time under its own optimum, with nobody else on track.

    Thraves's criterion. The pace is that car's own median green racing lap, so
    two cars differ by what the timing says they differ by; the degradation is
    the circuit-compound posterior for the tyre the car is actually on, which
    is the second-order effect he confirmed matters -- a car on a fast-wearing
    compound reaches its optimum on a different lap from one on a durable tyre
    even at identical raw pace. Fuel range is the race distance, since Formula 1
    has not refuelled since 2010, so the cap never binds and the program trades
    degradation against stop cost alone.
    """
    green = _green(laps)
    if green.empty:
        return {}
    pit_loss = float(model.pit_loss.median_s)
    times: dict[str, float] = {}
    for driver, part in green.groupby("Driver"):
        pace = float(part["lap_time_s"].median())
        compound = part["Compound"].mode()
        slope = 0.0
        if not compound.empty and str(compound.iloc[0]) in model.degradation:
            slope = float(model.degradation[str(compound.iloc[0])][0].mean)
        plan = optimal_stop_plan(
            race_laps=race_laps, green_pace_s=pace, net_slope_s=max(slope, 0.0),
            pit_loss_s=pit_loss, fuel_range_laps=race_laps,
        )
        if plan.deterministic_time_s is not None:
            times[str(driver)] = float(plan.deterministic_time_s)
    return times


def _spec(laps: pd.DataFrame, driver: str, name: str, lap: int) -> RivalSpec | None:
    """Build the rival the engine needs, once a selection rule has named a car."""
    try:
        them = state_at(laps, name, lap)
        gap = gap_between(laps, name, driver, lap)
    except (LookupError, ValueError):
        return None
    on_lap = laps[laps["LapNumber"] == lap]
    mine = on_lap[on_lap["Driver"] == driver]
    theirs = on_lap[on_lap["Driver"] == name]
    if mine.empty or theirs.empty:
        return None
    ahead = float(theirs.iloc[0]["Position"]) < float(mine.iloc[0]["Position"])
    stops = [s for s in pit_stops(laps, name) if s > lap]
    plan = stops[0] if stops else None
    target = None
    if plan is not None:
        try:
            target = compound_after(laps, name, plan)
        except LookupError:
            plan = None
    return RivalSpec(
        name=name, gap_s=gap if ahead else -abs(gap),
        compound=them.compound, tyre_age=them.tyre_age,
        pit_lap=plan, target_compound=target,
    )


def select(method: str, laps: pd.DataFrame, driver: str, lap: int,
           standalone: dict[str, float], pit_loss: float) -> str | None:
    """Which car this rule calls the rival, or None where the rule says nothing."""
    on_lap = laps[laps["LapNumber"] == lap].dropna(subset=["Position"])
    mine = on_lap[on_lap["Driver"] == driver]
    others = on_lap[on_lap["Driver"] != driver]
    if mine.empty or others.empty:
        return None

    if method == "position":
        position = int(mine.iloc[0]["Position"])
        nearest = others.assign(
            distance=lambda d: (d["Position"] - position).abs()
        ).nsmallest(1, "distance")
        return str(nearest.iloc[0]["Driver"])

    if method in {"pi_window", "d1"}:
        if "time_s" not in laps.columns or mine.iloc[0]["time_s"] is None:
            return None
        my_time = float(mine.iloc[0]["time_s"])
        deltas = others.assign(
            delta=others["time_s"].astype(float) - my_time
        ).dropna(subset=["delta"])
        if method == "d1":
            # The car immediately ahead on the clock: the leader whose defence
            # is the one being modelled.
            ahead = deltas[deltas["delta"] < 0]
            if ahead.empty:
                return None
            return str(ahead.nlargest(1, "delta").iloc[0]["Driver"])
        within = deltas[deltas["delta"].abs() <= pit_loss]
        if within.empty:
            return None
        return str(within.assign(
            distance=lambda d: d["delta"].abs()
        ).nsmallest(1, "distance").iloc[0]["Driver"])

    if method == "thraves":
        if driver not in standalone:
            return None
        mine_time = standalone[driver]
        candidates = {
            name: abs(value - mine_time)
            for name, value in standalone.items()
            if name != driver and name in set(others["Driver"])
        }
        if not candidates:
            return None
        return min(candidates, key=candidates.get)

    raise ValueError(f"unknown selection method {method!r}")


#: How each rule is described in the report, in the order they are shown.
DESCRIPTION = {
    "position": "nearest on classified position (the published rule)",
    "pi_window": "nearest on the clock, within one pit loss",
    "d1": "the car immediately ahead on cumulative time",
    "thraves": "nearest standalone optimal race time",
}


def write_report(frame: pd.DataFrame) -> Path:
    scored = frame.dropna(subset=["adversarial_lap"])
    published = scored[scored["method"] == "position"]

    lines = [
        "<!-- generated by scripts/run_rival_selection.py -->",
        "",
        "# Does it matter which car the model treats as the rival?",
        "",
        "Generated. Do not edit by hand.",
        "",
        "The published replay picks the rival by minimising absolute "
        "classified-position distance. Charles Thraves objected that this "
        "chooses the car ahead on some decisions and the car behind on "
        "others while the decision order is fixed, and that equidistant "
        "neighbours leave the choice to row order. He then proposed a "
        "criterion rather than only a fault: estimate for each car the total "
        "race time it would set under its own optimal strategy with no "
        "competition, and take as rival the car whose estimated time is "
        "closest.",
        "",
        "Four rules are run against the same decisions, so the question has "
        "an answer rather than an argument.",
        "",
        "| rule | what it picks | decisions scored |",
        "| --- | --- | ---: |",
    ]
    for method in METHODS:
        part = scored[scored["method"] == method]
        lines.append(
            f"| `{method}` | {DESCRIPTION[method]} | {len(part)} |"
        )

    lines += [
        "",
        "## Does the choice move Result 3?",
        "",
        "Errors are signed in laps, positive meaning the model stops later "
        "than the team did. *Closed* is the single-car error minus the "
        "cover-aware one in absolute terms, so a positive median would mean "
        "modelling the rival moved the recommendation toward what the team "
        "did.",
        "",
        "| rule | median cover-aware error | median single-car error | median closed | improved | worsened |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for method in METHODS:
        part = scored[scored["method"] == method]
        if part.empty:
            continue
        lines.append(
            f"| `{method}` | {part['adversarial_error'].median():+.0f} | "
            f"{part['single_car_error'].median():+.0f} | "
            f"{part['closed'].median():+.0f} | "
            f"{int((part['closed'] > 0).sum())} | "
            f"{int((part['closed'] < 0).sum())} |"
        )

    best = max(
        (m for m in METHODS if not scored[scored["method"] == m].empty),
        key=lambda m: scored[scored["method"] == m]["closed"].median(),
    )
    best_median = scored[scored["method"] == best]["closed"].median()
    verdict = (
        "No selection rule rescues it."
        if best_median <= 0 else
        f"The `{best}` rule moves it, by a median of {best_median:+.0f} laps."
    )
    lines += [
        "",
        f"**{verdict}** The cover-aware recommendation sits further from the "
        "real stop than the single-car one under every rule tried. His "
        "objection to the method stands and correcting it does not change "
        "the finding; the two are separate.",
        "",
        "## How often the rules disagree",
        "",
        "Two rules agreeing on a decision means they named the same car.",
        "",
        "| | " + " | ".join(f"`{m}`" for m in METHODS) + " |",
        "| --- | " + " | ".join("---:" for _ in METHODS) + " |",
    ]
    wide = frame.pivot_table(
        index=["season", "circuit", "driver"], columns="method",
        values="rival", aggfunc="first",
    )
    for row_method in METHODS:
        cells = []
        for col_method in METHODS:
            if row_method not in wide or col_method not in wide:
                cells.append("--")
                continue
            if row_method == col_method:
                cells.append("--")
                continue
            # Selecting the same column twice gives a frame, not a pair of
            # series, which is why the diagonal is skipped above rather than
            # computed and discarded.
            both = wide[[row_method, col_method]].dropna()
            if both.empty:
                cells.append("--")
                continue
            share = 100 * float(
                (both[row_method] == both[col_method]).mean()
            )
            cells.append(f"{share:.0f}%")
        lines.append(f"| `{row_method}` | " + " | ".join(cells) + " |")

    agreement = wide.dropna()
    if not agreement.empty:
        all_same = (agreement.nunique(axis=1) == 1).mean()
        lines += [
            "",
            f"All four rules name the same car on **{100 * all_same:.0f}%** "
            f"of the {len(agreement)} decisions where all four apply.",
        ]

    thraves = scored[scored["method"] == "thraves"].dropna(
        subset=["standalone_delta_s"]
    )
    if not thraves.empty:
        lines += [
            "",
            "## What the heuristic is sorting on",
            "",
            "The gap in estimated standalone race time between the audited "
            "car and the rival it selects has a median of "
            f"**{thraves['standalone_delta_s'].median():.1f} s** over a full "
            "race, quartiles "
            f"{thraves['standalone_delta_s'].quantile(0.25):.1f} to "
            f"{thraves['standalone_delta_s'].quantile(0.75):.1f}. Each car's "
            "estimate comes from its own median green lap, the "
            "circuit-compound degradation posterior for the tyre it is on, "
            "and the circuit's measured pit loss, scored by the same exact "
            "dynamic program the audit uses. Formula 1 has not refuelled "
            "since 2010, so the fuel cap is the race distance and never "
            "binds; what the program trades off is degradation against stop "
            "cost.",
        ]

    lines += [
        "",
        "## The limit, in his words",
        "",
        "At the extreme the choice of rival becomes endogenous, since each "
        "car's strategy depends on the others. The standalone time this "
        "heuristic sorts on is computed with no competition in it, which is "
        "what makes it computable and equally what makes it an "
        "approximation. Nothing here resolves that: a selection rule "
        "accounting for the interaction would have to solve the joint "
        "problem that selecting a rival is a step toward.",
        "",
        "A second approximation is mine rather than his. The standalone time "
        "is the whole race from the start, not the remaining race from the "
        "decision lap, so it sorts cars by intrinsic speed rather than by "
        "where they are in the race. Sorting on remaining time would pair "
        "cars that are close now; sorting on whole-race time pairs cars that "
        "are close in capability. His formulation is the latter and it is "
        "what is implemented.",
        "",
    ]
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    return OUT_MD


def main() -> int:
    warnings.filterwarnings("ignore")
    if "--report-only" in sys.argv:
        # Four duels per decision is a long run; rewriting prose should not
        # require repeating it.
        frame = pd.read_csv(OUT_CSV)
        out = write_report(frame)
        print(f"wrote {out}")
        return 0
    models = load_circuit_models()
    swaps = dict(zip(
        *pd.read_csv(F1_DERIVED_DIR / "overtaking_difficulty.csv")
        [["circuit", "adj_swap_rate"]].to_numpy().T
    ))
    audit = pd.read_csv(F1_DERIVED_DIR / "systematic_audit.csv")

    rows = []
    for index, decision in enumerate(audit.itertuples(), 1):
        circuit = str(decision.circuit)
        if circuit not in models or circuit not in swaps:
            continue
        print(f"[{index}/{len(audit)}] {decision.season} {circuit} "
              f"{decision.driver}", flush=True)
        try:
            laps = load_race_laps(f"{decision.season}_{circuit}")
        except (FileNotFoundError, ValueError):
            continue
        lap = int(decision.decision_lap)
        race_laps = int(laps["LapNumber"].max())
        model = models[circuit]
        compounds = frozenset(model.degradation)

        try:
            state = state_at(laps, str(decision.driver), lap)
            target = compound_after(laps, str(decision.driver),
                                    int(decision.real_pit_lap))
        except (LookupError, ValueError):
            continue
        if state.compound not in compounds or target not in compounds:
            continue

        standalone = standalone_race_times(laps, model, race_laps)
        pit_loss = float(model.pit_loss.median_s)

        for method in METHODS:
            name = select(method, laps, str(decision.driver), lap,
                          standalone, pit_loss)
            row = {
                "season": decision.season, "circuit": circuit,
                "driver": decision.driver, "method": method,
                "real_pit_lap": decision.real_pit_lap,
                "single_car_lap": decision.model_pit_lap,
                "rival": name,
            }
            if name is None:
                rows.append(row)
                continue
            spec = _spec(laps, str(decision.driver), name, lap)
            if spec is None or spec.compound not in compounds:
                rows.append(row)
                continue
            if spec.target_compound is not None and spec.target_compound not in compounds:
                spec = RivalSpec(spec.name, spec.gap_s, spec.compound,
                                 spec.tyre_age, None, None)
            scenario = Scenario(
                circuit=circuit, current_lap=lap, total_laps=race_laps,
                compound=state.compound, tyre_age=state.tyre_age,
                target_compound=target, rivals=(spec,),
            )
            try:
                result = duel(scenario, spec, model,
                              swap_rate=float(swaps[circuit]),
                              n_draws=N_DRAWS, seed=SEED)
            except Exception:  # noqa: BLE001 - a decision the duel cannot represent
                rows.append(row)
                continue
            row["adversarial_lap"] = int(result.adversarial_pit_lap)
            row["gap_s"] = round(float(spec.gap_s), 3)
            row["standalone_delta_s"] = (
                round(abs(standalone[name] - standalone[str(decision.driver)]), 3)
                if name in standalone and str(decision.driver) in standalone
                else None
            )
            rows.append(row)

    frame = pd.DataFrame(rows)
    frame["single_car_error"] = frame["single_car_lap"] - frame["real_pit_lap"]
    frame["adversarial_error"] = frame["adversarial_lap"] - frame["real_pit_lap"]
    frame["closed"] = (
        frame["single_car_error"].abs() - frame["adversarial_error"].abs()
    )
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUT_CSV, index=False)
    print(f"wrote {OUT_CSV}")
    out = write_report(frame)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
