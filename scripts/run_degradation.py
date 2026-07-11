"""Run the Phase 2 degradation modelling for all scoped circuits.

For each circuit: build the modelling frame, fit degree-1 and degree-2
models, cross-validate both (leave-one-race-out), select the degree with
the lower mean CV RMSE, save the figure and export coefficients for the
Phase 4 simulator.

Outputs: ``reports/degradation_phase2.md``, ``reports/figures/*.png``,
``data/derived/degradation_coefficients.csv``.

Usage (from the repo root)::

    python scripts/run_degradation.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from src.degradation.dataset import (  # noqa: E402
    MIN_STINT_PACE_LAPS,
    TRAFFIC_TRIM_FACTOR,
    build_modelling_frame,
    load_circuit_laps,
)
from src.degradation.model import FitResult, fit_circuit  # noqa: E402
from src.degradation.plots import degradation_figure  # noqa: E402
from src.degradation.validation import FoldResult, leave_one_race_out, mean_rmse  # noqa: E402
from src.ingestion.config import DERIVED_DIR, REPORTS_DIR  # noqa: E402

CIRCUITS = ("monaco", "singapore", "barcelona", "suzuka")
DEGREES = (1, 2)


def coefficients_rows(fit: FitResult) -> list[dict[str, object]]:
    """Flatten one fit into simulator-ready coefficient rows."""
    rows: list[dict[str, object]] = []
    for compound, coefs in fit.deg_coefs.items():
        row: dict[str, object] = {
            "circuit": fit.circuit,
            "compound": compound,
            "degree": fit.degree,
            "fuel_slope_s_per_lap": fit.fuel_slope.value,
            "fuel_slope_ci_low": fit.fuel_slope.ci_low,
            "fuel_slope_ci_high": fit.fuel_slope.ci_high,
            "n_laps": fit.n_laps,
            "n_stints": fit.n_stints,
        }
        for power, coef in enumerate(coefs, start=1):
            row[f"deg_p{power}"] = coef.value
            row[f"deg_p{power}_ci_low"] = coef.ci_low
            row[f"deg_p{power}_ci_high"] = coef.ci_high
        rows.append(row)
    return rows


def fold_table(folds: list[FoldResult]) -> list[str]:
    lines = ["| Test race | RMSE (s) | within-stint R² | laps | stints |", "|---|---|---|---|---|"]
    for f in folds:
        lines.append(
            f"| {f.test_race} | {f.rmse_s:.3f} | {f.r2_within:.3f} | {f.n_laps} | {f.n_stints} |"
        )
    return lines


def main() -> int:
    report: list[str] = [
        "# Phase 2 — Tyre degradation model",
        "",
        "Fixed-effects OLS per circuit (seasons pooled): "
        "`lap_time = a_driver_race + fuel*lap_number + deg_compound(tyre_age)`.",
        "Degree (linear vs quadratic tyre-age term) selected per circuit by",
        "leave-one-race-out CV RMSE on **within-stint demeaned** lap times —",
        "the honest metric, since driver-race intercepts cannot transfer to an",
        "unseen race. Data filters: pace laps, dry compounds, traffic trim at",
        f"{TRAFFIC_TRIM_FACTOR}x driver median, stints with >= {MIN_STINT_PACE_LAPS} laps.",
        "",
    ]
    all_coef_rows: list[dict[str, object]] = []

    for circuit in CIRCUITS:
        laps = load_circuit_laps(circuit)
        frame, diag = build_modelling_frame(laps, circuit)
        print(f"{circuit}: {diag.after_min_stint} laps, {diag.n_stints} stints", flush=True)

        cv: dict[int, list[FoldResult]] = {
            d: leave_one_race_out(frame, circuit, degree=d) for d in DEGREES
        }
        selected = min(DEGREES, key=lambda d: mean_rmse(cv[d]))
        fit = fit_circuit(frame, circuit, degree=selected)
        degradation_figure(frame, fit, REPORTS_DIR / "figures" / f"degradation_{circuit}.png")
        all_coef_rows += coefficients_rows(fit)

        report += [
            f"## {circuit}",
            "",
            f"Frame: {diag.pace_laps_in} pace laps -> {diag.after_compound_filter} dry ->"
            f" {diag.after_traffic_trim} after traffic trim -> {diag.after_min_stint} in stints"
            f" >= {MIN_STINT_PACE_LAPS} laps ({diag.n_stints} stints, {diag.n_driver_races}"
            " driver-races).",
            "",
            f"**Selected degree: {selected}** "
            f"(CV RMSE {mean_rmse(cv[selected]):.3f}s vs "
            f"{mean_rmse(cv[3 - selected]):.3f}s for degree {3 - selected}). "
            f"Overall fit R² = {fit.r2_overall:.3f} (inflated by fixed effects; see CV).",
            "",
            f"Fuel-burn proxy: {fit.fuel_slope.value:+.4f} s/lap "
            f"[{fit.fuel_slope.ci_low:+.4f}, {fit.fuel_slope.ci_high:+.4f}].",
            "",
            "Degradation coefficients (s per lap of tyre age, 95% CI):",
            "",
            "| Compound | " + " | ".join(f"t^{p}" for p in range(1, selected + 1)) + " |",
            "|---|" + "---|" * selected,
        ]
        for compound, coefs in fit.deg_coefs.items():
            cells = " | ".join(
                f"{c.value:+.4f} [{c.ci_low:+.4f}, {c.ci_high:+.4f}]" for c in coefs
            )
            report.append(f"| {compound} | {cells} |")
        report += ["", f"CV folds (degree {selected}):", ""]
        report += fold_table(cv[selected])
        report += [
            "",
            f"![degradation {circuit}](figures/degradation_{circuit}.png)",
            "",
        ]

    report += [
        "## Interpreting the CV numbers (read before using the coefficients)",
        "",
        "- **CV RMSE (~0.55-1.3 s/lap)** is the lap-level noise any consumer of",
        "  this model must expect around a pace prediction; Phase 4 uses it as",
        "  the stochastic lap-noise scale per circuit.",
        "- **Within-stint R² is frequently negative on real data**, while the",
        "  identical pipeline scores ~0.85 on synthetic data at its noise floor",
        "  (see `tests/test_degradation.py`). Meaning: a degradation trend",
        "  fitted on two seasons often predicts a third season's within-stint",
        "  evolution no better than a flat line. Season-specific conditions",
        "  (temperatures, resurfacing, tyre-construction changes) materially",
        "  move the true slope. This is a finding, not a failure — and it is",
        "  the reason the simulator treats degradation as uncertain.",
        "- **Consequence for Phase 4:** coefficients enter the simulator as",
        "  distributions (via their CIs), never as trusted point values, and",
        "  pit-window recommendations inherit that uncertainty.",
        "- **Consequence for Phase 5:** real strategists' decisions must not be",
        "  audited as if the true degradation slope had been knowable in-race.",
        "",
        "## Limitations (stated, not hidden)",
        "",
        "- **Fuel and tyre age are separated only through the fixed-effects",
        "  structure** (stints starting at different lap numbers); the fuel",
        "  slope is a proxy that also absorbs track evolution, which grips up",
        "  over the race. The two cannot be fully disentangled from timing",
        "  data alone.",
        "- **Classical (homoscedastic) standard errors**; lap-time noise is",
        "  heteroscedastic (traffic, weather drift), so CIs are approximate.",
        "- **Track temperature is not a regressor** in the MVP; its effect is",
        "  absorbed by race fixed effects (between races) and residual noise",
        "  (within a race).",
        "- **Compound allocation is not random**: teams fit HARD when they",
        "  plan long stints. Slopes are descriptive of observed usage, not",
        "  causal effects of compound choice.",
        "- Within-stint R² is low where degradation is genuinely small",
        "  (street circuits): when the true signal is ~0.02 s/lap, noise",
        "  dominates and R² near zero is the honest outcome, not a failure.",
        "",
    ]

    pd.DataFrame(all_coef_rows).to_csv(
        DERIVED_DIR / "degradation_coefficients.csv", index=False
    )
    (REPORTS_DIR / "degradation_phase2.md").write_text("\n".join(report), encoding="utf-8")
    print(f"\nWrote reports/degradation_phase2.md and {len(all_coef_rows)} coefficient rows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
