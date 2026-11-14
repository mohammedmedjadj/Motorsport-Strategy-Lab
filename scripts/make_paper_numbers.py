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

import inspect
import pathlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.reporting.names import circuit as circuit_name  # noqa: E402
from src.reporting.names import circuit_class as circuit_class_name  # noqa: E402
from src.ingestion.config import (  # noqa: E402
    DERIVED_DIR,
    ENDURANCE_DERIVED_DIR,
    F1_DERIVED_DIR,
    REPO_ROOT,
    REPORTS_DIR,
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

    # --- scope, per series, for the methods table ------------------------
    import glob
    import re as _re

    # The F1 models, the transfer layers and the audit all use the seasons
    # before the 2026 rules; races from 2026 are ingested but not modelled.
    from src.ingestion.config import PRE_ERA_SEASONS as _PRE

    all_f1 = sorted(glob.glob(str(F1_DERIVED_DIR / "laps_*.csv")))
    f1_files = [f for f in all_f1
                if int(_re.search(r"laps_(\d{4})_", pathlib.Path(f).name).group(1)) in _PRE]
    out["NRacesFoneHeldOut"] = str(len(all_f1) - len(f1_files))
    f1_years = sorted({
        int(_re.search(r"laps_(\d{4})_", pathlib.Path(f).name).group(1))
        for f in f1_files
    })
    out["NRacesFone"] = str(len(f1_files))
    out["SeasonsFone"] = f"{f1_years[0]}--{f1_years[-1]}"
    out["NDecisionsFoneScope"] = f"{len(f1_audit):,}"

    for series, group in plans.groupby("series"):
        name = _tex_name(series)
        out[f"NRaces{name}"] = str(len(group))
        out[f"Seasons{name}"] = f"{group['year'].min()}--{group['year'].max()}"
        out[f"NClasses{name}"] = str(group["car_class"].nunique())
        out[f"NCircuits{name}"] = str(group["circuit_canonical"].nunique())
        decisions = end_audit[end_audit["series"] == series]
        out[f"NDecisions{name}"] = f"{len(decisions):,}"

    # --- protocol constants, read from the code that uses them -----------
    from src.audit.systematic import (
        LOOKBACK as F1_LOOKBACK,
        MIN_FIRST_STOP_LAP as F1_MIN_STOP,
        N_FINISHERS,
        N_RIVALS,
    )
    from src.audit.systematic_endurance import (
        LOOKBACK as END_LOOKBACK,
        MIN_FIRST_STOP_LAP as END_MIN_STOP,
        N_CARS,
    )
    from src.simulator.engine import simulate as _simulate

    out["NFinishers"] = str(N_FINISHERS)
    out["NCars"] = str(N_CARS)
    out["LookbackFone"] = str(F1_LOOKBACK)
    out["LookbackEnd"] = str(END_LOOKBACK)
    out["MinFirstStopFone"] = str(F1_MIN_STOP)
    out["MinFirstStopEnd"] = str(END_MIN_STOP)
    out["NRivals"] = str(N_RIVALS)
    out["NDraws"] = f"{inspect.signature(_simulate).parameters['n_draws'].default:,}"
    out["MinFinalStint"] = str(
        inspect.signature(_simulate).parameters["min_final_stint"].default
    )

    # --- how well resolved the Formula 1 degradation fit actually is -------
    # The paper shows this figure and would be dishonest to show it without
    # saying how much of it is indistinguishable from zero.
    coefs = pd.read_csv(F1_DERIVED_DIR / "degradation_coefficients.csv")
    crosses = (coefs["deg_p1_ci_low"] <= 0) & (coefs["deg_p1_ci_high"] >= 0)
    out["NCoefCrossingZero"] = str(int(crosses.sum()))
    out["PctCoefCrossingZero"] = f"{100 * crosses.mean():.0f}"

    # --- the same accounting for the endurance fits -------------------------
    # The Formula 1 figure above has carried this caveat since it was first
    # shown; the endurance figure has not, and its numbers are worse. Each
    # championship gets its own macros. There is deliberately no pooled
    # endurance figure: WEC, IMSA and ELMS run different calendars and
    # different classes, and an average over the three describes none of them.
    fits = pd.read_csv(ENDURANCE_DERIVED_DIR / "endurance_degradation_fits.csv")
    fits["crosses_zero"] = (fits["ci_low"] <= 0) & (fits["ci_high"] >= 0)
    for series, suffix in (("wec", "Wec"), ("imsa", "Imsa"), ("elms", "Elms")):
        part = fits[fits["series"] == series]
        out[f"NFits{suffix}"] = str(len(part))
        out[f"NSlopeZero{suffix}"] = str(int(part["crosses_zero"].sum()))
        out[f"PctSlopeZero{suffix}"] = f"{100 * part['crosses_zero'].mean():.0f}"
        out[f"NSlopeNegative{suffix}"] = str(int((part["net_slope"] < 0).sum()))
        out[f"PctSlopeNegative{suffix}"] = f"{100 * (part['net_slope'] < 0).mean():.0f}"
        out[f"NSeparable{suffix}"] = str(int(part["separable"].sum()))
        out[f"MedFuelDegCorr{suffix}"] = f"{part['fuel_deg_corr'].median():.3f}"

    overlapping = total = 0
    for _, group in coefs.groupby("circuit"):
        rows = list(group.itertuples())
        for index, first in enumerate(rows):
            for second in rows[index + 1:]:
                total += 1
                if (first.deg_p1_ci_low <= second.deg_p1_ci_high
                        and second.deg_p1_ci_low <= first.deg_p1_ci_high):
                    overlapping += 1
    out["PctCompoundOverlap"] = f"{100 * overlapping / total:.0f}"

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

    # --- what family that p-value was selected from -------------------------
    # The first thing a reviewer asks about a p-value. Counted against the
    # most adversarial family that can be argued for: every binary partition
    # of the endurance car classes, as though the car-type split had been
    # found by searching them. See reports/cross_series/formal_tests.md.
    p_value = float(diff["p_value"])
    n_partitions = (2 ** (int(out["NClasses"]) - 1) - 2) // 2
    out["NReportedTests"] = "5"
    out["NClassPartitions"] = str(n_partitions)
    out["TransferPBonferroni"] = f"{p_value * n_partitions:.3f}"
    out["BonferroniBreakeven"] = f"{0.05 / p_value:.0f}"

    # --- R2: which term of the comparison actually decides the regime ------
    # The answer to the circularity objection, and it has to be a measurement
    # rather than an argument. See reports/cross_series/regime_decomposition.md,
    # including the third candidate that was thrown out for scoring 1.000 by
    # construction.
    regime = pd.read_csv(DERIVED_DIR / "cross_series" / "regime_decomposition.csv")
    labels = {"pit loss": "PitLoss", "net degradation slope": "Slope"}
    # `row` is a function in this scope; shadowing it cost a debugging pass
    # here once already.
    for _, discriminator in regime.iterrows():
        suffix = labels[discriminator["quantity"]]
        out[f"RegimeAuc{suffix}"] = f"{discriminator['auc']:.3f}"
        out[f"RegimeAuc{suffix}CI"] = (
            f"[{discriminator['ci_low']:.3f}, {discriminator['ci_high']:.3f}]"
        )
    out["RegimeNTyreLimited"] = str(int(regime["n_tyre_limited"].iloc[0]))
    out["RegimeNFuelLimited"] = str(int(regime["n_fuel_limited"].iloc[0]))

    # --- R3: the third candidate explanation, and how it failed -----------
    # Salminen's position-keeping defence, replayed on the same first-stop
    # decisions. Every figure the subsection quotes is derived here, including
    # the ones describing the defects found while building it -- a number about
    # a bug drifts exactly like any other number, and one of these already did.
    d1 = pd.read_csv(F1_DERIVED_DIR / "d1_defence.csv")
    chasers = d1[d1["role"] == "chaser"]
    predicted = chasers[chasers["euu_lap"].notna()]
    reachable = chasers[chasers["pit_loss_s"].notna()]
    implied = chasers[
        chasers["theta_resolved"].astype(bool) & chasers["theta_ratio"].notna()
    ]

    out["DOneDecisions"] = str(len(d1))
    out["DOneNoRival"] = str(int((d1["role"] == "race leader").sum()))
    out["DOneChasers"] = str(len(chasers))
    out["DOnePredicted"] = str(len(predicted))
    out["DOneMedianGap"] = f"{chasers['gap_to_leader_s'].median():.1f}"
    out["DOneWithinPitLoss"] = str(int(reachable["within_pit_loss"].sum()))
    out["DOneReachable"] = str(len(reachable))
    out["DOneMedianError"] = f"{predicted['euu_error'].median():+.0f}"
    out["DOneBaselineError"] = f"{predicted['single_car_error'].median():+.0f}"
    out["DOneCloser"] = str(int(
        (predicted["euu_error"].abs() < predicted["single_car_error"].abs()).sum()
    ))
    out["DOneFurther"] = str(int(
        (predicted["euu_error"].abs() > predicted["single_car_error"].abs()).sum()
    ))
    out["DOneImpliedTheta"] = f"{implied['implied_theta'].median():.3f}"
    out["DOneMeasuredTheta"] = f"{implied['theta'].median():.3f}"
    out["DOneThetaRatio"] = f"{implied['theta_ratio'].median():.1f}"
    out["DOneThetaRatioIQR"] = (
        f"{implied['theta_ratio'].quantile(0.25):.1f} to "
        f"{implied['theta_ratio'].quantile(0.75):.1f}"
    )
    out["DOnePctThetaAbove"] = f"{100 * (implied['theta_ratio'] > 1).mean():.0f}"
    # Where the required rate sits among every slope the project fits, which is
    # what makes "the data almost never shows this" a measurement.
    all_slopes = coefs["deg_p1"].dropna()
    required = float(implied["implied_theta"].median())
    out["DOneThetaPercentile"] = f"{100 * (all_slopes < required).mean():.0f}"
    # The defects, each of which inflated the window.
    out["DOneMaxGap"] = f"{chasers['gap_to_leader_s'].max():.0f}"
    out["DOnePctAgeIsLap"] = (
        f"{100 * (chasers['tyre_age'] == chasers['real_pit_lap']).mean():.0f}"
    )
    history = pd.read_csv(F1_DERIVED_DIR / "history_pit_loss.csv")
    slug_delta = history.groupby("circuit")["pit_loss_median_s"].median()
    matched = int(chasers["circuit"].map(slug_delta).notna().sum())
    out["DOneStaleDropped"] = str(len(chasers) - matched)

    # --- which car the adversarial model should treat as the rival --------
    # Four selection rules on the same decisions. The two halves of the answer
    # are kept apart here because they point opposite ways: the rules disagree
    # about which car to model on most decisions, and none of them moves the
    # headline.
    rival = pd.read_csv(F1_DERIVED_DIR / "rival_selection.csv")
    scored = rival.dropna(subset=["adversarial_lap"])
    out["NRivalRules"] = str(scored["method"].nunique())
    for method, suffix in (("position", "Position"), ("thraves", "Thraves"),
                           ("pi_window", "PiWindow"), ("d1", "DOne")):
        part = scored[scored["method"] == method]
        out[f"Rival{suffix}Scored"] = str(len(part))
        out[f"Rival{suffix}Adv"] = f"{part['adversarial_error'].median():+.0f}"
        out[f"Rival{suffix}Closed"] = f"{part['closed'].median():+.0f}"
        out[f"Rival{suffix}MeanClosed"] = f"{part['closed'].mean():+.2f}"
        out[f"Rival{suffix}Better"] = str(int((part["closed"] > 0).sum()))
        out[f"Rival{suffix}Worse"] = str(int((part["closed"] < 0).sum()))

    wide = rival.pivot_table(
        index=["season", "circuit", "driver"], columns="method",
        values="rival", aggfunc="first",
    ).dropna()
    out["NRivalAllApply"] = str(len(wide))
    out["NRivalAllAgree"] = str(int((wide.nunique(axis=1) == 1).sum()))
    out["NRivalTwoCars"] = str(int((wide.nunique(axis=1) == 2).sum()))
    out["NRivalThreeCars"] = str(int((wide.nunique(axis=1) == 3).sum()))
    out["MaxRivalCars"] = str(int(wide.nunique(axis=1).max()))
    pairs = [100 * (wide[x] == wide[y]).mean()
             for i, x in enumerate(wide.columns) for y in wide.columns[i + 1:]]
    out["RivalPairMin"] = f"{min(pairs):.0f}"
    out["RivalPairMax"] = f"{max(pairs):.0f}"
    out["RivalPairMedian"] = f"{np.median(pairs):.0f}"
    out["PctRivalThravesAgrees"] = (
        f"{100 * (wide['thraves'] == wide['position']).mean():.0f}"
    )
    thraves_gap = scored[
        (scored["method"] == "thraves") & scored["standalone_delta_s"].notna()
    ]["standalone_delta_s"]
    out["RivalStandaloneGap"] = f"{thraves_gap.median():.1f}"

    # How many of the published replay's decisions had their rival chosen by
    # row order rather than by racing, which is the defect Thraves named.
    undercut = pd.read_csv(F1_DERIVED_DIR / "undercut_hypothesis.csv")
    out["NTiedDecisions"] = str(int((undercut["relation"] == "tie").sum()))

    # --- the literature catalogue, counted rather than remembered ----------
    # The framing claim is about how many papers were catalogued and how many
    # of them validate out of sample. Counting the table means the claim
    # cannot drift away from the catalogue it describes.
    catalogue = (REPORTS_DIR / "cross_series" / "related_work.md").read_text(
        encoding="utf-8"
    )
    entries = re.findall(r"^\| (\d+) \| \*\*", catalogue, re.M)
    out["NCatalogued"] = str(len(entries))
    if len(entries) != int(entries[-1]):
        raise ValueError(
            f"related_work.md has {len(entries)} rows numbered up to "
            f"{entries[-1]}; the numbering and the count disagree"
        )

    # --- what a fresh clone cannot rebuild ---------------------------------
    # Counted from the table in data/external/README.md, so the paper cannot
    # claim a smaller number than that file documents.
    external = (REPO_ROOT / "data" / "external" / "README.md").read_text(
        encoding="utf-8"
    )
    blocked = re.findall(r"^\| `scripts/(\w+\.py)` \|", external, re.M)
    out["NBlockedLayers"] = str(len(blocked))

    # --- the thinnest transfer score, the one a reviewer goes for first ----
    loro = pd.read_csv(ENDURANCE_DERIVED_DIR / "endurance_degradation_loro.csv")
    held = loro["held_out_season"].astype(str)
    folds = loro[held != "MEAN"].dropna(subset=["r2_within"])
    key = ["series", "event", "car_class"]
    spread = folds.groupby(key)["r2_within"].agg(["min", "max", "size"])
    published = (
        loro[held == "MEAN"].dropna(subset=["r2_within"])
        .nlargest(2, "r2_within")
    )
    # The runner-up, because the headline circuit-class is the stable one and
    # the one below it is the thin one. That contrast is the point.
    headline = published.iloc[0]
    best = spread.loc[(headline.series, headline.event, headline.car_class)]
    out["BestTransferFolds"] = str(int(best["size"]))
    out["BestTransferSpread"] = f"{best['max'] - best['min']:.3f}"

    runner_up = published.iloc[-1]
    thin = spread.loc[(runner_up.series, runner_up.event, runner_up.car_class)]
    out["ThinTransfer"] = f"{runner_up.r2_within:+.3f}"
    out["ThinTransferWhere"] = circuit_class_name(
        str(runner_up.event), str(runner_up.car_class)
    )
    out["ThinTransferFolds"] = str(int(thin["size"]))
    out["ThinTransferLow"] = f"{thin['min']:+.3f}"
    out["ThinTransferHigh"] = f"{thin['max']:+.3f}"
    out["ThinTransferSpread"] = f"{thin['max'] - thin['min']:.3f}"

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
    # Two medians, because they answer different questions and the paper uses
    # both: over every decision (comparable with the endurance rows below) and
    # over the late ones only (the size of the gap when there is one).
    out["FoneMedian"] = f"{f1_audit['delta_laps'].median():+.0f}"
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

    # The optimiser again, with each team's next stop held fixed
    # (run_committed_strategy*.py), so the table compares the rules against
    # the audit as corrected and not only as first run. Medians are over the
    # decisions that can be replayed, which in endurance are fewer.
    committed_abs: dict[tuple[str, str], float] = {}
    f1_rows = pd.read_csv(F1_DERIVED_DIR / "committed_strategy.csv")
    committed_abs[("f1", "")] = float(
        f1_rows["committed_delta_laps"].dropna().abs().median())
    end_rows = pd.read_csv(DERIVED_DIR / "endurance" / "committed_strategy.csv")
    for (series, car_class), group in end_rows.groupby(["series", "car_class"]):
        committed_abs[(series, car_class)] = float(
            group["committed_delta_laps"].dropna().abs().median())
    commit_beats = commit_ties = commit_loses = 0

    beaten = tied = held = by_b1 = 0
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
        fixed = committed_abs.get((series, str(car_class)))
        out[f"{name}CommitError"] = "--" if fixed is None else f"{fixed:.0f}"
        if fixed is not None:
            if fixed < best:
                commit_beats += 1
            elif fixed == best:
                commit_ties += 1
            else:
                commit_loses += 1
        if best < errors["Model"]:
            beaten += 1
            # Which rule wins matters: B1 uses no fitted quantity at all, so a
            # class it wins says something the others do not.
            if errors["Bone"] == best:
                by_b1 += 1
        elif best == errors["Model"]:
            tied += 1
        else:
            held += 1

    out["NClassesRuleWins"] = str(beaten)
    out["NClassesBoneWins"] = str(by_b1)
    out["NClassesRuleTies"] = str(tied)
    out["NClassesOptimiserWins"] = str(held)
    out["NClassesScored"] = str(beaten + tied + held)
    out["NClassesCommitBeatsRules"] = str(commit_beats)
    out["NClassesCommitTiesRules"] = str(commit_ties)
    out["NClassesCommitLosesRules"] = str(commit_loses)

    # --- Result 2: is the AUC gap a gap in measurement precision? -----------
    precision = pd.read_csv(DERIVED_DIR / "cross_series" / "regime_precision.csv")
    half = precision.iloc[(precision["kept_share"] - 0.5).abs().argmin()]
    third = precision.iloc[(precision["kept_share"] - 1 / 3).abs().argmin()]
    out["PrecisionHalfSlopeAuc"] = f"{half['auc_slope']:.3f}"
    out["PrecisionHalfPitAuc"] = f"{half['auc_pit_loss']:.3f}"
    out["NPrecisionHalf"] = str(int(half["n_race_seasons"]))
    out["PrecisionThirdSlopeAuc"] = f"{third['auc_slope']:.3f}"
    out["PrecisionThirdPitAuc"] = f"{third['auc_pit_loss']:.3f}"
    out["NPrecisionThird"] = str(int(third["n_race_seasons"]))
    out["NPrecisionThirdTyreLimited"] = str(int(third["n_tyre_limited"]))

    # Per-class median pit loss, quoted in the text to explain why the results
    # are grouped by class. Derived, because a guard caught them typed.
    for (series, car_class), group in plans.groupby(["series", "car_class"]):
        name = _tex_name(series) + _CLASS_TEX.get(str(car_class), "")
        out[f"{name}PitLoss"] = f"{group['pit_loss_s'].median():.0f}"

    # --- the track-position primitive the rejected explanation consumes ----
    # The range is quoted in the paper and it is one of the three claims
    # `thin_evidence.md` flags as thin, so the spread *within* a circuit is
    # generated alongside it. A range means nothing without it.
    swaps = pd.read_csv(F1_DERIVED_DIR / "overtaking_difficulty.csv")
    swaps = swaps.sort_values("adj_swap_rate")
    lowest, highest = swaps.iloc[0], swaps.iloc[-1]
    out["TrackPositionRange"] = f"{highest.adj_swap_rate / lowest.adj_swap_rate:.0f}"
    out["NCircuitsSwap"] = str(len(swaps))
    out["SwapLowestCircuit"] = circuit_name(str(lowest.circuit))
    out["SwapHighestCircuit"] = circuit_name(str(highest.circuit))
    out["SwapLowest"] = f"{lowest.adj_swap_rate:.4f}"
    out["SwapLowestSd"] = f"{lowest.sd_across_races:.4f}"
    out["SwapLowestRaces"] = str(int(lowest.n_races))
    out["SwapHighestRaces"] = str(int(highest.n_races))
    out["SwapRunnerUpRatio"] = (
        f"{swaps['adj_swap_rate'].iloc[1] / lowest.adj_swap_rate:.1f}"
    )
    out["SwapBetweenSd"] = f"{swaps['adj_swap_rate'].std():.4f}"
    out["SwapWithinSd"] = f"{swaps['sd_across_races'].median():.4f}"

    # --- what the cover-aware engine actually did, per circuit -------------
    # The paper says the mechanism moves the recommendation away from the real
    # stop. That is true of the calendar median, and it is not true everywhere,
    # so the exception is generated here rather than glossed over.
    undercut = pd.read_csv(F1_DERIVED_DIR / "undercut_hypothesis.csv")
    out["UndercutClosedMedian"] = f"{undercut['closed'].median():+.0f}"
    out["UndercutShareImproving"] = f"{100 * (undercut['closed'] > 0).mean():.0f}"
    out["UndercutSpearman"] = (
        f"{undercut['swap_rate'].corr(undercut['closed'], method='spearman'):+.2f}"
    )
    hardest = undercut[undercut["swap_rate"] == undercut["swap_rate"].min()]
    out["SwapLowestClosedMedian"] = f"{hardest['closed'].median():+.1f}"
    out["SwapLowestDecisions"] = str(len(hardest))

    # --- the cross-source check --------------------------------------------
    slope = pd.read_csv(F1_DERIVED_DIR / "slope_bias_check.csv")
    out["NIdentifiability"] = f"{slope['identifiability'].median():.3f}"

    # --- the audit median's race-clustered intervals ------------------------
    # These were computed and committed and then not published, while the
    # manuscript said an interval needed a clustering the audit table did not
    # carry. It carries it. Two of the seven classes turn out to contain zero,
    # which is the part that had to reach the paper.
    ci = pd.read_csv(DERIVED_DIR / "cross_series" / "audit_intervals.csv")
    ci = ci.set_index("scope")
    for scope, tex in (
        ("Formula 1", "Fone"), ("GTD", "ImsaGtd"), ("GTDPRO", "ImsaGtdpro"),
        ("GTP", "ImsaGtp"), ("HYPERCAR", "WecHypercar"), ("LMP2", "ElmsLmptwo"),
        ("LMP2 Pro/Am", "ElmsLmptwoProAm"), ("all endurance", "Endurance"),
    ):
        if scope not in ci.index:
            continue
        row = ci.loc[scope]
        out[f"AuditCi{tex}"] = f"[{row['ci_low']:+.1f}, {row['ci_high']:+.1f}]"
        # The bounds on their own as well, because prose outside the manuscript
        # quotes an interval as two numbers and the packet guard scans numbers,
        # not formatted intervals.
        out[f"AuditCiLow{tex}"] = f"{row['ci_low']:+.1f}"
        out[f"AuditCiHigh{tex}"] = f"{row['ci_high']:+.1f}"
        # The median from the same artifact as its interval, so a class median
        # and its interval cannot be quoted from two different scopes.
        out[f"AuditMed{tex}"] = f"{row['median_delta_laps']:+.0f}"
        out[f"AuditRaces{tex}"] = str(int(row["n_races"]))
    out["NAuditContainsZero"] = str(int(ci["contains_zero"].sum()))
    out["AuditZeroClasses"] = ", ".join(sorted(ci.index[ci["contains_zero"]]))
    out["NAuditScopes"] = str(int((ci.index != "all endurance").sum()))

    # --- what a stable slope could have scored ------------------------------
    # The null Result 1 needed: a low transfer score means either the slope
    # moved or there was never signal enough to recover it, and the published
    # number cannot tell those apart.
    ceil = pd.read_csv(F1_DERIVED_DIR / "transfer_ceiling.csv")
    sane = ceil[ceil["sane"]]
    out["NCeilingCircuits"] = str(len(sane))
    out["NCeilingBelowThreshold"] = str(int((sane["ceiling_mean"] < 0.2).sum()))
    counts = sane["verdict"].value_counts()
    out["NCeilingUnstable"] = str(int(counts.get("slope unstable", 0)))
    out["NCeilingStable"] = str(int(counts.get("slope stable", 0)))
    out["NCeilingNoSignal"] = str(int(counts.get("no signal to recover", 0)))
    out["NCeilingBorderline"] = str(int(counts.get("borderline", 0)))
    lo, hi = sane.loc[sane["ceiling_mean"].idxmin()], sane.loc[sane["ceiling_mean"].idxmax()]
    out["CeilingLowest"] = f"{lo['ceiling_mean']:+.3f}"
    out["CeilingLowestWhere"] = str(lo["circuit"]).replace("_", " ").title()
    out["CeilingHighest"] = f"{hi['ceiling_mean']:+.3f}"
    out["CeilingHighestWhere"] = str(hi["circuit"]).replace("_", " ").title()
    leak = (sane["published_r2"] - sane["noleak_r2"]).abs()
    out["LeakageMean"] = f"{leak.mean():.4f}"
    out["LeakageMax"] = f"{leak.max():.4f}"
    out["NCeilingExcluded"] = str(int((~ceil["sane"]).sum()))

    # --- the fourth candidate for Result 3, and its sign --------------------
    fresh = pd.read_csv(F1_DERIVED_DIR / "fresh_tyre.csv")
    profile = pd.read_csv(F1_DERIVED_DIR / "fresh_tyre_profile.csv").sort_values("tyre_age")
    youngest = profile.iloc[0]
    out["FreshAge"] = str(int(youngest["tyre_age"]))
    out["FreshResid"] = f"{youngest['mean_resid_s']:+.3f}"
    out["FreshResidNext"] = f"{profile.iloc[1]['mean_resid_s']:+.3f}"
    out["FreshAgeNext"] = str(int(profile.iloc[1]["tyre_age"]))
    out["NFreshCircuits"] = str(int(fresh["bonus_s"].notna().sum()))
    out["NFreshFaster"] = str(int((fresh["bonus_s"] > 0).sum()))
    out["FreshMedianBonus"] = f"{fresh['bonus_s'].median():+.3f}"

    # --- Result 3 with the team's own strategy held fixed --------------------
    def signed(x: float) -> str:
        if float(x) == 0:
            return "0"
        return f"{x:+.0f}" if float(x).is_integer() else f"{x:+.1f}"

    def interval(r: pd.Series, prefix: str = "") -> str:
        return f"[{r[prefix + 'ci_low']:+.1f}, {r[prefix + 'ci_high']:+.1f}]"

    commit = pd.read_csv(F1_DERIVED_DIR / "committed_strategy_summary.csv").set_index("group")
    commit_rows = pd.read_csv(F1_DERIVED_DIR / "committed_strategy.csv")
    for group, tex in (("all decisions", "All"), ("one stop", "One"),
                       ("two or more", "Multi"), ("three or more", "Three"),
                       ("two or more, second stop under green", "Green")):
        r = commit.loc[group]
        out[f"Commit{tex}Before"] = signed(r["median_delta"])
        out[f"Commit{tex}After"] = signed(r["committed_median_delta"])
        out[f"Commit{tex}Ci"] = interval(r, "committed_")
        # The bounds alone too: prose outside the manuscript quotes an interval
        # as two numbers, and the packet guard scans numbers.
        out[f"Commit{tex}CiLow"] = f"{r['committed_ci_low']:+.1f}"
        out[f"Commit{tex}CiHigh"] = f"{r['committed_ci_high']:+.1f}"
        out[f"Commit{tex}BeforeCi"] = interval(r)
        out[f"NCommit{tex}"] = str(int(r["n_decisions"]))
    multi = commit.loc["two or more"]
    out["CommitWindow"] = f"{multi['window_laps']:.0f}"
    out["CommitEngineMiss"] = f"{multi['committed_abs_miss']:.0f}"
    out["CommitUniformMiss"] = f"{multi['uniform_miss']:.1f}"
    out["CommitMidpointMiss"] = f"{multi['midpoint_miss']:.1f}"
    out["NCommitDropped"] = str(int(commit_rows["committed_delta_laps"].isna().sum()))
    both = []
    for _, race in commit_rows.groupby(["season", "circuit"]):
        one = race[race["n_stops"] == 1]["delta_laps"]
        more = race[race["n_stops"] >= 2]["delta_laps"]
        if len(one) and len(more):
            both.append(float(more.median() - one.median()))
    out["NCommitWithinRaces"] = str(len(both))
    out["CommitWithinGap"] = signed(float(np.median(both)))

    end_commit = pd.read_csv(DERIVED_DIR / "endurance" / "committed_strategy_summary.csv")
    end_labels = {("imsa", "GTD"): "ImsaGtd", ("imsa", "GTDPRO"): "ImsaGtdpro",
                  ("imsa", "GTP"): "ImsaGtp", ("wec", "HYPERCAR"): "WecHypercar",
                  ("elms", "LMP2"): "ElmsLmptwo", ("elms", "LMP2 Pro/Am"): "ElmsLmptwoProAm"}
    informative = 0
    for r in end_commit.itertuples():
        tex = end_labels[(r.series, r.car_class)]
        row = end_commit.loc[r.Index]
        out[f"EndCommit{tex}Before"] = signed(r.median_delta)
        out[f"EndCommit{tex}After"] = signed(r.committed_median_delta)
        out[f"EndCommit{tex}Ci"] = interval(row, "committed_")
        out[f"EndCommit{tex}Window"] = f"{r.window_laps:.0f}"
        out[f"EndCommit{tex}Miss"] = f"{r.committed_abs_miss:.0f}"
        out[f"EndCommit{tex}Uniform"] = f"{r.uniform_miss:.1f}"
        out[f"EndCommit{tex}Midpoint"] = f"{r.midpoint_miss:.1f}"
        informative += int(r.committed_abs_miss < min(r.uniform_miss, r.midpoint_miss))
    out["NEndCommit"] = str(int(end_commit["n_decisions"].sum()))
    # First stops replayed with the team's next stop held fixed, all series.
    out["NCommitTotal"] = f"{int(out['NCommitAll']) + int(out['NEndCommit']):,}"
    out["NEndCommitClasses"] = str(len(end_commit))
    out["NEndCommitContainsZero"] = str(int(end_commit["committed_contains_zero"].sum()))
    out["NEndCommitInformative"] = str(informative)

    # --- is Result 2's separation just a class label? -----------------------
    wc = pd.read_csv(DERIVED_DIR / "cross_series" / "regime_within_class.csv")
    flat = wc[wc["car_class"] == "all"].set_index("quantity")["auc"]
    out["RegimeAucStandardised"] = f"{flat['pit loss, standardised']:.3f}"
    out["RegimeAucClassLabel"] = f"{flat['class identity alone']:.3f}"
    out["RegimeWithinClassShare"] = f"{flat['within-class variance share of pit loss']:.0%}".replace("%", "")
    inside = wc[(wc["quantity"] == "pit loss, within class") & wc["auc"].notna()]
    out["NRegimeWithinClass"] = str(len(inside))
    out["NRegimeClassesOneRegime"] = str(
        int((wc[wc["quantity"] == "pit loss, within class"]["auc"].isna()).sum())
    )
    out["RegimeWithinClassMin"] = f"{inside['auc'].min():.3f}"
    out["RegimeWithinClassMax"] = f"{inside['auc'].max():.3f}"

    # --- three repairs a team could try for Result 1 and Result 3 ------------
    import json

    def load(name: str) -> dict:
        return json.loads((F1_DERIVED_DIR / f"{name}_summary.json").read_text(encoding="utf-8"))

    alloc = pd.read_csv(REPO_ROOT / "data" / "reference" / "pirelli_compounds.csv")
    out["NAllocationRaces"] = str(len(alloc))
    out["NAllocationPirelli"] = str(int(alloc["pirelli_press_url"].notna().sum()))
    ident = load("compound_identity")
    changed, linear = ident["changed"], ident["changed_linear"]
    out["NCompoundCircuits"] = str(ident["n_circuits"])
    out["NCompoundChanged"] = str(ident["n_changed"])
    out["CompoundRelative"] = f"{changed['median_relative']:.3f}"
    out["CompoundReal"] = f"{changed['median_real']:.3f}"
    out["CompoundDiff"] = f"{changed['median_difference']:+.3f}"
    out["CompoundDiffCi"] = f"[{changed['ci_low']:+.3f}, {changed['ci_high']:+.3f}]"
    out["NCompoundBetter"] = str(changed["n_better"])
    out["NCompoundWorse"] = str(changed["n_worse"])
    out["CompoundSignP"] = f"{changed['sign_p']:.2f}"
    out["CompoundMaxGain"] = f"{changed['max_difference']:+.3f}"
    out["CompoundLinearDiff"] = f"{linear['median_difference']:+.3f}"
    out["CompoundLinearDiffCi"] = f"[{linear['ci_low']:+.3f}, {linear['ci_high']:+.3f}]"
    out["NCompoundLinearBetter"] = str(linear["n_better"])
    out["NCompoundLinearWorse"] = str(linear["n_worse"])
    out["NCompoundMoved"] = str(ident["n_moved"])
    out["NCompoundDegenerate"] = str(ident["n_degenerate"])
    unstable = ident["unstable"]
    out["NCompoundUnstable"] = str(unstable["n"])
    out["NCompoundUnstableBetter"] = str(unstable["n_better"])
    out["NCompoundUnstableWorse"] = str(unstable["n_worse"])
    out["CompoundUnstableMin"] = f"{unstable['min_difference']:+.3f}"
    out["CompoundUnstableMax"] = f"{unstable['max_difference']:+.3f}"
    out["CompoundUnstableMedian"] = f"{unstable['median_difference']:+.3f}"
    out["CompoundUnseenPct"] = f"{100 * ident['unseen_share']:.1f}"
    out["CompoundUnseenMaxPct"] = f"{100 * ident['unseen_max']:.1f}"

    fri = load("practice_long_runs")
    out["NFridayRaces"] = str(fri["n_races"])
    out["NFridayCircuits"] = str(fri["n_circuits"])
    out["NFridaySprint"] = str(fri["n_fp1"])
    out["FridayOther"] = f"{fri['r2_other_seasons']:.3f}"
    out["FridayRaw"] = f"{fri['r2_friday']:.3f}"
    out["FridayCorrected"] = f"{fri['r2_friday_corrected']:.3f}"
    out["FridayBoth"] = f"{fri['r2_both']:.3f}"
    out["FridayOffset"] = f"{fri['offset']:+.3f}"
    for key, tex in (("friday_minus_other", "Raw"), ("corrected_minus_other", "Corrected"),
                     ("both_minus_other", "Both")):
        d = fri[key]
        out[f"Friday{tex}Diff"] = f"{d['median']:+.3f}"
        out[f"Friday{tex}DiffCi"] = f"[{d['ci_low']:+.3f}, {d['ci_high']:+.3f}]"
        out[f"NFriday{tex}Better"] = str(d["n_better"])
        out[f"NFriday{tex}Worse"] = str(d["n_worse"])
    out["NFridayOtherAbove"] = str(fri["n_other_above"])
    out["NFridayRawAbove"] = str(fri["n_friday_above"])
    out["NFridayBothAbove"] = str(fri["n_both_above"])

    retest = load("one_stop_retest")
    out["NRetest"] = str(retest["n_one_stop"])
    rules = retest["rules"]
    out["NRetestRules"] = str(len(rules))
    pub = rules["position"]
    out["RetestCloser"] = str(pub["better"])
    out["RetestFurther"] = str(pub["worse"])
    out["RetestCloserMax"] = str(max(r["better"] for r in rules.values()))
    out["RetestFurtherMin"] = str(min(r["worse"] for r in rules.values()))
    out["RetestSignPMax"] = f"{max(r['sign_p'] for r in rules.values()):.3f}"
    sal = retest["salminen"]
    out["NRetestLeaders"] = str(sal["leaders"])
    out["NRetestPredicted"] = str(sal["predicted"])
    out["RetestEuuError"] = signed(sal["euu_error"])
    out["RetestSingleError"] = signed(sal["single_error"])
    out["RetestEuuCloser"] = str(sal["closer"])
    out["RetestEuuFurther"] = str(sal["further"])
    ins = retest["salminen_inside"]
    out["NRetestEuuAfterFlag"] = str(ins["after_flag"])
    out["NRetestEuuInside"] = str(ins["n"])
    out["RetestEuuInsideAbsDiff"] = signed(ins["abs_diff"])
    out["RetestEuuInsideAbsDiffCi"] = (
        f"[{ins['abs_diff_ci'][0]:+.0f}, {ins['abs_diff_ci'][1]:+.0f}]"
    )
    out["RetestEuuInsideCloser"] = str(ins["closer"])
    out["RetestEuuInsideFurther"] = str(ins["further"])

    design = load("audit_design_checks")
    names = {"top": "Top", "all": "All"}
    words = {5: "Five", 10: "Ten", 15: "Fifteen"}
    for key, g in design["grid"].items():
        field, lb = key.split("_")
        tag = names[field] + words[int(lb)]
        out[f"Design{tag}N"] = f"{g['n']:,}"
        out[f"Design{tag}Median"] = signed(g["median"])
        out[f"Design{tag}Ci"] = f"[{g['ci_low']:+.1f}, {g['ci_high']:+.1f}]"
        out[f"Design{tag}Hl"] = signed(g["hl"])
        out[f"Design{tag}OneMedian"] = signed(g["one_median"])
        out[f"Design{tag}OneCi"] = f"[{g['one_ci_low']:+.1f}, {g['one_ci_high']:+.1f}]"
        out[f"Design{tag}OneHl"] = signed(g["one_hl"])
        out[f"Design{tag}Bound"] = f"{100 * g['at_bound']:.0f}"
    medians = [g["median"] for g in design["grid"].values()]
    out["DesignMinMedian"] = signed(min(medians))
    out["DesignMaxMedian"] = signed(max(medians))
    ratio = design["ratio"]
    out["RatioResolvedN"] = str(ratio["resolved"]["n"])
    out["RatioResolvedMedian"] = signed(ratio["resolved"]["median"])
    out["RatioResolvedOneMedian"] = signed(ratio["resolved"]["one_median"])
    out["RatioUnresolvedN"] = str(ratio["unresolved"]["n"])
    out["RatioUnresolvedMedian"] = signed(ratio["unresolved"]["median"])
    out["RatioUnresolvedOneMedian"] = signed(ratio["unresolved"]["one_median"])
    out["RatioQuadraticN"] = str(ratio["quadratic circuit"]["n"])
    imp = design["implied"]
    out["ImpliedN"] = str(imp["n"])
    out["ImpliedFitted"] = f"{imp['median_fitted']:.2f}"
    out["ImpliedRatio"] = f"{imp['median_implied']:.2f}"
    out["ImpliedShareBelow"] = f"{100 * imp['share_below']:.0f}"
    out["ImpliedShareBelowCi"] = (
        f"[{100 * imp['share_below_ci'][0]:.0f}\\%, {100 * imp['share_below_ci'][1]:.0f}\\%]"
    )
    out["ImpliedRatioCi"] = (
        f"[{imp['median_implied_ci'][0]:.2f}, {imp['median_implied_ci'][1]:.2f}]"
    )
    out["ClosedFormN"] = str(design["closed_form"]["n"])
    out["ClosedFormGap"] = f"{design['closed_form']['median_abs_vs_engine']:.1f}"

    base = load("transfer_baselines")
    out["BaseCircuits"] = str(base["n_circuits"])
    for key, tag in (("past", "Past"), ("category", "Category")):
        b = base[key]
        out[f"Base{tag}Median"] = f"{b['median']:.3f}"
        out[f"Base{tag}Loro"] = f"{b['median_loro']:.3f}"
        out[f"Base{tag}Diff"] = f"{b['median_diff']:+.3f}"
        out[f"Base{tag}DiffCi"] = f"[{b['ci_low']:+.3f}, {b['ci_high']:+.3f}]"
        out[f"NBase{tag}Better"] = str(b["n_better"])
        out[f"NBase{tag}Worse"] = str(b["n_worse"])
    out["CeilingShareN"] = str(base["ceiling"]["n"])
    out["CeilingShareMedian"] = f"{base['ceiling']['median_share']:.2f}"
    out["NCeilingShareHalf"] = str(base["ceiling"]["n_above_half"])
    k = base["ceiling"]
    out["CeilingShareCategory"] = f"{k['median_share_category']:.2f}"
    out["NCeilingShareHalfCategory"] = str(k["n_above_half_category"])
    out["CeilingCategoryDiff"] = f"{k['category_minus_own']:+.3f}"
    out["CeilingCategoryDiffCi"] = (
        f"[{k['category_minus_own_ci'][0]:+.3f}, {k['category_minus_own_ci'][1]:+.3f}]"
    )
    out["NCeilingCategoryBetter"] = str(k["n_category_better"])
    out["NCeilingCategoryWorse"] = str(k["n_category_worse"])
    trims = base["trim"]
    levels = sorted(trims)
    out["TrimLow"], out["TrimPublished"], out["TrimHigh"] = levels[0], levels[1], levels[2]
    out["CeilingMeasurable"] = str(base["ceiling"]["threshold"])
    out["TrimShareMoved"] = f"{100 * max(v['share_moved_10pct'] for v in trims.values()):.0f}"
    out["TrimLoroLow"] = f"{min(v['median_loro'] for v in trims.values()):.3f}"
    out["TrimLoroHigh"] = f"{max(v['median_loro'] for v in trims.values()):.3f}"

    index = json.loads((DERIVED_DIR / "cross_series" / "regime_index_summary.json").read_text(encoding="utf-8"))
    out["IndexN"] = str(index["n_positive"])
    out["IndexAuc"] = f"{index['index_auc']:.3f}"
    out["IndexShareSlope"] = f"{100 * index['shares']['slope']:.0f}"
    out["IndexSharePit"] = f"{100 * index['shares']['pit loss']:.0f}"
    out["IndexShareStint"] = f"{100 * index['shares']['stint']:.0f}"
    out["IndexWithoutPit"] = f"{index['auc_without']['pit loss']:.3f}"
    out["IndexWithoutSlope"] = f"{index['auc_without']['slope']:.3f}"
    d = index["differences"]
    out["IndexDropDiff"] = f"{d['without_slope_minus_without_pit']:+.3f}"
    out["IndexDropDiffCi"] = f"[{d['without_ci'][0]:+.3f}, {d['without_ci'][1]:+.3f}]"
    out["IndexAloneDiff"] = f"{d['pit_minus_slope_alone']:+.3f}"
    out["IndexAloneDiffCi"] = f"[{d['alone_ci'][0]:+.3f}, {d['alone_ci'][1]:+.3f}]"

    # The prospective test's prediction intervals, by the procedure fixed in
    # paper/prospective_protocol.md: resample whole races of the committed
    # replay and take the median of each resampled set.
    committed = pd.read_csv(F1_DERIVED_DIR / "committed_strategy.csv").dropna(
        subset=["committed_delta_laps"])
    committed["race"] = committed["season"].astype(str) + "_" + committed["circuit"]
    groups = [g["committed_delta_laps"].to_numpy() for _, g in committed.groupby("race")]
    rng_pi = np.random.default_rng(20261108)
    for n_races, tag in ((4, "Four"), (24, "Season")):
        meds = [np.median(np.concatenate([groups[j] for j in rng_pi.integers(0, len(groups), n_races)]))
                for _ in range(20_000)]
        lo, hi = np.percentile(meds, [2.5, 97.5])
        out[f"ProspectivePi{tag}"] = f"[{signed(lo)}, {signed(hi)}]"

    ceil_tab = pd.read_csv(F1_DERIVED_DIR / "transfer_ceiling.csv")
    ceil_tab = ceil_tab[ceil_tab["sane"].astype(bool)]
    out["CeilingResidGapMax"] = f"{(ceil_tab['ceiling_mean'] - ceil_tab['ceiling_pooled_resid']).max():.3f}"
    endc = json.loads((ENDURANCE_DERIVED_DIR / "endurance_ceiling_summary.json").read_text(encoding="utf-8"))
    out["EndCeilN"] = str(endc["n"])
    out["EndCeilBelow"] = str(endc["n_ceiling_below_threshold"])
    v = endc["verdicts"]
    out["EndCeilNoSignal"] = str(v.get("no signal to recover", 0))
    out["EndCeilStable"] = str(v.get("slope stable", 0))
    out["EndCeilUnstable"] = str(v.get("slope unstable", 0))
    out["EndCeilBorderline"] = str(v.get("borderline", 0))
    out["EndCeilGtThree"] = f"{endc['gt3']['mean_ceiling']:+.3f}"
    out["EndCeilProto"] = f"{endc['proto']['mean_ceiling']:+.3f}"
    out["EndCeilDiff"] = f"{endc['ceiling_diff']['diff']:+.3f}"
    out["EndCeilDiffCi"] = f"[{endc['ceiling_diff']['ci'][0]:+.3f}, {endc['ceiling_diff']['ci'][1]:+.3f}]"
    sh = endc["share"]
    out["EndShareGtThree"] = f"{sh['gt3_mean']:.2f}"
    out["EndShareProto"] = f"{sh['proto_mean']:.2f}"
    out["NEndShareGtThree"] = str(sh["n_gt3"])
    out["NEndShareProto"] = str(sh["n_proto"])
    out["EndShareDiff"] = f"{sh['diff']:+.2f}"
    out["EndShareDiffCi"] = f"[{sh['ci'][0]:+.2f}, {sh['ci'][1]:+.2f}]"
    lm = endc["elms_lmp2"]
    out["NLmptwoNoSignal"] = str(lm.get("no signal to recover", 0))
    out["NLmptwoTotal"] = str(sum(lm.values()))
    out["NLmptwoUnstable"] = str(lm.get("slope unstable", 0))

    chk = load("estimation_checks")
    rc, it, rf = chk["race_clustering"], chk["interaction"], chk["refuelling"]
    out["RaceClusterN"] = str(rc["n_slopes"])
    out["RaceClusterZeroDr"] = str(rc["zero_driver_race"])
    out["RaceClusterZero"] = str(rc["zero_race"])
    out["InterN"] = str(it["n_circuits"])
    out["InterPositive"] = str(it["n_gamma_positive"])
    out["InterSignificant"] = str(it["n_gamma_significant"])
    out["InterDecisions"] = str(it["n_decisions"])
    out["InterGapWithout"] = signed(it["gap_without"])
    out["InterGapWith"] = signed(it["gap_with"])
    out["InterOneN"] = str(it["one_n"])
    out["InterOneWithout"] = signed(it["one_gap_without"])
    out["InterOneWith"] = signed(it["one_gap_with"])
    out["RefuelShare"] = f"{100 * rf['median_fuel_share']:.0f}"
    out["RefuelShareMax"] = f"{100 * rf['max_fuel_share']:.0f}"
    out["RefuelTyreLimited"] = str(rf["tyre_limited_marginal"])
    out["RefuelChanged"] = str(rf["n_changed"])

    # --- identification checks (run_identification_checks.py) ---------------
    idc = load("identification_checks")
    ca, va, en = idc["cancellation"], idc["variance"], idc["endurance"]
    out["CancelN"] = str(ca["n"])
    out["CancelFuel"] = f"{ca['fuel_median']:+.3f}"
    out["CancelWear"] = f"{ca['wear_median']:+.3f}"
    out["CancelNet"] = f"{ca['net_abs_median']:.3f}"
    out["CancelRho"] = f"{ca['rho']:.2f}"
    out["CancelLowest"] = str(ca["lowest"]).replace("_", " ").title()
    out["CancelLowestFuel"] = f"{ca['lowest_fuel']:+.3f}"
    out["CancelLowestWear"] = f"{ca['lowest_wear']:+.3f}"
    out["VarN"] = str(va["n"])
    out["VarCircuits"] = str(va["n_circuits"])
    out["VarHet"] = str(va["n_heterogeneous"])
    out["VarIsq"] = f"{va['i2_median']:.2f}"
    out["VarIsqCi"] = f"[{va['i2_median_ci'][0]:.2f}, {va['i2_median_ci'][1]:.2f}]"
    out["VarIsqHalf"] = str(va["n_i2_above_half"])
    out["VarTauShare"] = f"{100 * va['tau_over_mu_median']:.0f}"
    out["VarTauShareCi"] = (
        f"[{100 * va['tau_over_mu_ci'][0]:.0f}, {100 * va['tau_over_mu_ci'][1]:.0f}]"
    )
    out["VarTauExcl"] = str(va["n_tau_ci_excludes_zero"])
    out["VarSeInflation"] = f"{va['se_inflation_median']:.1f}"
    out["VarSeInflationMax"] = f"{va['se_inflation_max']:.1f}"
    iv = va["i2_by_verdict"]
    out["VarIsqStable"] = f"{iv.get('slope stable', float('nan')):.2f}"
    out["VarIsqUnstable"] = f"{iv.get('slope unstable', float('nan')):.2f}"
    out["VarIsqNoSignal"] = f"{iv.get('no signal to recover', float('nan')):.2f}"
    out["EndVarN"] = str(en["n"])
    out["EndVarHet"] = str(en["n_heterogeneous"])
    out["EndVarIsq"] = f"{en['i2_median']:.2f}"
    out["EndVarIsqStable"] = f"{en['i2_by_verdict'].get('slope stable', float('nan')):.2f}"
    t, tr = idc["temperature"], idc["temperature_repair"]
    out["TempTheta"] = f"{t['theta_per_10c']:+.3f}"
    out["TempThetaSe"] = f"{t['theta_per_10c_se']:.3f}"
    out["TempShare"] = f"{100 * t['share_removed']:.0f}"
    out["TempRange"] = f"{t['temp_range_median_c']:.0f}"
    out["TempOwnDiff"] = f"{tr['median_difference']:+.3f}"
    out["TempOwnDiffCi"] = f"[{tr['ci'][0]:+.3f}, {tr['ci'][1]:+.3f}]"
    out["TempOwnBetter"] = str(tr["n_better"])
    out["TempCatDiff"] = f"{tr['category']['median_difference']:+.3f}"
    out["TempCatDiffCi"] = f"[{tr['category']['ci'][0]:+.3f}, {tr['category']['ci'][1]:+.3f}]"
    out["TempCatBetter"] = str(tr["category"]["n_better"])
    out["TempN"] = str(tr["n"])
    fs = idc["first_stint"]
    out["FirstPairs"] = str(fs["n_pairs"])
    out["FirstSteeper"] = str(fs["n_first_steeper"])
    out["FirstSig"] = str(fs["n_significant"])
    out["FirstSigSteeper"] = str(fs["n_significant_steeper"])
    out["FirstN"] = str(fs["n_decisions"])
    out["FirstGapPooled"] = signed(fs["gap_pooled"])
    out["FirstGapSplit"] = signed(fs["gap_split"])
    out["FirstOneN"] = str(fs["one_n"])
    out["FirstOneGapPooled"] = signed(fs["one_gap_pooled"])
    out["FirstOneGapSplit"] = signed(fs["one_gap_split"])
    ex = idc["extrapolation"]
    out["ExtrapN"] = str(ex["n"])
    out["ExtrapMax"] = f"{ex['pct_beyond_max']:.0f}"
    out["ExtrapPninetyfive"] = f"{ex['pct_beyond_p95']:.0f}"
    out["ExtrapReal"] = f"{ex['pct_real_beyond_p95']:.0f}"
    out["ExtrapOne"] = f"{ex['one_pct_beyond_p95']:.0f}"
    out["ExtrapInsideGap"] = signed(ex["gap_inside_p95"])
    out["ExtrapOneInsideGap"] = signed(ex["one_gap_inside_p95"])
    gp = idc["gt3_paired"]["measured"]
    out["GtPairEvents"] = str(gp["n_events"])
    out["GtPairDiff"] = f"{gp['mean_difference']:+.3f}"
    out["GtPairDiffCi"] = f"[{gp['ci'][0]:+.3f}, {gp['ci'][1]:+.3f}]"
    out["GtPairP"] = f"{gp['p_sign_flip']:.2f}"
    out["GtPairHigher"] = str(gp["n_gt3_higher"])

    # --- the committed audit out of sample (run_audit_out_of_sample.py) -----
    aos = load("audit_out_of_sample")
    for tag, key in (("Oos", "out_of_sample"), ("Wide", "widened")):
        g = aos[key]
        out[f"{tag}N"] = str(g["n"])
        out[f"{tag}Median"] = signed(g["median"])
        out[f"{tag}Ci"] = f"[{signed(g['ci'][0])}, {signed(g['ci'][1])}]"
        out[f"{tag}Published"] = signed(g["published_median"])
        out[f"{tag}OneN"] = str(g["n_one"])
        out[f"{tag}OneMedian"] = signed(g["one_median"])
        out[f"{tag}OneCi"] = f"[{signed(g['one_ci'][0])}, {signed(g['one_ci'][1])}]"
        out[f"{tag}OnePublished"] = signed(g["one_published_median"])
        out[f"{tag}Moved"] = f"{g['pct_moved']:.0f}"

    # The verdict rule of the noise ceiling, read from the script that applies it.
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "run_transfer_ceiling", REPO_ROOT / "scripts" / "run_transfer_ceiling.py")
    ceiling_mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    spec.loader.exec_module(ceiling_mod)
    out["StableGap"] = f"{ceiling_mod.STABLE_GAP:.2f}"
    out["UnstableGap"] = f"{ceiling_mod.UNSTABLE_GAP:.2f}"

    coefs_tab = pd.read_csv(F1_DERIVED_DIR / "degradation_coefficients.csv")
    noise = coefs_tab.groupby("circuit")["cv_rmse_s"].first()
    sane_ceiling = ceil_tab.set_index("circuit")
    out["CancelNoise"] = f"{noise.reindex(sane_ceiling.index).median():.2f}"
    out["NFoneAboveTwo"] = str(int((sane_ceiling["noleak_r2"] > 0.2).sum()))
    out["OosShift"] = f"{aos['out_of_sample']['median_abs_shift']:.0f}"
    # The cross-source slope check: core FastF1 slopes beside the independent
    # Ergast-schema history, paired by circuit, as tests/test_paper_claims.py
    # recomputes it for the README.
    from src.ingestion.config import breadth_key
    history = pd.read_csv(F1_DERIVED_DIR / "history_degradation.csv")
    core_slope = coefs_tab.groupby("circuit")["deg_p1"].median()
    hist_slope = (history[history["era"] == "ground-effect"]
                  .groupby("circuit")["tyre_slope_s"].median())
    pairs = [(float(v), float(hist_slope[breadth_key(c)])) for c, v in core_slope.items()
             if breadth_key(c) in hist_slope.index]
    pairs = [(a, b) for a, b in pairs if np.isfinite(a) and np.isfinite(b)]
    diffs = np.array([b - a for a, b in pairs])
    out["CrossSourceN"] = str(len(pairs))
    out["CrossSourceDiff"] = f"{np.median(diffs):+.4f}"
    out["CrossSourceWear"] = f"{np.median([a for a, _ in pairs]):.3f}"

    hz = load("stop_hazard")
    out["HazardStints"] = str(hz["n_stints"])
    out["HazardLaps"] = f"{hz['n_laps']:,}"
    out["HazardRaces"] = str(hz["n_races"])
    out["HazardRatio"] = f"{hz['ratio']:.2f}"
    out["HazardRatioCi"] = f"[{hz['ratio_ci'][0]:.2f}, {hz['ratio_ci'][1]:.2f}]"
    out["HazardRatioCiFixed"] = (
        f"[{hz['ratio_ci_fixed_slopes'][0]:.2f}, {hz['ratio_ci_fixed_slopes'][1]:.2f}]"
    )
    for key, name in (("to harder", "Harder"), ("to softer", "Softer")):
        d = hz["directions"][key]
        out[f"Hazard{name}"] = f"{d['ratio']:.2f}"
        out[f"Hazard{name}Ci"] = f"[{d['ratio_ci'][0]:.2f}, {d['ratio_ci'][1]:.2f}]"

    # --- implied ratio by direction (run_implied_direction.py) ---------------
    idr = load("implied_direction")
    for key, name in (("to harder", "Harder"), ("to softer", "Softer")):
        d = idr["directions"][key]
        out[f"Implied{name}N"] = str(d["n"])
        out[f"Implied{name}Races"] = str(d["races"])
        out[f"Implied{name}"] = f"{d['implied']:.2f}"
        out[f"Implied{name}Ci"] = f"[{d['implied_ci'][0]:.2f}, {d['implied_ci'][1]:.2f}]"
        out[f"ImpliedFitted{name}"] = f"{d['fitted']:.2f}"
        out[f"ImpliedFitted{name}Ci"] = f"[{d['fitted_ci'][0]:.2f}, {d['fitted_ci'][1]:.2f}]"
    out["ImpliedExpectedSide"] = f"{100 * idr['implied_on_expected_side']:.0f}"
    out["ImpliedFittedExpectedSide"] = f"{100 * idr['fitted_on_expected_side']:.0f}"

    # --- compound baseline offsets (run_compound_offsets.py) ---------------
    co = load("compound_offsets")
    out["OffsetsN"] = str(co["n"])
    out["OffsetsFittedSide"] = f"{100 * co['fitted_offsets_expected_side']:.0f}"
    h = co["directions"]["to harder"]
    out["OffsetHarder"] = f"{h['offset_gap']:+.3f}"
    out["OffsetHarderCi"] = f"[{h['offset_gap_ci'][0]:+.3f}, {h['offset_gap_ci'][1]:+.3f}]"
    out["OffsetsGapPlain"] = signed(co["gap_plain"])
    out["OffsetsGap"] = signed(co["gap_offsets"])
    out["OffsetsGapCi"] = f"[{signed(co['gap_offsets_ci'][0])}, {signed(co['gap_offsets_ci'][1])}]"

    # --- 2026 races already ingested (run_heldout_2026.py) -----------------
    h26 = load("heldout_2026")
    out["HeldRaces"] = str(h26["n_races"])
    out["HeldIngested"] = str(h26["n_ingested"])
    out["HeldN"] = str(h26["top5_five"]["n"])
    out["HeldMedian"] = signed(h26["top5_five"]["median"])
    out["HeldCi"] = f"[{signed(h26['top5_five']['ci'][0])}, {signed(h26['top5_five']['ci'][1])}]"
    out["HeldOneMedian"] = signed(h26["top5_five"]["one_median"])
    out["HeldOneN"] = str(h26["top5_five"]["one_n"])
    out["HeldWideN"] = str(h26["all_fifteen"]["n"])
    out["HeldWideMedian"] = signed(h26["all_fifteen"]["median"])
    out["HeldWideCi"] = (
        f"[{signed(h26['all_fifteen']['ci'][0])}, {signed(h26['all_fifteen']['ci'][1])}]"
    )
    out["HeldImpliedN"] = str(h26["implied"]["n"])
    out["HeldImplied"] = f"{h26['implied']['median']:.2f}"
    out["HeldImpliedCi"] = f"[{h26['implied']['ci'][0]:.2f}, {h26['implied']['ci'][1]:.2f}]"

    # --- between-race variance, three objections (run_tau_robustness.py) ----
    tr = load("tau_robustness")
    for key, name in (("published", "Pub"), ("real_compound", "Real"),
                      ("unchanged_allocation", "Unchanged"), ("net_slope", "Net")):
        t = tr[key]
        out[f"Tau{name}N"] = str(t["n"])
        out[f"Tau{name}Circuits"] = str(t["n_circuits"])
        out[f"Tau{name}Het"] = str(t["n_heterogeneous"])
        out[f"Tau{name}Isq"] = f"{t['i2_median']:.2f}"
        out[f"Tau{name}ShareDl"] = f"{100 * t['share_dl_median']:.0f}"
        out[f"Tau{name}ShareReml"] = f"{100 * t['share_reml_median']:.0f}"
        out[f"Tau{name}ShareRemlCi"] = (
            f"[{100 * t['share_reml_ci'][0]:.0f}, {100 * t['share_reml_ci'][1]:.0f}]"
        )
        out[f"Tau{name}Common"] = f"{100 * t['common_tau_share']:.0f}"
        out[f"Tau{name}CommonCi"] = (
            f"[{100 * t['common_tau_share_ci'][0]:.0f}, {100 * t['common_tau_share_ci'][1]:.0f}]"
        )
        out[f"Tau{name}CommonN"] = str(t["n_resolved_means"])

    # --- reference rules (run_reference_rules.py) ---------------------------
    ref = json.loads((DERIVED_DIR / "cross_series" / "reference_rules_summary.json").read_text(encoding="utf-8"))
    ties = sum(1 for g in ref.values() if round(g["ratio_one_abs"]) == round(g["committed_abs"]))
    out["RatioOneTies"] = str(ties)
    out["RatioOneClasses"] = str(len(ref))
    for key, g in ref.items():
        series, car_class = key.split("|")
        name = (_tex_name(series) if series == "f1"
                else _tex_name(series) + _CLASS_TEX.get(car_class, ""))
        out[f"{name}RatioOneError"] = f"{g['ratio_one_abs']:.0f}"
        out[f"{name}Caution"] = f"{g['pct_neutralised']:.0f}"
        out[f"{name}GreenN"] = str(g["green_n"])
        out[f"{name}GreenMedian"] = signed(g["green_committed_median"])
        out[f"{name}GreenCi"] = (
            f"[{signed(g['green_committed_ci'][0])}, {signed(g['green_committed_ci'][1])}]")
    out["FoneRatioOneSigned"] = signed(ref["f1|"]["ratio_one_median"])
    imsa = [g for k, g in ref.items() if k.startswith("imsa")]
    out["ImsaCautionMin"] = f"{min(g['pct_neutralised'] for g in imsa):.0f}"
    out["ImsaCautionMax"] = f"{max(g['pct_neutralised'] for g in imsa):.0f}"

    est = load("estimability")
    out["EstChecked"] = str(est["f1_coefficients_checked"])
    out["EstFailed"] = str(est["f1_non_estimable"])

    dev = load("deviation_cost")
    out["NDeviationCars"] = str(dev["n_cars"])
    out["NDeviationRaces"] = str(dev["n_races"])
    out["DeviationMedianLaps"] = f"{dev['median_abs_deviation']:.0f}"
    out["DeviationPredicted"] = f"{dev['median_predicted_s']:.2f}"
    out["DeviationPlannerPerLap"] = f"{dev['planner_per_lap_s']:.2f}"
    out["DeviationPerLap"] = f"{dev['abs_deviation']['slope']:.2f}"
    out["DeviationPerLapCi"] = (
        f"[{dev['abs_deviation']['ci_low']:+.2f}, {dev['abs_deviation']['ci_high']:+.2f}]"
    )
    out["DeviationSlope"] = f"{dev['predicted_cost_s']['slope']:.2f}"
    out["DeviationSlopeCi"] = (
        f"[{dev['predicted_cost_s']['ci_low']:+.2f}, {dev['predicted_cost_s']['ci_high']:+.2f}]"
    )
    out["DeviationSpread"] = f"{dev['within_race_sd_s']:.1f}"
    # Power: the standard error implied by the interval, the smallest per-lap
    # effect detectable at 5% with 80% power (2.8 standard errors), and the
    # decisions that would detect the planner's own price.
    se = (dev["abs_deviation"]["ci_high"] - dev["abs_deviation"]["ci_low"]) / 3.92
    out["DeviationMde"] = f"{2.8 * se:.2f}"
    needed = dev["n_cars"] * (2.8 * se / dev["planner_per_lap_s"]) ** 2
    out["DeviationNeeded"] = f"{int(round(needed, -2)):,}"

    return out



_ONE_DECIMAL_INTERVAL = re.compile(r"^\[([-+]?\d+\.\d), ([-+]?\d+\.\d)\]$")


def _lap_interval(value: str) -> str:
    """Write a lap interval the way its median is written: [+1, +4], not [+1.0, +4.0].

    Medians of whole laps are whole or half laps, so a one-decimal interval whose
    bounds are both multiples of a half is a lap interval; every other value is
    returned unchanged.
    """
    m = _ONE_DECIMAL_INTERVAL.match(str(value))
    if not m:
        return value
    bounds = [float(m.group(1)), float(m.group(2))]
    if any((2 * b) % 1 for b in bounds):
        return value

    def one(b: float) -> str:
        if b == 0:
            return "0"
        return f"{b:+.0f}" if b.is_integer() else f"{b:+.1f}"

    return f"[{one(bounds[0])}, {one(bounds[1])}]"

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
        lines.append(f"\\newcommand{{\\{name}}}{{{_lap_interval(value)}}}")
    lines.append("")

    (PAPER / "numbers.tex").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {PAPER / 'numbers.tex'} ({len(macros)} macros)")
    for name, value in list(macros.items())[:12]:
        print(f"  \\{name:24s} {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
