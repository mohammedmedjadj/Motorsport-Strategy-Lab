"""Every number in the paper, as a LaTeX macro generated from the artifacts.

A paper is the worst possible place for the failure this project keeps hitting.
Prose does not recompute, and a submitted PDF cannot be quietly corrected — so
`paper/main.tex` contains no digits at all. It says `\\NDecisions`, and this
script writes what that expands to.

The consequence is the useful one: regenerate the artifacts, regenerate this,
and the paper is correct or the drift workflow fails. There is no path where
the repository moves and the manuscript silently does not.

Writes ``paper/numbers.tex``.

Usage (offline, from the repo root)::

    python scripts/make_paper_numbers.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from src.ingestion.config import (  # noqa: E402
    DERIVED_DIR,
    ENDURANCE_DERIVED_DIR,
    F1_DERIVED_DIR,
    REPO_ROOT,
)

PAPER = REPO_ROOT / "paper"


#: Series key to a LaTeX-legal macro fragment. TeX command names accept
#: letters only, so digits have to be spelled out.
_TEX_NAMES = {"f1": "Fone", "imsa": "Imsa", "wec": "Wec", "elms": "Elms"}

#: Class code to a LaTeX-legal macro fragment, for the same reason.
_CLASS_TEX = {"GTD": "Gtd", "GTDPRO": "Gtdpro", "GTP": "Gtp",
              "HYPERCAR": "Hypercar", "LMP2": "Lmptwo",
              "LMP2 Pro/Am": "LmptwoProAm"}


def _tex_name(series: str) -> str:
    return _TEX_NAMES.get(str(series).lower(), str(series).capitalize())


def _plans() -> pd.DataFrame:
    frame = pd.read_csv(ENDURANCE_DERIVED_DIR / "multistop_plans.csv")
    frame["tyre_limited"] = frame["optimal_stops"] != frame["min_stops"]
    return frame


def _macros() -> dict[str, str]:
    """Every quantity the manuscript quotes, keyed by its macro name."""
    out: dict[str, str] = {}

    # --- scope --------------------------------------------------------------
    f1_audit = pd.read_csv(F1_DERIVED_DIR / "systematic_audit.csv")
    end_audit = pd.read_csv(ENDURANCE_DERIVED_DIR / "systematic_audit.csv")
    plans = _plans()
    loro = pd.read_csv(ENDURANCE_DERIVED_DIR / "endurance_degradation_loro.csv")
    mean_loro = loro[loro["held_out_season"].astype(str) == "MEAN"].dropna(
        subset=["r2_within"]
    )

    out["NDecisions"] = f"{len(f1_audit) + len(end_audit):,}"
    out["NDecisionsFone"] = f"{len(f1_audit):,}"
    out["NRaceSeasons"] = f"{len(plans):,}"
    out["NCircuitClasses"] = str(len(mean_loro))
    out["NClasses"] = str(plans.groupby(["series", "car_class"]).ngroups + 1)
    out["NCircuitsFone"] = str(
        pd.read_csv(F1_DERIVED_DIR / "degradation_coefficients.csv")["circuit"].nunique()
    )
    out["NCoefficientsFone"] = str(
        len(pd.read_csv(F1_DERIVED_DIR / "degradation_coefficients.csv"))
    )

    # --- R1: transfer -------------------------------------------------------
    best = mean_loro.nlargest(1, "r2_within").iloc[0]
    out["BestTransfer"] = f"{best['r2_within']:+.3f}"
    out["BestTransferWhere"] = f"{best['event']} {best['car_class']}"
    threshold = 0.2
    out["TransferThreshold"] = f"{threshold}"
    out["NTransferAboveTwo"] = str(
        int((mean_loro["r2_within"] > threshold).sum())
    )

    formal = pd.read_csv(DERIVED_DIR / "cross_series" / "formal_tests.csv")

    def row(name: str) -> pd.Series:
        return formal[formal["result"] == name].iloc[0]

    gt3, proto = row("GT3 mean LORO R2"), row("prototype mean LORO R2")
    diff = row("GT3 minus prototype")
    out["GTThreeMean"] = f"{gt3['estimate']:+.3f}"
    out["GTThreeCI"] = f"[{gt3['ci_low']:+.3f}, {gt3['ci_high']:+.3f}]"
    out["ProtoMean"] = f"{proto['estimate']:+.3f}"
    out["ProtoCI"] = f"[{proto['ci_low']:+.3f}, {proto['ci_high']:+.3f}]"
    out["TransferDiff"] = f"{diff['estimate']:+.3f}"
    out["TransferDiffCI"] = f"[{diff['ci_low']:+.3f}, {diff['ci_high']:+.3f}]"
    out["TransferP"] = f"{float(diff['p_value']):.4f}"

    # --- R2: the pit-loss rule ---------------------------------------------
    by_class = plans.groupby(["series", "car_class"]).agg(
        pit_loss=("pit_loss_s", "median"), share=("tyre_limited", "mean")
    )
    correlation = row("pit loss vs tyre-limited share (r)")
    out["PitLossR"] = f"{by_class['pit_loss'].corr(by_class['share']):.3f}"
    out["PitLossRCI"] = (
        f"[{correlation['ci_low']:+.3f}, {correlation['ci_high']:+.3f}]"
    )
    edge = plans.loc[plans["tyre_limited"], "pit_loss_s"].max()
    above = plans[plans["pit_loss_s"] > edge]
    out["CheapStopEdge"] = f"{edge:.1f}"
    out["NAboveEdge"] = str(len(above))
    out["NTyreLimitedAboveEdge"] = str(int(above["tyre_limited"].sum()))
    out["NTyreLimited"] = str(int(plans["tyre_limited"].sum()))
    second = plans.loc[plans["tyre_limited"], "pit_loss_s"].nlargest(2).iloc[-1]
    out["EdgeWithoutDefining"] = f"{second:.1f}"
    out["EdgeDropPct"] = f"{100 * (edge - second) / edge:.0f}"

    # --- R3: the audit ------------------------------------------------------
    late = f1_audit[f1_audit["delta_laps"] > 1]
    out["FoneLateShare"] = f"{100 * len(late) / len(f1_audit):.0f}"
    out["FoneLateMedian"] = f"{late['delta_laps'].median():.0f}"
    for series, group in end_audit.groupby("series"):
        name = _tex_name(str(series))
        out[f"{name}Median"] = f"{group['delta_laps'].median():+.0f}"
        out[f"{name}LateShare"] = f"{100 * (group['delta_laps'] > 1).mean():.0f}"
        out[f"{name}CautionShare"] = (
            f"{100 * group['real_stop_neutralised'].mean():.0f}"
        )

    # --- baselines ----------------------------------------------------------
    # Per class, not per championship. IMSA runs three classes at the same
    # rounds with median pit losses of 57, 24 and 40 seconds; one IMSA row
    # averages three strategy regimes into a number describing none of them.
    scored = pd.concat(
        [pd.read_csv(DERIVED_DIR / s / "baseline_comparison.csv")
         for s in ("f1", "endurance")],
        ignore_index=True,
    )
    scored["car_class"] = scored["car_class"].fillna("")
    out["NScored"] = f"{len(scored):,}"

    beaten = tied = held = 0
    for (series, car_class), group in scored.groupby(["series", "car_class"]):
        name = (_tex_name(series) if series == "f1"
                else _tex_name(series) + _CLASS_TEX.get(str(car_class), ""))
        errors = {}
        for key, column in (("Model", "model_pit_lap"), ("Bone", "b1_lap"),
                            ("Btwo", "b2_lap"), ("Bthree", "b3_lap")):
            values = (group[column] - group["real_pit_lap"]).abs().dropna()
            errors[key] = values.median() if len(values) else None
            out[f"{name}{key}Error"] = (
                f"{values.median():.0f}" if len(values) else "--"
            )
        rules = [v for k, v in errors.items() if k != "Model" and v is not None]
        if errors["Model"] is None or not rules:
            continue
        best = min(rules)
        if best < errors["Model"]:
            beaten += 1
        elif best == errors["Model"]:
            tied += 1
        else:
            held += 1

    out["NClassesRuleWins"] = str(beaten)
    out["NClassesRuleTies"] = str(tied)
    out["NClassesOptimiserWins"] = str(held)
    out["NClassesScored"] = str(beaten + tied + held)

    # Per-class median pit loss, quoted in the text to explain why the results
    # are grouped by class. Derived, because a guard caught them typed.
    for (series, car_class), group in plans.groupby(["series", "car_class"]):
        name = _tex_name(series) + _CLASS_TEX.get(str(car_class), "")
        out[f"{name}PitLoss"] = f"{group['pit_loss_s'].median():.0f}"

    # --- the cross-source check --------------------------------------------
    slope = pd.read_csv(F1_DERIVED_DIR / "slope_bias_check.csv")
    out["NIdentifiability"] = f"{slope['identifiability'].median():.3f}"

    return out


def main() -> int:
    macros = _macros()
    PAPER.mkdir(parents=True, exist_ok=True)
    lines = [
        "% GENERATED by scripts/make_paper_numbers.py -- do not edit by hand.",
        "%",
        "% Every number in main.tex is one of these macros. The manuscript",
        "% contains no digits of its own, so it cannot drift from the data the",
        "% way this project's prose repeatedly has -- regenerate the artifacts,",
        "% regenerate this file, and the paper is correct or CI fails.",
        "",
    ]
    for name, value in macros.items():
        lines.append(f"\\newcommand{{\\{name}}}{{{value}}}")
    lines.append("")

    (PAPER / "numbers.tex").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {PAPER / 'numbers.tex'} ({len(macros)} macros)")
    for name, value in list(macros.items())[:12]:
        print(f"  \\{name:24s} {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
