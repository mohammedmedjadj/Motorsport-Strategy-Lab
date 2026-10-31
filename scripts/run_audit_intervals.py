"""Race-clustered intervals for the audit median, and the regime check that bites.

Two objections, both answerable from committed tables.

**The audit median carries no interval.** The paper declines to publish one,
reasoning that a bootstrap over decisions would be too narrow and that a
bootstrap over races needs a clustering the audit table does not carry. The
second half is wrong: ``data/derived/f1/systematic_audit.csv`` carries season and
circuit, and the endurance table carries series, year and event. Those are race
identifiers. Resampling whole races is available, so the interval is published
here, and a class whose interval contains zero is named rather than reported as
a finding.

**Result 2's separation might be a class label in disguise.** One reading takes
the AUC gap between pit loss and net degradation slope as an artefact of pit loss
having the wider spread. That mechanism does not exist — AUC is a rank statistic
and is unchanged by any monotone rescaling, which is checked here rather than
asserted. The version of the worry that does bite is different: if pit loss were
near-constant within a class, its AUC would be measuring class identity. So the
separation is recomputed *inside* each class, where class identity is held fixed
and cannot do any work.

Writes ``data/derived/cross_series/audit_intervals.csv`` and
``reports/cross_series/audit_intervals.md``.

    python scripts/run_audit_intervals.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

DRAWS = 10_000
SEED = 20261027

F1_AUDIT = REPO / "data" / "derived" / "f1" / "systematic_audit.csv"
END_AUDIT = REPO / "data" / "derived" / "endurance" / "systematic_audit.csv"
PLANS = REPO / "data" / "derived" / "endurance" / "multistop_plans.csv"
OUT_CSV = REPO / "data" / "derived" / "cross_series" / "audit_intervals.csv"
OUT_MD = REPO / "reports" / "cross_series" / "audit_intervals.md"


def cluster_bootstrap_median(
    frame: pd.DataFrame, race_keys: list[str], rng, value: str = "delta_laps"
) -> dict:
    """Percentile interval on the median, resampling whole races.

    Decisions inside one race share a track, a tyre allocation and whatever
    neutralisations happened, so the race is the unit that varies. Resampling
    decisions would narrow the interval in the direction that flatters the
    result, which is why the paper refused to do it.
    """
    frame = frame.dropna(subset=[value])
    key = frame[race_keys].astype(str).agg("_".join, axis=1)
    groups = [g[value].to_numpy(dtype=float) for _, g in frame.groupby(key)]
    n = len(groups)
    draws = np.empty(DRAWS)
    for i in range(DRAWS):
        picked = rng.integers(0, n, size=n)
        draws[i] = np.median(np.concatenate([groups[j] for j in picked]))
    low, high = (float(x) for x in np.percentile(draws, [2.5, 97.5]))
    return {
        "median_delta_laps": float(np.median(frame[value])),
        "ci_low": low,
        "ci_high": high,
        "n_decisions": int(len(frame)),
        "n_races": n,
        "contains_zero": bool(low <= 0 <= high),
    }


def auc(score: np.ndarray, positive: np.ndarray) -> float:
    """Rank-based AUC, tie-aware. Invariant to any monotone rescaling of score."""
    score, positive = np.asarray(score, dtype=float), np.asarray(positive, dtype=bool)
    ok = np.isfinite(score)
    score, positive = score[ok], positive[ok]
    pos, neg = score[positive], score[~positive]
    if not len(pos) or not len(neg):
        return float("nan")
    ranks = pd.Series(np.concatenate([pos, neg])).rank().to_numpy()
    return float(
        (ranks[: len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))
    )


def main() -> int:
    rng = np.random.default_rng(SEED)
    rows: list[dict] = []

    f1 = pd.read_csv(F1_AUDIT)
    rows.append(
        {"scope": "Formula 1", **cluster_bootstrap_median(f1, ["season", "circuit"], rng)}
    )
    end = pd.read_csv(END_AUDIT)
    for car_class, sub in end.groupby("car_class"):
        rows.append(
            {
                "scope": str(car_class),
                **cluster_bootstrap_median(sub, ["series", "year", "event"], rng),
            }
        )
    rows.append(
        {
            "scope": "all endurance",
            **cluster_bootstrap_median(end, ["series", "year", "event"], rng),
        }
    )
    table = pd.DataFrame(rows)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT_CSV, index=False)

    # --- Result 2, the check that is not scale-dependent -------------------
    plans = pd.read_csv(PLANS)
    plans["tyre_limited"] = plans["optimal_stops"] != plans["min_stops"]
    y = plans["tyre_limited"].to_numpy(dtype=bool)
    standardise = lambda v: (v - np.nanmean(v)) / np.nanstd(v)  # noqa: E731

    overall_pit = auc(-plans["pit_loss_s"].to_numpy(), y)
    overall_slope = auc(plans["net_slope_s"].to_numpy(), y)
    standardised_pit = auc(standardise(-plans["pit_loss_s"].to_numpy()), y)
    class_mean = plans.groupby("car_class")["pit_loss_s"].transform("mean").to_numpy()
    label_only = auc(-class_mean, y)
    within_total = plans.groupby("car_class")["pit_loss_s"].transform("var").mean()
    within_share = float(within_total / plans["pit_loss_s"].var())

    within: list[tuple[str, int, int, float]] = []
    for car_class, sub in plans.groupby("car_class"):
        a = auc(-sub["pit_loss_s"].to_numpy(), sub["tyre_limited"].to_numpy(dtype=bool))
        within.append((str(car_class), len(sub), int(sub["tyre_limited"].sum()), a))

    # The regime check went to the report only, so the manuscript could not
    # quote it without retyping a number -- which is the one thing this project
    # does not allow. It is an artifact now.
    regime_csv = REPO / "data" / "derived" / "cross_series" / "regime_within_class.csv"
    pd.DataFrame(
        [
            {
                "quantity": "pit loss",
                "auc": overall_pit,
                "car_class": "all",
                "race_seasons": len(plans),
                "tyre_limited": int(y.sum()),
            },
            {
                "quantity": "net degradation slope",
                "auc": overall_slope,
                "car_class": "all",
                "race_seasons": len(plans),
                "tyre_limited": int(y.sum()),
            },
            {
                "quantity": "pit loss, standardised",
                "auc": standardised_pit,
                "car_class": "all",
                "race_seasons": len(plans),
                "tyre_limited": int(y.sum()),
            },
            {
                "quantity": "class identity alone",
                "auc": label_only,
                "car_class": "all",
                "race_seasons": len(plans),
                "tyre_limited": int(y.sum()),
            },
            {
                "quantity": "within-class variance share of pit loss",
                "auc": within_share,
                "car_class": "all",
                "race_seasons": len(plans),
                "tyre_limited": int(y.sum()),
            },
        ]
        + [
            {
                "quantity": "pit loss, within class",
                "auc": a,
                "car_class": c,
                "race_seasons": n,
                "tyre_limited": n_lim,
            }
            for c, n, n_lim, a in within
        ]
    ).to_csv(regime_csv, index=False)

    zero = table[table["contains_zero"]]["scope"].tolist()
    lines = [
        "<!-- GENERATED by scripts/run_audit_intervals.py — do not edit by hand. "
        "Every number here is read from a committed artifact; change the data or the "
        "generator, not this file. -->",
        "",
        "# Intervals the audit can carry, and the regime check that is not about scale",
        "",
        "## The audit median, with a race-clustered interval",
        "",
        "Decisions inside one race are not independent, so the race is the unit "
        "resampled. The audit tables carry race identifiers, so this interval is "
        "available and is published rather than declined.",
        "",
        "| scope | median | 95% CI | decisions | races |",
        "|---|---|---|---|---|",
    ]
    for _, r in table.iterrows():
        flag = " — **contains zero**" if r["contains_zero"] else ""
        lines.append(
            f"| {r['scope']} | {r['median_delta_laps']:+.1f} | "
            f"[{r['ci_low']:+.1f}, {r['ci_high']:+.1f}] | "
            f"{int(r['n_decisions'])} | {int(r['n_races'])} |{flag}"
        )
    lines += [
        "",
        (
            f"The gap is away from zero everywhere except **{', '.join(zero)}**, where it "
            "is not established and should not be read as a finding."
            if zero
            else "No interval contains zero."
        ),
        "",
        "## Result 2: is the separation a class label?",
        "",
        f"- AUC, pit loss: **{overall_pit:.4f}**; net degradation slope: "
        f"**{overall_slope:.4f}**.",
        f"- The same AUC after standardising pit loss: **{standardised_pit:.4f}**. AUC is "
        "a rank statistic, so rescaling cannot move it, and the proposed correction "
        "changes nothing.",
        f"- Class identity alone, ranking by each class's mean pit loss: "
        f"**{label_only:.4f}** — well short of pit loss itself.",
        f"- **{within_share:.0%}** of the variance in pit loss is *within* class rather "
        "than between: pit loss is a property of the circuit's pit lane, not of the car.",
        "",
        "Separation recomputed inside each class, where class identity is fixed:",
        "",
        "| class | race-seasons | tyre-limited | AUC of pit loss |",
        "|---|---|---|---|",
    ]
    for car_class, n, n_limited, a in within:
        shown = f"{a:.4f}" if np.isfinite(a) else "undefined — one regime only"
        lines.append(f"| {car_class} | {n} | {n_limited} | {shown} |")
    lines += [
        "",
        "Where both regimes occur, the cost of the stop still separates them inside "
        "the class. The separation is therefore not class identity wearing a "
        "continuous disguise.",
        "",
    ]
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(table.to_string(index=False))
    print(f"\nwrote {OUT_CSV}\nwrote {OUT_MD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
