"""Put an interval on each headline result, and a test where a test applies.

The three findings are currently described, not tested. This is the gap a
reviewer reaches first, and closing it is what separates a project report from
a paper:

1. **"GT3 transfers, prototypes do not."** A comparison of two numbers with
   nothing said about how far either could move. Now a difference in mean
   leave-one-race-out R² between the two groups, with a cluster bootstrap
   interval and a permutation p-value.
2. **"r = -0.982."** Six points and no interval. Bootstrapped over the 205
   *races*, recomputing each class summary inside every replicate, because a
   bootstrap over six points is decoration.
3. **"no race above 22.5 s is tyre-limited."** A maximum, quoted as if it were
   a calibrated constant. Bootstrapping a maximum is the wrong instrument and
   the report says so; what is reported instead is how far the edge moves when
   the single race defining it is removed.

Writes ``data/derived/cross_series/formal_tests.csv`` and
``reports/cross_series/formal_tests.md``.

Usage (offline, from the repo root)::

    python scripts/run_formal_tests.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.ingestion.config import DERIVED_DIR, ENDURANCE_DERIVED_DIR, REPORTS_DIR  # noqa: E402
from src.stats.inference import (  # noqa: E402
    boundary_sensitivity,
    cluster_bootstrap,
    compare_groups,
    correlation_over_units,
)

CROSS_SERIES = REPORTS_DIR / "cross_series"
CROSS_DERIVED = DERIVED_DIR / "cross_series"

#: The split under test. GT3 classes against everything with a prototype
#: underneath it — the grouping the transfer claim is actually about.
GT3_CLASSES = frozenset({"GTD", "GTDPRO"})


def transfer_groups() -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """Mean LORO R² per circuit-class, split GT3 against prototype.

    One value per circuit-class, never per fold: the folds inside a
    circuit-class share a pooled fitted slope, so treating them as independent
    would inflate the sample four-fold and narrow every interval below.
    """
    loro = pd.read_csv(ENDURANCE_DERIVED_DIR / "endurance_degradation_loro.csv")
    mean = loro[loro["held_out_season"].astype(str) == "MEAN"].dropna(
        subset=["r2_within"]
    )
    gt3 = mean[mean["car_class"].isin(GT3_CLASSES)]["r2_within"].to_numpy(float)
    proto = mean[~mean["car_class"].isin(GT3_CLASSES)]["r2_within"].to_numpy(float)
    return gt3, proto, mean


def pit_loss_groups() -> list[np.ndarray]:
    """Each class's races as (pit loss, tyre-limited) pairs."""
    plans = pd.read_csv(ENDURANCE_DERIVED_DIR / "multistop_plans.csv")
    plans["tyre_limited"] = plans["optimal_stops"] != plans["min_stops"]
    return [
        group[["pit_loss_s", "tyre_limited"]].to_numpy(float)
        for _, group in plans.groupby(["series", "car_class"])
    ]


def _class_summary(races: np.ndarray) -> tuple[float, float]:
    """A class's median pit loss and its tyre-limited share."""
    return float(np.median(races[:, 0])), float(np.mean(races[:, 1]) * 100.0)


def main() -> int:
    rows: list[dict] = []

    # --- 1. Does GT3 transfer better than prototypes? -----------------------
    gt3, proto, mean_table = transfer_groups()
    comparison = compare_groups(gt3, proto)
    gt3_mean = cluster_bootstrap(gt3, np.mean, unit="circuit-class")
    proto_mean = cluster_bootstrap(proto, np.mean, unit="circuit-class")

    rows += [
        {"result": "GT3 mean LORO R2", "estimate": gt3_mean.estimate,
         "ci_low": gt3_mean.low, "ci_high": gt3_mean.high,
         "unit": gt3_mean.unit, "n": len(gt3), "p_value": ""},
        {"result": "prototype mean LORO R2", "estimate": proto_mean.estimate,
         "ci_low": proto_mean.low, "ci_high": proto_mean.high,
         "unit": proto_mean.unit, "n": len(proto), "p_value": ""},
        {"result": "GT3 minus prototype", "estimate": comparison.difference.estimate,
         "ci_low": comparison.difference.low, "ci_high": comparison.difference.high,
         "unit": comparison.difference.unit, "n": len(gt3) + len(proto),
         "p_value": comparison.p_value},
    ]

    # --- 2. An interval on the pit-loss correlation -------------------------
    correlation = correlation_over_units(pit_loss_groups(), _class_summary)
    rows.append({
        "result": "pit loss vs tyre-limited share (r)",
        "estimate": correlation.estimate, "ci_low": correlation.low,
        "ci_high": correlation.high, "unit": correlation.unit,
        "n": correlation.draws, "p_value": "",
    })

    # --- 3. How well located is the cheap-stop edge? ------------------------
    plans = pd.read_csv(ENDURANCE_DERIVED_DIR / "multistop_plans.csv")
    plans["tyre_limited"] = plans["optimal_stops"] != plans["min_stops"]
    tyre_limited = plans.loc[plans["tyre_limited"], "pit_loss_s"].to_numpy(float)
    edge = boundary_sensitivity(tyre_limited)
    rows.append({
        "result": "cheap-stop edge (s)", "estimate": edge["maximum"],
        "ci_low": edge["without_the_defining_point"], "ci_high": edge["maximum"],
        "unit": "leave-one-out on the defining race", "n": int(edge["n"]),
        "p_value": "",
    })

    frame = pd.DataFrame(rows)
    CROSS_DERIVED.mkdir(parents=True, exist_ok=True)
    frame.to_csv(CROSS_DERIVED / "formal_tests.csv", index=False)

    significant = comparison.difference.excludes_zero
    lines = [
        "<!-- GENERATED by scripts/run_formal_tests.py — do not edit by hand. -->",
        "",
        "# Intervals and tests for the three headline results",
        "",
        "Every headline in this project was described rather than tested. Two "
        "numbers were compared with nothing said about how far either could "
        "move; a correlation was quoted without an interval; a threshold was "
        "quoted as if it were a calibrated constant. This is that gap closed, "
        "and where a test does not apply, it says so instead of supplying one "
        "that looks like it does.",
        "",
        "## 1. Do GT3 slopes transfer better than prototype slopes?",
        "",
        f"One value per circuit-class — **{len(gt3)} GT3, {len(proto)} "
        "prototype** — never one per fold. Folds inside a circuit-class share "
        "a pooled fitted slope, so treating them as independent would quadruple "
        "the apparent sample and narrow every interval here.",
        "",
        "| group | mean LORO within-stint R² | 95% interval |",
        "|---|---|---|",
        f"| GT3 (GTD, GTD PRO) | {gt3_mean.estimate:+.4f} | "
        f"[{gt3_mean.low:+.4f}, {gt3_mean.high:+.4f}] |",
        f"| prototype (GTP, Hypercar, LMP2) | {proto_mean.estimate:+.4f} | "
        f"[{proto_mean.low:+.4f}, {proto_mean.high:+.4f}] |",
        f"| **difference** | **{comparison.difference.estimate:+.4f}** | "
        f"[{comparison.difference.low:+.4f}, {comparison.difference.high:+.4f}] |",
        "",
        f"Permutation test on the group labels, {comparison.permutations:,} "
        f"relabellings: **p = {comparison.p_value:.4f}**.",
        "",
        (
            "The interval excludes zero and the permutation test agrees, so "
            "**the difference survives being tested** rather than merely "
            "being visible in a table."
            if significant and comparison.p_value < 0.05 else
            "The interval includes zero" + (
                " and the permutation test does not reject either"
                if comparison.p_value >= 0.05 else
                ", though the permutation test does reject"
            ) + ". **The claim as stated is not supported at this cluster "
            "count**, and the honest reading is that GT3's advantage rests on "
            "a handful of circuits rather than on the class."
        ),
        "",
        (
            "A permutation test is reported alongside the bootstrap because "
            f"with {min(len(gt3), len(proto))} clusters in the smaller group a "
            "bootstrap interval is doing well to be honest about its width."
            if min(len(gt3), len(proto)) < 20 else
            "Both are reported because they fail differently. The bootstrap "
            "assumes the clusters resemble the population they were drawn "
            "from; the permutation assumes only that the labels are "
            "exchangeable under the null. Agreement between two tests with "
            f"different assumptions, at {min(len(gt3), len(proto))} and "
            f"{max(len(gt3), len(proto))} clusters, is worth more than either "
            "alone."
        ),
        "",
        "## 2. An interval on the pit-loss correlation",
        "",
        f"**r = {correlation.estimate:+.3f}**, 95% interval "
        f"[{correlation.low:+.3f}, {correlation.high:+.3f}].",
        "",
        "Resampled over **races within each class**, recomputing every class "
        "summary inside each replicate — not over the six class points. A "
        "bootstrap with n = 6 would produce an interval, and it would be "
        "decoration: the variation that exists is between races, and that is "
        "the level this propagates.",
        "",
        "## 3. How well located is the 22.5 s edge?",
        "",
        "**Not an interval, because a bootstrap is the wrong instrument here.** "
        "The threshold is a *maximum* — the largest pit loss at which any race "
        "is still tyre-limited — so the statistic sits on the boundary of its "
        "own support. Resampling gives a distribution that is degenerate above "
        "the maximum and understates the uncertainty below it. Reporting a "
        "percentile interval would be putting a number where a caveat belongs.",
        "",
        "What is informative is leave-one-out on the only observation the "
        "estimate depends on:",
        "",
        "| | pit loss |",
        "|---|---|",
        f"| the edge | **{edge['maximum']:.1f} s** |",
        f"| with the single race defining it removed | "
        f"**{edge['without_the_defining_point']:.1f} s** |",
        f"| gap | {edge['gap']:.1f} s ({edge['relative_gap']:.0%} of the edge) |",
        f"| tyre-limited races in total | {int(edge['n'])} |",
        "",
        f"The edge drops **{edge['relative_gap']:.0%}** when one race is "
        "removed. The *rule* — a cheap stop is necessary — rests on 150 "
        "race-seasons above the edge with no exception; the *constant* rests on "
        "one race. Quote the rule, and quote the number as an order of "
        "magnitude.",
        "",
        "## What is still not tested",
        "",
        "The audit's 12-lap gap carries no interval here, and deliberately: it "
        "is a median over decisions that are not independent — several drivers "
        "from the same race share a track, a Safety Car and a tyre allocation. "
        "A bootstrap over decisions would understate its width and a bootstrap "
        "over races would need a clustering the audit table does not currently "
        "carry. Stating that is more useful than an interval that is wrong in a "
        "direction which flatters the result.",
        "",
    ]

    (CROSS_SERIES / "formal_tests.md").write_text("\n".join(lines), encoding="utf-8")
    print(frame.to_string(index=False))
    print(f"\nwrote {CROSS_SERIES / 'formal_tests.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
