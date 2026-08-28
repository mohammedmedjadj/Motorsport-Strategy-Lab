"""Replay every real first pit stop on the F1 calendar through the simulator.

The decision audit used to be five hand-picked races. This is the same question
asked uniformly: for every race with a fitted model, the top finishers' first
stops are replayed and the model's recommendation compared to what the team did.

Writes ``data/derived/f1/systematic_audit.csv`` and
``reports/f1/systematic_audit.md``.

Usage (offline, from the repo root)::

    python scripts/run_systematic_audit.py
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from src.audit.systematic import (  # noqa: E402
    LOOKBACK,
    N_FINISHERS,
    replay_race,
    to_frame,
)
from src.ingestion.config import F1_DERIVED_DIR, F1_REPORTS_DIR, PRE_ERA_SEASONS  # noqa: E402
from src.simulator.artifacts import load_circuit_models  # noqa: E402

N_DRAWS = 1500


def race_slugs() -> list[str]:
    """Every ingested race inside the regulation-stable fitting window."""
    slugs = []
    for path in sorted(F1_DERIVED_DIR.glob("laps_*.csv")):
        season, circuit = path.stem.removeprefix("laps_").split("_", 1)
        if int(season) in PRE_ERA_SEASONS:
            slugs.append(f"{season}_{circuit}")
    return slugs


def report(frame: pd.DataFrame) -> str:
    green = frame[~frame["real_stop_neutralised"]]
    neutral = frame[frame["real_stop_neutralised"]]
    agree = frame[frame["delta_laps"].abs() <= 1]
    late = frame[frame["delta_laps"] > 1]
    early = frame[frame["delta_laps"] < -1]
    lines = [
        "# F1 decision audit — every first stop on the calendar",
        "",
        f"The model is asked **{LOOKBACK} laps before** each real first stop, "
        f"given the state as it actually was, for the top {N_FINISHERS} "
        "classified finishers of every race with a fitted model. Its "
        "recommended lap is compared to the team's.",
        "",
        "A **replay, not a forecast**: the decision point is defined relative to "
        "a stop that already happened. The question is where the model disagrees "
        "with real strategy and by how much, not whether it could have called "
        "the race.",
        "",
        f"**{len(frame)} decisions across {frame['circuit'].nunique()} circuits "
        f"and {frame.groupby(['season', 'circuit']).ngroups} races.**",
        "",
        "| | decisions | share | median |Δ| | median cost of the real lap |",
        "|---|---|---|---|---|",
        f"| model agrees within 1 lap | {len(agree)} | {len(agree)/len(frame):.0%} | "
        f"{agree['delta_laps'].abs().median():.0f} | {agree['median_cost_s'].median():.2f} s |",
        f"| model would have stopped **later** | {len(late)} | {len(late)/len(frame):.0%} | "
        f"{late['delta_laps'].abs().median():.0f} | {late['median_cost_s'].median():.2f} s |",
        f"| model would have stopped **earlier** | {len(early)} | {len(early)/len(frame):.0%} | "
        f"{early['delta_laps'].abs().median():.0f} | {early['median_cost_s'].median():.2f} s |",
        "",
        "`median cost` is the model's own median race time at the lap the team "
        "chose, minus at the lap it would have chosen. It is the size of the "
        "disagreement in seconds, and it is the number that says whether a "
        "disagreement in laps matters at all.",
        "",
        "## Where the model disagrees most",
        "",
        "| season | circuit | driver | real | model | Δ | cost |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in frame.reindex(frame["median_cost_s"].abs().sort_values(ascending=False).index).head(12).itertuples():
        lines.append(
            f"| {r.season} | {r.circuit} | {r.driver} | {r.real_pit_lap} | "
            f"{r.model_pit_lap} | {r.delta_laps:+d} | {r.median_cost_s:+.2f} s |"
        )

    lines += [
        "",
        "## The disagreement is a systematic bias, and it is not the safety cars",
        "",
        "The obvious explanation is that teams box opportunistically into a "
        "neutralisation the model cannot foresee — it is asked five laps "
        "earlier, before the Safety Car exists. **Measured, that is not what "
        "is happening.** Splitting the same decisions on whether the real stop "
        "was neutralised:",
        "",
        "| real stop taken | decisions | median Δ laps | median cost |",
        "|---|---|---|---|",
        f"| under green | {len(green)} | {green['delta_laps'].median():+.0f} | "
        f"{green['median_cost_s'].median():+.2f} s |",
        f"| under a neutralisation | {len(neutral)} | "
        f"{neutral['delta_laps'].median():+.0f} | "
        f"{neutral['median_cost_s'].median():+.2f} s |",
        "",
        "The bias is present in **both** groups and barely larger in the "
        "neutralised one. Whatever makes this model want to run the tyre out, "
        "it applies to ordinary green-flag stops as much as to opportunistic "
        "ones, so missing foresight does not account for it.",
        "",
        "**What the audit establishes is that the bias exists and is large.** "
        "Two causes were consistent with it. One has since been tested and "
        "**rejected**; the other is still open:",
        "",
        "1. ~~**No track position.**~~ **Tested and rejected.** The engine "
        "optimises one car's expected race time and cannot pay for an undercut, "
        "which sounded like the answer. Re-running all 357 decisions through "
        "the cover-aware adversarial engine — which does model the undercut and "
        "does consume each circuit's measured stickiness — moves the "
        "recommendation *away* from the real stop, not toward it: median error "
        "+11 laps against the single-car engine's +9, closer in 65 decisions and "
        "further in 188. See "
        "[`undercut_hypothesis.md`](undercut_hypothesis.md).",
        "2. **Slopes biased toward durability.** The endurance side of this "
        "project has a diagnosed, unfixed omitted variable that pushes fitted "
        "degradation slopes *down* "
        "([track evolution](../cross_series/track_evolution_omitted_variable.md)). "
        "A tyre that looks flatter than it is makes staying out look cheaper "
        "than it is. Whether the F1 fits carry the same bias is not established.",
        "",
        "With track position eliminated, the slope-bias candidate is the one "
        "left standing, and it is now specific enough to test: fit the F1 "
        "degradation model with a race-time term and see whether the "
        "recommendation moves earlier. That is the same correction withdrawn "
        "twice on endurance data, so it is not a small job — but it is now the "
        "only explanation this audit has not ruled out.",
        "",
    ]

    by_circuit = frame.groupby("circuit").agg(
        decisions=("delta_laps", "size"),
        median_abs_delta=("delta_laps", lambda s: s.abs().median()),
        median_cost=("median_cost_s", "median"),
    ).sort_values("median_cost", ascending=False)
    lines += [
        "",
        "## By circuit",
        "",
        "| circuit | decisions | median |Δ| laps | median cost |",
        "|---|---|---|---|",
    ]
    for circuit, r in by_circuit.iterrows():
        lines.append(
            f"| {circuit} | {int(r['decisions'])} | {r['median_abs_delta']:.0f} | "
            f"{r['median_cost']:+.2f} s |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    warnings.filterwarnings("ignore")
    models = load_circuit_models()
    replays = []
    slugs = race_slugs()
    for index, slug in enumerate(slugs, 1):
        circuit = slug.split("_", 1)[1]
        if circuit not in models:
            continue
        print(f"[{index}/{len(slugs)}] {slug}", flush=True)
        replays += replay_race(slug, models[circuit], n_draws=N_DRAWS)

    frame = to_frame(replays)
    F1_DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_csv(F1_DERIVED_DIR / "systematic_audit.csv", index=False)
    (F1_REPORTS_DIR / "systematic_audit.md").write_text(report(frame), encoding="utf-8")
    print(f"\n{len(frame)} decisions replayed across "
          f"{frame.groupby(['season', 'circuit']).ngroups} races")
    print(f"wrote {F1_DERIVED_DIR / 'systematic_audit.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
