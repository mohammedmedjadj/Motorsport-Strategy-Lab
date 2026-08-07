"""Phase 5: replay five real strategy decisions through the simulator.

For each case: rebuild the real race state from data, simulate every
alternative, compare the model's window with what the strategists actually
did, and state plainly whether the model agrees, disagrees, or is blind.

Usage (from the repo root)::

    python scripts/run_audit.py
"""

from __future__ import annotations

import sys
import textwrap
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


def case_facts(rec, case: AuditCase) -> dict[str, float]:
    """The handful of numbers the cross-case narrative quotes.

    Extracted from the simulation rather than typed into the prose. The
    narrative below used to carry them as literals, which meant every one of
    them silently went stale the moment the coefficients behind them changed
    -- and they did, when the degradation standard errors went cluster-robust.
    A generated report must not contain a hand-written number.
    """
    table = rec.table
    real = table[table["pit_lap"] == case.real_pit_lap]
    best = table[table["pit_lap"] == rec.best_lap].iloc[0]
    out: dict[str, float] = {"best_lap": float(rec.best_lap)}
    if real.empty:
        return out
    real = real.iloc[0]
    out["cost_s"] = float(real["median_s"] - best["median_s"])
    out["real_median_s"] = float(real["median_s"])
    out["best_median_s"] = float(best["median_s"])
    out["top_p_best"] = float(table["p_best"].max())
    out["top_p_best_lap"] = float(table.loc[table["p_best"].idxmax(), "pit_lap"])
    for col in table.columns:
        if col.startswith("p_best") or col.startswith("p_ahead"):
            out[f"real_{col}"] = float(real[col])
            out[f"best_{col}"] = float(best[col])
        if col.startswith("p_ahead"):
            out[f"max_{col}"] = float(table[col].max())
            out[f"max_{col}_lap"] = float(table.loc[table[col].idxmax(), "pit_lap"])
            out[f"min_{col}"] = float(table[col].min())
    if case.scenario.include_no_stop and (table["pit_lap"] == 0).any():
        row = table[table["pit_lap"] == 0].iloc[0]
        out["nostop_median_s"] = float(row["median_s"])
    return out


def audit_case(case: AuditCase, models, facts: dict[str, dict[str, float]]) -> list[str]:
    model = models[case.scenario.circuit]
    rec = summarise(case.scenario, simulate(case.scenario, model, N_DRAWS, SEED))
    facts[case.case_id] = case_facts(rec, case)
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
    facts: dict[str, dict[str, float]] = {}
    for case in build_cases():
        lines += audit_case(case, models, facts)

    lines += analysis(facts)
    (F1_REPORTS_DIR / "audit_cases.md").write_text("\n".join(lines), encoding="utf-8")
    print("\nWrote reports/audit_cases.md")
    return 0


def analysis(f: dict[str, dict[str, float]]) -> list[str]:
    """The cross-case findings, with every number computed from the run above.

    This block used to be a list of literal strings written after reading one
    set of outputs. That made it a hand-written section inside a generated
    report: correct on the day, and silently wrong from the first time the
    inputs moved. They did move — when the degradation standard errors went
    cluster-robust — and it changed two of the findings below, not just their
    decimals.

    Paragraphs are written as single strings and wrapped on the way out, so
    the prose stays readable no matter how wide a formatted number turns out
    to be.
    """
    a, b, c, d, e = (f[k] for k in "ABCDE")
    # The narrative quotes each real choice's own table row. ``case_facts``
    # returns only ``best_lap`` when that row is off-table -- a branch
    # ``verdict()`` handles explicitly -- so name the case that broke rather
    # than dying on a KeyError three frames deeper.
    for case_id, facts in zip("ABCDE", (a, b, c, d, e)):
        if "cost_s" not in facts:
            raise RuntimeError(
                f"Case {case_id}: the real pit lap is outside the modelled "
                "candidate set, so the cross-case narrative cannot quote it. "
                "Fix the case definition rather than the report."
            )
    for case_id, facts in (("D", d), ("E", e)):
        if "nostop_median_s" not in facts:
            raise RuntimeError(
                f"Case {case_id}: the narrative compares against staying out, "
                "but this scenario no longer includes the no-stop candidate."
            )

    # Claims that could stop being true are decided from the numbers rather
    # than from memory of one run -- the same discipline as the figures.
    a_p_best_phrase = (
        "it is not merely competitive but the outright winner"
        if a["real_p_best"] >= a["top_p_best"] - 1e-9
        else f"it is beaten by lap {int(a['top_p_best_lap'])} ({a['top_p_best']:.3f})"
    )
    b_phrase = (
        "never reaches 0.5 at any candidate stop lap"
        if b["max_p_ahead_VER"] < 0.5
        else "now reaches 0.5 at some candidate stop lap, which it did not "
             "when this finding was first written"
    )
    d_phrase = (
        "both above"
        if d["real_p_ahead_SAI"] > d["best_p_ahead_SAI"]
        and d["real_p_ahead_NOR"] > d["best_p_ahead_NOR"]
        else "against"
    )

    paragraphs = [
        "**1. Three metrics, three different answers — which is the whole "
        "argument for reporting a distribution (Case A).** "
        f"Verstappen's real lap-17 cover costs +{a['cost_s']:.2f}s in median "
        f"race time against the lap-{int(a['best_lap'])} optimum. On P(best) "
        f"{a_p_best_phrase}: {a['real_p_best']:.3f} against "
        f"{a['best_p_best']:.3f} for the median-optimal lap. On P(ahead of "
        "Norris) it is neither: lap 17 "
        f"gives {a['real_p_ahead_NOR']:.3f} where lap "
        f"{int(a['max_p_ahead_NOR_lap'])} would have given "
        f"{a['max_p_ahead_NOR']:.3f}.",

        "So the three summaries rank the same decision first, middling and "
        "not-quite-best. Pitting early loses a little expected time, wins "
        "outright in the scenarios that decide races (a later safety car, a "
        "faster-than-expected Norris undercut), and is not the sharpest "
        "available bet on the head-to-head. Any single-number verdict on this "
        "call — including the flattering one — is an artefact of which number "
        "was chosen.",

        "**2. Folklore correction: Norris's extended stint did not lose him "
        f"Barcelona 2024 (Case B).** P(ahead of Verstappen) {b_phrase}: it "
        f"runs {b['min_p_ahead_VER']:.3f} to "
        f"{b['max_p_ahead_VER']:.3f}, his real lap-23 choice sitting at "
        f"{b['real_p_ahead_VER']:.3f} against a best-available "
        f"{b['max_p_ahead_VER']:.3f} at lap {int(b['max_p_ahead_VER_lap'])}. No "
        "pit lap available to him makes him the favourite, and his "
        f"+{b['cost_s']:.2f}s against the optimum is small beside that. The race "
        "was decided by pace and track position, not by the stop timing the "
        "post-race narrative focused on.",

        "**3. The bunching blind spot, quantified (Case C).** The model calls "
        f"Sainz's universally-praised lap-20 safety-car stop {c['cost_s']:.2f}s "
        f"worse than stopping at lap {int(c['best_lap'])} — and here the MODEL "
        "is wrong, for a reason documented since Phase 4: it does not model the "
        "field bunching behind the safety car. In reality the SC had already "
        "erased Sainz's 6.4s lead, so staying out would have gifted every rival "
        "a discounted stop while his own cushion was gone; the model still "
        "credits him that cushion. This disagreement is the audit's most useful "
        "output: it turns a known qualitative limitation into a measured "
        f"~{c['cost_s']:.0f}s bias for SC-window decisions at the front of a "
        "bunched field.",

        "**4. The model endorses the boldest real gamble of the set (Case D).** "
        f"Russell's lap-44 VSC stop is within {d['cost_s']:.2f}s of the model "
        f"optimum and beats staying out on median time ({d['real_median_s']:.1f} "
        f"against {d['nostop_median_s']:.1f}). It also buys the head-to-heads "
        f"the stop was for: P(ahead of Sainz) {d['real_p_ahead_SAI']:.3f} and "
        f"P(ahead of Norris) {d['real_p_ahead_NOR']:.3f}, {d_phrase} what the "
        f"median-optimal lap returns ({d['best_p_ahead_SAI']:.3f} and "
        f"{d['best_p_ahead_NOR']:.3f}). Mercedes bought a near coin-flip for the "
        "win at roughly zero expected-time cost. History records the crash; the "
        "decision was sound.",

        "**5. The declared blind spot, stated as one (Case E).** At Monaco 2024 "
        f"the model puts the real no-stop within {e['cost_s']:.2f}s of its own "
        f"optimum and gives it P(best) {e['real_p_best']:.3f}, "
        f"{'the highest of any candidate' if e['real_p_best'] >= e['top_p_best'] - 1e-9 else 'behind lap ' + str(int(e['top_p_best_lap']))}"
        ". That agreement is not a success. The model "
        "has no track-position term, and the reason nobody stopped was that "
        "overtaking at Monaco is close to impossible — not that the lap times "
        "happened to work out. A time-only model reaching the right answer for "
        "the wrong reason is exactly the case that has to be read as a "
        "limitation rather than a validation.",
    ]
    lines = ["## Cross-case analysis (the audit's findings)", ""]
    for para in paragraphs:
        lines += [textwrap.fill(para, width=75), ""]
    return lines


if __name__ == "__main__":
    sys.exit(main())
