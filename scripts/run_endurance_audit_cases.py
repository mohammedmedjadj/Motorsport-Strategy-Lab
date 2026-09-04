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


def case_facts(case: EnduranceAuditCase, table: pd.DataFrame,
               best_lap: int, window: tuple[int, ...]) -> dict[str, float | int | bool]:
    """The numbers the cross-case analysis quotes, taken from the case itself.

    The analysis used to be a hand-written list of strings, and it drifted the
    way hand-written prose about computed values always does. It claimed both
    Safety-Car-onset stops were endorsed "decisively so — P(best) 0.84 and
    0.91": 0.84 was the P(best) of the lap the *model* preferred, not the lap
    the team took (which was 0.068), and 0.91 appeared nowhere in the table at
    all. Now the analysis is a function of these.
    """
    real = table[table["pit_lap"] == case.real_pit_lap]
    best = table[table["pit_lap"] == best_lap].iloc[0]
    return {
        "real_pit_lap": int(case.real_pit_lap),
        "best_lap": int(best_lap),
        "real_p_best": float(real.iloc[0]["p_best"]) if not real.empty else float("nan"),
        "best_p_best": float(best["p_best"]),
        "real_median_cost_s": (
            float(real.iloc[0]["median_s"] - best["median_s"])
            if not real.empty else float("nan")
        ),
        "inside_window": bool(case.real_pit_lap in window),
        "spread_s": float(best["p90_s"] - best["p10_s"]),
    }


def audit_case(case: EnduranceAuditCase) -> tuple[list[str], dict]:
    table = simulate(case.scenario, case.model, n_draws=N_DRAWS, seed=SEED)
    best_lap, window = window_and_best(table)
    facts = case_facts(case, table, best_lap, window)
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
    return lines, facts


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
def _endorsement(fact: dict, label: str) -> str:
    """One case's verdict, stated on both statistics rather than one.

    They can disagree sharply and that disagreement is the point. A stop can
    sit inside the recommended window on median cost -- materially indifferent
    -- while its P(best) is small, because P(best) is an argmin over draws and
    splits almost all its mass onto whichever near-identical candidate wins
    most often. Quoting P(best) alone as "decisively endorsed" reads a
    coin-flip between two laps 0.05 s apart as a strong preference.
    """
    inside = "inside" if fact["inside_window"] else "outside"
    return (
        f"**{label}** — real lap {fact['real_pit_lap']}, "
        f"{inside} the window at +{fact['real_median_cost_s']:.2f} s against "
        f"the model's lap {fact['best_lap']}; P(best) "
        f"{fact['real_p_best']:.3f} for the real lap against "
        f"{fact['best_p_best']:.3f} for the model's."
    )


def WEC_ANALYSIS(facts: list[dict]) -> list[str]:
    """Cross-case analysis for WEC, quoting the cases it just computed."""
    a, c = facts[0], facts[2]
    decisive = [f for f in (a, c) if f["real_p_best"] > 0.5]
    return [
        "## Cross-case analysis",
        "",
        "**1. Opportunistic caution stops sit inside the model's window at both "
        "circuits — including the anomalous-slope one (Cases A, C).** "
        + _endorsement(a, "Bahrain 2025") + " " + _endorsement(c, "Imola 2024") +
        " The engine prices a caution stop's opportunity cost the same way "
        "regardless of the sign of the degradation slope, so the strategists' "
        "instinct to box the moment the flag changes holds up even at Imola, "
        "where the raw slope is a measured, unexplained anomaly (Phase 2).",
        "",
        "**The two statistics disagree, and that is worth more than either "
        f"alone.** {len(decisive)} of these two real stops carries a P(best) "
        "above 0.5, yet both are inside the window on median cost. The reason is "
        "structural: P(best) is an argmin over draws, so when two candidate laps "
        "differ by hundredths of a second in median race time it hands nearly all "
        "its mass to whichever wins marginally more often. Reading that as a "
        "strong preference would be reading a coin flip as a verdict — and an "
        "earlier version of this section did exactly that, quoting the *model's* "
        "P(best) as though it were the team's.",
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

def IMSA_ANALYSIS(facts: list[dict]) -> list[str]:
    """Cross-case analysis for IMSA GTP, quoting the cases it just computed.

    Six numbers in this section had drifted from the tables directly above
    them: P(best) 0.919 for 0.918, 0.792 for 0.791, +7.92 s for +7.81 s, and
    -- the one that changed a qualitative claim -- 0.339 for 0.240, a 29%
    relative error supporting the words "far less confident". All correct when
    typed, all stale the moment the inputs moved, none noticed because the
    table and the paragraph were written by different mechanisms.
    """
    glen, road_america, mosport = facts[0], facts[1], facts[2]
    ordering = " -> ".join(
        f"{fact['best_p_best']:.3f} ({name})"
        for name, fact in (("Road America", road_america),
                           ("Watkins Glen", glen),
                           ("Mosport", mosport))
    )
    return [
        "## Cross-case analysis",
        "",
        "**1. The strongest-signal circuit matches the model exactly (Case B).** "
        "Road America's routine first stop lands precisely on the model's own "
        f"optimum (P(best) {road_america['real_p_best']:.3f}) — the circuit with "
        "the most consistently significant degradation fit in IMSA behaves "
        "exactly as that fit predicts, with no neutralisation involved to "
        "complicate the read.",
        "",
        "**2. Both FCY-onset stops read 'outside', but for different reasons "
        "(Cases A, C).** At Watkins Glen (Case A) the model is decisive — "
        f"P(best) {glen['best_p_best']:.3f} at lap {glen['best_lap']} vs "
        f"{glen['real_p_best']:.3f} at the real lap {glen['real_pit_lap']} — and "
        f"the +{glen['real_median_cost_s']:.2f}s gap is a real, if modest, "
        "correction: with 15 laps of fuel still in the tank, waiting past the FCY "
        "onset paid off more than boxing on it did. At Mosport (Case C) the "
        "'outside' label is far less confident: the model's own optimum carries "
        f"P(best) just {mosport['best_p_best']:.3f} against "
        f"{mosport['real_p_best']:.3f} for the real stop — a genuine relative "
        f"preference, but on a {mosport['spread_s']:.0f}s p10-p90 spread that is "
        "honest uncertainty, not a confident correction, exactly matching "
        "Mosport's flat, single-season slope (its confidence interval covers "
        "zero, Phase 2).",
        "",
        "**3. Model confidence tracks the strength of its own degradation "
        "signal, not a fixed default (all three cases).** P(best) at the "
        f"recommended lap runs {ordering} — the same ordering Phase 4's own demo "
        "scenarios found, now confirmed against real stop decisions rather than a "
        "synthetic mid-race state.",
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


GT3_ANALYSIS = [
    "## What these two cases show",
    "",
    "Both circuits are tyre-limited: the exact dynamic program wants more "
    "stops than the fuel minimum, which no prototype race in scope ever "
    "reaches. The single-stop engine cannot express \"stop more often\", so "
    "read its window as where the *next* stop belongs given that pressure, "
    "not as agreement or disagreement with the full plan.",
    "",
    "The two layers of the model disagree with each other at VIR, and saying "
    "so is more useful than picking one. The full-race dynamic program wants "
    "five stops where the winner took three and the fuel minimum is two — "
    "stop *more often*. The single-stop engine, asked about the lap-28 "
    "decision in isolation, wants that particular stop **later** (lap 40, "
    "+14.24 s). Both are consistent: more stops overall and each one later is "
    "only contradictory if you assume the extra visits come at the front of "
    "the race, and nothing in the DP says they do.",
    "",
    "What neither layer has is a term for track position. A time-only optimum "
    "cannot price what two extra stops cost on a short circuit where passing "
    "is hard, which is the same limitation the F1 audit documents at Monaco. "
    "A gap this size is a question about the model as much as about the "
    "strategy.",
    "",
]

ELMS_ANALYSIS = [
    "## What these two cases show",
    "",
    "Mugello 2024 produced the only double stop under caution in any audited "
    "race here, and both class winners made it independently — laps 66 and 67 "
    "under the same Safety Car, in LMP2 and in LMP2 Pro/Am. The engine models "
    "one stop, so it can price the first and is structurally silent on the "
    "second. That silence is the finding worth recording: a real strategy "
    "existed that this model has no way to represent.",
    "",
    "It also disagrees with the first stop, and by a lot — +19.71 s for LMP2 "
    "and +16.16 s for Pro/Am against an optimum of lap 84 in both. The engine "
    "discounts a neutralised stop by the pace ratio but has no rivals in it, "
    "so it cannot see the reason teams take one: everyone else is queued "
    "behind a Safety Car and the *relative* cost is what collapses, not the "
    "absolute one. Two independent class winners made the same call, which is "
    "the strongest signal available that the omission matters here.",
    "",
    "One thing the two cases agree on exactly: the recommended window is lap "
    "83-84 for both classes, at the same event, in the same conditions. The "
    "crew-rating comparison found no consistent effect across championships, "
    "and at the level of a single decision the model sees no difference at "
    "all.",
    "",
    "ELMS is the most Safety-Car-dominated series in scope — 23 of 29 races "
    "see one, against WEC's 19 of 33 and IMSA's none at all — so the value of "
    "a neutralised stop is higher here than anywhere else this project models.",
    "",
]


def write_report(series: str, title: str, analysis,
                 out_dir: str | None = None, filename: str = "audit_cases.md") -> None:
    """``out_dir`` separates the *scope key* from where its report lives: the
    GT3 cases are IMSA's classes, not a series, so they belong in reports/imsa/
    under their own filename rather than inventing a reports/gt3/ directory."""
    cases = build_cases(series)
    lines = [f"# {title}", ""] + HEADER
    facts = []
    for case in cases:
        case_lines, case_fact = audit_case(case)
        lines += case_lines
        facts.append(case_fact)
    # `analysis` may be a plain list -- prose that quotes no computed value --
    # or a callable that receives every case's numbers. The callable form
    # exists because the static form silently went stale: see case_facts().
    lines += analysis(facts) if callable(analysis) else analysis
    out = REPORTS_DIR / (out_dir or series) / filename
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out}\n")


def main() -> int:
    write_report("wec", "WEC per-decision audit — real stop timing vs the model", WEC_ANALYSIS)
    # Every one of these cases is GTP, and reports/imsa/gtp/ is where every
    # other GTP phase report lives. Writing to the series root left a stale
    # hand-copied duplicate in gtp/ that nothing regenerated -- it sat there
    # for three weeks carrying six numbers that had since drifted, in exactly
    # the directory a GTP reader navigates to.
    write_report("imsa", "IMSA GTP per-decision audit — real stop timing vs the model",
                 IMSA_ANALYSIS, out_dir="imsa/gtp")
    write_report(
        "gt3",
        "IMSA GT3 per-decision audit — GTD and GTD PRO, where an extra stop can pay",
        GT3_ANALYSIS, out_dir="imsa", filename="gt3_audit_cases.md",
    )
    write_report(
        "elms",
        "ELMS per-decision audit — real stop timing vs the model",
        ELMS_ANALYSIS, out_dir="elms",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())