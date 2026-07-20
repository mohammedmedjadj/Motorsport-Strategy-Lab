"""Phase 5: replay five real strategy decisions through the simulator.

For each case: rebuild the real race state from data, simulate every
alternative, compare the model's window with what the strategists actually
did, and state plainly whether the model agrees, disagrees, or is blind.

Usage (from the repo root)::

    python scripts/run_audit.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.audit.cases import AuditCase, build_cases  # noqa: E402
from src.ingestion.config import F1_REPORTS_DIR  # noqa: E402
from src.simulator.artifacts import load_circuit_models  # noqa: E402
from src.simulator.engine import simulate  # noqa: E402
from src.simulator.recommend import summarise  # noqa: E402

N_DRAWS = 5000
SEED = 20260712


def focused_table(rec, case: AuditCase) -> str:
    """Window rows + the real decision row + the no-stop row, always."""
    keep = set(rec.window) | {case.real_pit_lap, rec.best_lap}
    if case.scenario.include_no_stop:
        keep.add(0)
    df = rec.table[rec.table["pit_lap"].isin(sorted(keep))]
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, row in df.iterrows():
        cells = [f"{row[c]:.0f}" if c == "pit_lap" else f"{row[c]:.2f}" for c in cols]
        marker = " <- real" if int(row["pit_lap"]) == case.real_pit_lap else ""
        cells[0] += marker
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def verdict(rec, case: AuditCase) -> str:
    """One quantified sentence: real choice vs model optimum."""
    real_row = rec.table[rec.table["pit_lap"] == case.real_pit_lap]
    best_row = rec.table[rec.table["pit_lap"] == rec.best_lap].iloc[0]
    if real_row.empty:
        return (
            f"The real choice (lap {case.real_pit_lap}) is outside the modelled"
            " candidate set."
        )
    real = real_row.iloc[0]
    delta = real["median_s"] - best_row["median_s"]
    label = "no further stop" if case.real_pit_lap == 0 else f"lap {case.real_pit_lap}"
    inside = case.real_pit_lap in rec.window
    return (
        f"Real choice ({label}): median cost +{delta:.2f}s vs the model optimum"
        f" (lap {rec.best_lap}); {'INSIDE' if inside else 'OUTSIDE'} the"
        f" recommended window."
    )


def audit_case(case: AuditCase, models) -> list[str]:
    model = models[case.scenario.circuit]
    rec = summarise(case.scenario, simulate(case.scenario, model, N_DRAWS, SEED))
    s = case.scenario
    ongoing = f" — {s.ongoing[0]} currently deployed" if s.ongoing else ""
    lines = [
        f"## Case {case.case_id}: {case.title}",
        "",
        f"**State (measured from data):** end of lap {s.current_lap}/{s.total_laps},"
        f" {case.driver} on {s.compound} age {s.tyre_age}{ongoing}. Rivals: "
        + "; ".join(
            f"{r.name} ({'+' if r.gap_s > 0 else ''}{r.gap_s:.1f}s, {r.compound} age"
            f" {r.tyre_age}, real plan: {'stop lap ' + str(r.pit_lap) if r.pit_lap else 'no stop'})"
            for r in s.rivals
        )
        + ".",
        "",
        f"**Real decision:** {case.real_decision}",
        "",
        f"**Question:** {case.question}",
        "",
        "**Model output** (pit_lap 0 = no further stop):",
        "",
        *[f"- {line}" for line in rec.summary_lines()],
        f"- **Verdict:** {verdict(rec, case)}",
        "",
        focused_table(rec, case),
        "",
    ]
    print(f"Case {case.case_id}: window {rec.window}")
    return lines


def main() -> int:
    models = load_circuit_models()
    lines = [
        "# Phase 5 — Retrospective decision audit",
        "",
        f"Five real decision moments replayed through the simulator ({N_DRAWS}",
        f"draws, seed {SEED}). Race states (compounds, tyre ages, gaps, rival",
        "plans) are reconstructed from the committed lap data, not quoted from",
        "memory. Rivals follow their real historical plans; the studied",
        "driver's alternatives are simulated.",
        "",
        "Reading guide: the model optimises **expected race time** under its",
        "stated scope (no SC bunching, no red flags, no track-position /",
        "overtaking model). Where reality hinged on exactly those effects, the",
        "disagreement is the finding.",
        "",
    ]
    for case in build_cases():
        lines += audit_case(case, models)

    lines += ANALYSIS
    (F1_REPORTS_DIR / "audit_cases.md").write_text("\n".join(lines), encoding="utf-8")
    print("\nWrote reports/audit_cases.md")
    return 0


#: Written after reviewing the seed-fixed outputs above; every number cited
#: is reproducible from this script (seed 20260712, 5000 draws).
ANALYSIS = [
    "## Cross-case analysis (the audit's findings)",
    "",
    "**1. Median race time alone would mis-rank real decisions; the",
    "distribution outputs are what make the audit fair (Case A).**",
    "Verstappen's real lap-17 cover costs +3.2s in median race time vs the",
    "lap-26 optimum — yet it holds the single highest P(best) (0.43 vs 0.03)",
    "and the best P(ahead of Norris) (0.70 vs 0.64). Translation: pitting",
    "early loses a little time in the median scenario but wins outright in",
    "the scenarios that matter (a later SC or a faster-than-expected Norris",
    "undercut). Red Bull paid ~3s of expected time to buy +6 points of win",
    "probability against the live threat — the model's own multi-metric",
    "output vindicates the call that its single-metric summary would flag",
    "as 'too early'.",
    "",
    "**2. Folklore correction: Norris's extended stint did not lose him",
    "Barcelona 2024 (Case B).** P(ahead of Verstappen) is flat at 0.30-0.32",
    "across every candidate stop lap, real choice included. No pit-lap",
    "choice available to Norris flips that race; his +1.45s vs optimum is",
    "noise-level. The model's verdict: the race was decided by pace and",
    "track position, not by the stop timing the post-race narrative",
    "focused on.",
    "",
    "**3. The bunching blind spot, quantified (Case C).** The model calls",
    "Sainz's universally-praised lap-20 SC stop 6.5s worse than staying out",
    "to lap 37 — and here the MODEL is wrong, for a reason documented since",
    "Phase 4: it does not model the field bunching behind the safety car.",
    "In reality the SC had already erased Sainz's 6.4s lead, so staying out",
    "would have gifted every rival a discounted stop while his own cushion",
    "was gone; the model still credits him that cushion, inflating the",
    "stay-out branch by roughly the erased lead plus queue effects. This",
    "disagreement is the audit's most useful output: it converts a known",
    "qualitative limitation into a measured ~6-7s bias for SC-window",
    "decisions at the front of a bunched field.",
    "",
    "**4. The model endorses the boldest real gamble of the set (Case D).**",
    "Russell's lap-44 VSC stop is within 1.1s of the model optimum and",
    "strictly better than staying out (median 1913.8 vs 1915.5; P(ahead",
    "Sainz) 0.47 vs 0.42; P(ahead Norris) 0.57 vs 0.54). Mercedes bought a",
    "near coin-flip for the win at roughly zero expected-time cost. History",
    "records the gamble failing on the last lap — the audit records that",
    "it was the right bet. Outcome and decision quality are different",
    "things; this case is why.",
    "",
    "**5. Monaco agrees for subtler reasons than expected (Case E).** The",
    "blind-spot case was chosen expecting disagreement, but even the pure",
    "time model keeps Leclerc out (no-stop P(best) = 0.69): Monaco's",
    "flattening degradation curve never repays a 19.1s pit loss over the",
    "remaining 38 laps. The genuine blind spots remain — the model does not",
    "know the lap-1 red flag made the no-stop strategy legal, and it",
    "assigns no value to track position — but at Monaco the physics alone",
    "already point the same way.",
    "",
    "## Scope reminders for reading these verdicts",
    "",
    "- 'OUTSIDE the recommended window' is a statement about expected race",
    "  time under the model's scope, not a judgement that strategists erred;",
    "  Cases A and C show two different resolutions of that tension (the",
    "  distributions vindicate A; a documented model limitation explains C).",
    "- Rival behaviour is frozen to history; counterfactual rival reactions",
    "  (e.g. Norris covering Verstappen's undercut) are not simulated.",
    "- Phase 2 showed degradation slopes move between seasons; verdict",
    "  margins under ~2s should be read as ties.",
    "",
]


if __name__ == "__main__":
    sys.exit(main())
