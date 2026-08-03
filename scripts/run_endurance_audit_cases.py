"""Per-decision retrospective audit for WEC and IMSA — the endurance analogue
of ``scripts/run_audit.py`` (F1 Phase 5).

For each case: rebuild the real race state from the committed derived laps,
simulate every alternative next-stop lap, compare the model's window with the
real stop, and state plainly whether the model agrees, disagrees, or gives an
honestly wide, indecisive answer.

Usage (from the repo root, offline — reads committed derived data)::

    python scripts/run_endurance_audit_cases.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.audit.endurance_cases import EnduranceAuditCase, build_cases  # noqa: E402
from src.ingestion.config import REPORTS_DIR  # noqa: E402
from src.simulator.endurance import simulate  # noqa: E402

N_DRAWS = 5000
SEED = 20260712
WINDOW_TOLERANCE_S = 0.5  # same convention as src/simulator/recommend.py


def window_and_best(table: pd.DataFrame) -> tuple[int, tuple[int, ...]]:
    """Best-median candidate and the set within WINDOW_TOLERANCE_S of it —
    the endurance analogue of ``recommend.summarise``'s window, applied
    directly to the table ``simulate`` already returns."""
    best_idx = int(table["median_s"].idxmin())
    best_lap = int(table.loc[best_idx, "pit_lap"])
    best_median = float(table.loc[best_idx, "median_s"])
    window = tuple(
        int(lap) for lap, m in zip(table["pit_lap"], table["median_s"])
        if m <= best_median + WINDOW_TOLERANCE_S
    )
    return best_lap, window


def verdict(table: pd.DataFrame, case: EnduranceAuditCase, best_lap: int, window: tuple[int, ...]) -> str:
    real_row = table[table["pit_lap"] == case.real_pit_lap]
    best_row = table[table["pit_lap"] == best_lap].iloc[0]
    if real_row.empty:
        return f"The real choice (lap {case.real_pit_lap}) is outside the modelled candidate set."
    real = real_row.iloc[0]
    delta = real["median_s"] - best_row["median_s"]
    inside = case.real_pit_lap in window
    return (
        f"Real choice (lap {case.real_pit_lap}): median cost +{delta:.2f}s vs the "
        f"model optimum (lap {best_lap}); {'INSIDE' if inside else 'OUTSIDE'} the "
        f"recommended window."
    )


def focused_table(table: pd.DataFrame, case: EnduranceAuditCase, best_lap: int, window: tuple[int, ...]) -> str:
    keep = set(window) | {case.real_pit_lap, best_lap}
    if 0 in table["pit_lap"].to_numpy():
        keep.add(0)
    df = table[table["pit_lap"].isin(sorted(keep))]
    cols = [c for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, row in df.iterrows():
        cells = [f"{row[c]:.0f}" if c == "pit_lap" else f"{row[c]:.3f}" for c in cols]
        marker = " <- real" if int(row["pit_lap"]) == case.real_pit_lap else ""
        cells[0] += marker
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def audit_case(case: EnduranceAuditCase) -> list[str]:
    table = simulate(case.scenario, case.model, n_draws=N_DRAWS, seed=SEED)
    best_lap, window = window_and_best(table)
    s = case.scenario
    spread = float(table.loc[table["pit_lap"] == best_lap, "p90_s"].iloc[0]
                   - table.loc[table["pit_lap"] == best_lap, "p10_s"].iloc[0])
    w = ", ".join(str(lap) for lap in window)
    lines = [
        f"## Case {case.case_id}: {case.title}",
        "",
        f"**State (measured from data):** end of lap {s.current_lap}/{s.total_laps}, "
        f"car {case.car} on tyre age {s.tyre_age}, {s.laps_since_refuel} laps since "
        f"last refuel (fuel range {case.model.fuel_range_laps} laps; net slope "
        f"{case.model.net_slope_s:+.4f} s/lap).",
        "",
        f"**Real decision:** {case.real_decision}",
        "",
        f"**Question:** {case.question}",
        "",
        "**Model output** (pit_lap 0 = run to the flag without stopping, where feasible):",
        "",
        f"- Best median pit lap: **{best_lap}** — recommended window (medians within "
        f"{WINDOW_TOLERANCE_S}s): **[{w}]**.",
        f"- Outcome spread at the best lap (p10-p90): {spread:.1f}s — the honest "
        "uncertainty of any single-race outcome.",
        f"- **Verdict:** {verdict(table, case, best_lap, window)}",
        "",
        focused_table(table, case, best_lap, window),
        "",
    ]
    print(f"Case {case.case_id}: best {best_lap}, window {window}")
    return lines


HEADER = [
    "Real stop decisions replayed through the single-next-stop simulator "
    f"({N_DRAWS} draws, seed {SEED}). Race states (tyre age, laps since last "
    "refuel, the real stop lap) are reconstructed from the committed derived "
    "laps, not quoted from memory. See ``src/audit/endurance_cases.py`` for "
    "the case-selection rationale — there is no public strategy narrative to "
    "draw on for these races the way F1's audit has, so cases are chosen by a "
    "measurable, uniformly-applied criterion instead (an opportunistic "
    "neutralisation-onset stop, or a routine green-flag one) rather than by "
    "fame.",
    "",
    "Reading guide: the model optimises **expected race time** to the next "
    "stop only, under its stated scope (no rivals, no track position, a "
    "single net degradation slope, FCY/SC hazards drawn from the series-wide "
    "posterior). Where a real decision disagrees, the disagreement is read "
    "against those stated limits, not as a verdict on the crew that made the "
    "call.",
    "",
]


#: Written after reviewing the seed-fixed outputs above; every number cited
#: is reproducible from this script (seed 20260712, 5000 draws).
WEC_ANALYSIS = [
    "## Cross-case analysis",
    "",
    "**1. Opportunistic caution stops are strongly endorsed, even at the "
    "anomalous-slope circuit (Cases A, C).** Both Bahrain 2025's Safety "
    "Car-onset stop and Imola 2024's are inside the model's window, and "
    "decisively so — P(best) 0.84 and 0.91 respectively. The engine prices a "
    "caution stop's opportunity cost the same way regardless of the sign of "
    "the degradation slope, and real strategists' instinct to box the moment "
    "the flag changes holds up even at Imola, where the raw slope itself is a "
    "measured, unexplained anomaly (Phase 2).",
    "",
    "**2. The routine Bahrain stop (Case B) is 'outside' by 4.33s against an "
    "819s spread — noise at this scale, not a real disagreement.** The model "
    "is near-indifferent between lap 125 and 126 (P(best) 0.003 vs 0.997) "
    "despite the tiny median gap, because Bahrain's tightly-estimated slope "
    "makes the model highly sensitive to a single lap of tyre age. The 0.5s "
    "window tolerance, inherited unchanged from the F1 audit, is a far "
    "stricter bar at endurance race-time scale (thousands of seconds) than at "
    "F1's; a verdict should be read against the case's own spread, not the "
    "'inside/outside' label alone.",
    "",
    "**3. The fuel clock binds the window as hard as the degradation slope "
    "does.** At both Bahrain (Case A) and Imola (Case C) the recommended "
    "window sits at or just past the point the tank allows — a stop earlier "
    "than the model prefers is not on the table, mirroring the Phase 4 "
    "finding that no scoped WEC race is tyre-limited on stop count.",
    "",
    "## Scope reminders for reading these verdicts",
    "",
    "- 'OUTSIDE the recommended window' is a statement about expected race "
    "time under the model's stated scope (no rivals, no track position, a "
    "single net degradation slope, FCY/SC hazards drawn from the series-wide "
    "posterior), not a judgement on the crew that made the call.",
    "- Read a verdict's margin against its own outcome spread (p10-p90), not "
    "just the 0.5s window label — Case B shows a 'tie' can still be labelled "
    "'outside' at endurance race-time scale.",
    "- No per-car cost of *also* changing tyres vs a fuel-only splash (the "
    "measured tyre-change premium, Phase 3) is priced here — the single-stop "
    "engine still uses one flat pit loss.",
    "- A per-decision audit like F1's real-outcome comparisons (who actually "
    "won, what the rival did) is not attempted here: WEC has no rivals or "
    "track-position model, so only the stop-timing question is replayed.",
    "",
]

IMSA_ANALYSIS = [
    "## Cross-case analysis",
    "",
    "**1. The strongest-signal circuit matches the model exactly (Case B).** "
    "Road America's routine first stop lands precisely on the model's own "
    "optimum (P(best) 0.919) — the circuit with the most consistently "
    "significant degradation fit in IMSA behaves exactly as that fit "
    "predicts, with no neutralisation involved to complicate the read.",
    "",
    "**2. Both FCY-onset stops read 'outside', but for different reasons "
    "(Cases A, C).** At Watkins Glen (Case A) the model is decisive — "
    "P(best) 0.792 at lap 104 vs 0.014 at the real lap 90 — and the +7.92s "
    "gap is a real, if modest, correction: with 15 laps of fuel still in the "
    "tank, waiting past the FCY onset paid off more than boxing on it did. At "
    "Mosport (Case C) the 'outside' label is far less confident: the model's "
    "own optimum carries P(best) just 0.339 against 0.011 for the real stop "
    "— a genuine relative preference, but on a 581s p10-p90 spread that is "
    "honest uncertainty, not a confident correction, exactly matching "
    "Mosport's flat, single-season slope (its confidence interval covers "
    "zero, Phase 2).",
    "",
    "**3. Model confidence tracks the strength of its own degradation "
    "signal, not a fixed default (all three cases).** P(best) at the "
    "recommended lap runs 0.919 (Road America) -> 0.792 (Watkins Glen) -> "
    "0.339 (Mosport) — the same ordering Phase 4's own demo scenarios found, "
    "now confirmed against real stop decisions rather than a synthetic mid-"
    "race state.",
    "",
    "## Scope reminders for reading these verdicts",
    "",
    "- 'OUTSIDE the recommended window' is a statement about expected race "
    "time under the model's stated scope (no rivals, no track position, a "
    "single net degradation slope, FCY/SC hazards drawn from the series-wide "
    "posterior), not a judgement on the crew that made the call.",
    "- Read a verdict's margin against the model's own P(best) at that lap, "
    "not just the label — Case C's 'outside' carries far less confidence "
    "than Case A's.",
    "- IMSA has zero measured Safety Car events in 63 races (Phase 3); every "
    "case here concerns FCY or green-flag timing only.",
    "- No per-car cost of *also* changing tyres vs a fuel-only splash (IMSA's "
    "measured, smaller tyre-change premium, Phase 3) is priced here — the "
    "single-stop engine still uses one flat pit loss.",
    "",
]


def write_report(series: str, title: str, analysis: list[str]) -> None:
    cases = build_cases(series)
    lines = [f"# {title}", ""] + HEADER
    for case in cases:
        lines += audit_case(case)
    lines += analysis
    out = REPORTS_DIR / series / "audit_cases.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out}\n")


def main() -> int:
    write_report("wec", "WEC per-decision audit — real stop timing vs the model", WEC_ANALYSIS)
    write_report("imsa", "IMSA per-decision audit — real stop timing vs the model", IMSA_ANALYSIS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
