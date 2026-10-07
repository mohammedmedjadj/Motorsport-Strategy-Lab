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

    f1_files = sorted(glob.glob(str(F1_DERIVED_DIR / "laps_*.csv")))
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
