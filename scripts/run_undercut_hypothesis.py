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

        rows.append({
            "season": decision.season, "circuit": circuit, "driver": decision.driver,
            "real_pit_lap": decision.real_pit_lap,
            "single_car_lap": decision.model_pit_lap,
            "adversarial_lap": int(result.adversarial_pit_lap),
            "swap_rate": round(float(swaps[circuit]), 4),
        })

    frame = pd.DataFrame(rows)
    frame["single_car_error"] = frame["single_car_lap"] - frame["real_pit_lap"]
    frame["adversarial_error"] = frame["adversarial_lap"] - frame["real_pit_lap"]
    frame["closed"] = frame["single_car_error"].abs() - frame["adversarial_error"].abs()
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

    (F1_REPORTS_DIR / "undercut_hypothesis.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    print(f"\n{len(frame)} decisions re-run; median laps closed {median_closed:+.1f}")
    print(f"wrote {F1_REPORTS_DIR / 'undercut_hypothesis.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
