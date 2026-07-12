"""Phase 4 demo: one pit-window recommendation per circuit.

Scenarios are illustrative (mid-race, worn MEDIUM, one rival each way) —
the point is to demonstrate the full uncertainty-propagating pipeline on
real artifacts, not to audit real decisions (that is Phase 5).

Usage (from the repo root)::

    python scripts/run_simulator_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ingestion.config import REPORTS_DIR  # noqa: E402
from src.simulator.artifacts import load_circuit_models  # noqa: E402
from src.simulator.engine import RivalSpec, Scenario, simulate  # noqa: E402
from src.simulator.recommend import summarise, table_markdown  # noqa: E402

#: Race lengths (scheduled laps) from data/derived/sessions.csv.
RACE_LAPS = {"monaco": 78, "singapore": 62, "barcelona": 66, "suzuka": 53}

N_DRAWS = 5000
SEED = 20260712


def demo_scenario(circuit: str, total_laps: int) -> Scenario:
    """Mid-race decision point: worn MEDIUM, one rival ahead, one behind."""
    current = total_laps // 3
    return Scenario(
        circuit=circuit,
        current_lap=current,
        total_laps=total_laps,
        compound="MEDIUM",
        tyre_age=current,  # started the race on this set
        target_compound="HARD",
        rivals=(
            RivalSpec("car_ahead", gap_s=2.5, compound="MEDIUM", tyre_age=current,
                      pit_lap=current + 8, target_compound="HARD"),
            RivalSpec("car_behind", gap_s=-3.0, compound="MEDIUM", tyre_age=current,
                      pit_lap=current + 5, target_compound="HARD"),
        ),
    )


def main() -> int:
    models = load_circuit_models()
    lines = [
        "# Phase 4 — Monte Carlo strategy simulator",
        "",
        f"{N_DRAWS} draws per scenario, seed {SEED} (bit-reproducible).",
        "Per draw, the engine resamples: degradation/fuel coefficients from",
        "their Phase 2 CIs, SC/VSC per-lap hazards from their Phase 3 Gamma",
        "posteriors, neutralisation durations from observed events, and lap",
        "noise at the Phase 2 CV RMSE. Candidates share realisations (common",
        "random numbers), so P(best) is a clean per-draw argmin.",
        "",
        "## Data-derived inputs (measured, not assumed)",
        "",
        "| Circuit | Green pace (s) | Pit loss (s, n) | SC pace ratio | VSC pace ratio | Lap noise (s) |",
        "|---|---|---|---|---|---|",
    ]
    for circuit, m in sorted(models.items()):
        pooled_sc = " (pooled)" if m.pace_ratios.used_pooled_sc else ""
        pooled_vsc = " (pooled)" if m.pace_ratios.used_pooled_vsc else ""
        lines.append(
            f"| {circuit} | {m.green_pace_s:.1f} | {m.pit_loss.median_s:.1f} "
            f"(n={m.pit_loss.n_events}) | {m.pace_ratios.sc_ratio:.2f}{pooled_sc} "
            f"| {m.pace_ratios.vsc_ratio:.2f}{pooled_vsc} | {m.lap_noise_s:.2f} |"
        )
    lines += [
        "",
        "## Demo scenarios",
        "",
        "Illustrative state: one third into the race on the starting MEDIUM,",
        "target HARD; a rival 2.5s ahead planning to stop in 8 laps and one",
        "3.0s behind planning to stop in 5.",
        "",
    ]

    for circuit, m in sorted(models.items()):
        scenario = demo_scenario(circuit, RACE_LAPS[circuit])
        rec = summarise(scenario, simulate(scenario, m, n_draws=N_DRAWS, seed=SEED))
        lines += [
            f"### {circuit} (lap {scenario.current_lap}/{scenario.total_laps}, "
            f"MEDIUM age {scenario.tyre_age} -> HARD)",
            "",
            *[f"- {s}" for s in rec.summary_lines()],
            "",
            table_markdown(rec),
            "",
        ]
        print(f"{circuit}: best lap {rec.best_lap}, window {rec.window}")

    lines += [
        "## Model scope (assumptions restated)",
        "",
        "- Field bunching behind the SC (gap resets) is NOT modelled; the",
        "  simulator captures the discounted-stop effect only. Recommendations",
        "  in SC-heavy scenarios are conservative about SC upside.",
        "- Red flags, traffic loss on rejoin, and tyre warm-up laps are out",
        "  of scope (each documented in earlier phases or here).",
        "- Rivals follow fixed announced plans; no strategic reaction.",
        "- One remaining stop; compound-usage rules are the user's job.",
        "",
    ]
    (REPORTS_DIR / "simulator_phase4.md").write_text("\n".join(lines), encoding="utf-8")
    print("\nWrote reports/simulator_phase4.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
