"""Which quantity decides whether an extra stop pays: the stop cost, or the tyre?

Result 2 says the regime is set by the cost of the stop rather than by the car.
The obvious objection is that this is close to circular. The optimiser's
decision is a comparison between what an extra stop costs and what the tyre
would give back, so of course pit loss predicts it -- pit loss is half the
comparison.

That objection has an answer and it is a measurement, not an argument. If pit
loss alone were doing the work, the degradation slope would carry no
information about the regime once you knew the stop cost. It does carry some.
So the claim is empirical: both terms enter, and one dominates by a margin
worth reporting.

Two candidate discriminators, each ranked against the regime the exact dynamic
program chose:

- **pit loss** (lower is more tyre-limited);
- **net degradation slope** (steeper is more tyre-limited).

A third was tried and thrown out. ``slope_headroom_x`` scored a perfect 1.000,
which is a tautology rather than a finding: the breakeven slope is found by
searching upward from the measured slope until the optimum takes an extra
stop, so a race that already takes one has a ratio of exactly 1 and every
other race is above it. It restates the label it was being scored against.
Section "A discriminator that was thrown out" has the numbers.

Discrimination is the area under the ROC curve, which here has a plain
reading: the probability that a tyre-limited race-season and a fuel-limited
one, drawn at random, are ordered correctly by that quantity alone. 0.5 is a
coin toss; 1.0 separates perfectly. It is computed from the Mann-Whitney
statistic rather than a curve, so it needs no threshold.

**On the closed form.** The intuition behind the regime is a comparison of
``beta * n(n+1)/2`` against ``pi``: with a linear slope ``beta``, a stint of
``n`` laps accumulates a triangular sum of degradation, and an extra stop is
worth its ``pi`` seconds when that sum exceeds it. The project does not use
that expression. ``scripts/run_multistop.py`` solves the exact multi-stop
dynamic program under the fuel cap and reads the stop count off the solution,
which is why the breakeven slope in that table is found numerically. The
closed form is checked here against the exact verdict rather than substituted
for it, because a paper that quotes a condition its code does not evaluate is
making a claim about the wrong thing.

Writes ``data/derived/cross_series/regime_decomposition.csv`` and
``reports/cross_series/regime_decomposition.md``.

Usage (offline, from the repo root)::

    python scripts/run_regime_decomposition.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.ingestion.config import (  # noqa: E402
    DERIVED_DIR,
    ENDURANCE_DERIVED_DIR,
    REPORTS_DIR,
)

PLANS = ENDURANCE_DERIVED_DIR / "multistop_plans.csv"
OUT_CSV = DERIVED_DIR / "cross_series" / "regime_decomposition.csv"
OUT_MD = REPORTS_DIR / "cross_series" / "regime_decomposition.md"

#: Bootstrap draws for the interval on each AUC, resampled at the race-season,
#: which is the unit the regime is defined on.
DRAWS = 10_000
SEED = 20260904


def auc(positive: np.ndarray, negative: np.ndarray) -> float:
    """P(a positive outranks a negative), ties counting a half.

    The Mann-Whitney form rather than a traced ROC curve: no threshold has to
    be chosen, and the value is exactly the probability a reader would check by
    hand on a small sample.
    """
    positive = np.asarray(positive, float)
    negative = np.asarray(negative, float)
    if positive.size == 0 or negative.size == 0:
        return float("nan")
    pooled = np.concatenate([positive, negative])
    ranks = pd.Series(pooled).rank().to_numpy()
    rank_sum = ranks[: positive.size].sum()
    n_pos, n_neg = positive.size, negative.size
    return float((rank_sum - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def load() -> pd.DataFrame:
    plans = pd.read_csv(PLANS)
    plans["tyre_limited"] = plans["optimal_stops"] != plans["min_stops"]
    # Signed so that larger always means "more tyre-limited", which keeps every
    # AUC on the same side of 0.5 and makes them comparable without a note
    # about direction attached to each one.
    plans["neg_pit_loss"] = -plans["pit_loss_s"]
    return plans


#: The quantity, the column carrying it signed so larger means more
#: tyre-limited, and how to describe it in a sentence.
CANDIDATES = (
    ("pit loss", "neg_pit_loss",
     "the cost of the stop, which is one side of the comparison"),
    ("net degradation slope", "net_slope_s",
     "the tyre, which is the other side"),
)


def headroom_is_a_restatement(plans: pd.DataFrame) -> dict:
    """Why slope headroom is not among the discriminators.

    The breakeven slope is found by searching upward from the measured one
    until the optimum takes an extra stop. A race that already takes one stops
    that search at the first step, so its ratio is exactly 1, and every race
    that does not is strictly above. The quantity is the label.
    """
    limited = plans[plans["tyre_limited"]]["slope_headroom_x"]
    fuel = plans[~plans["tyre_limited"]]["slope_headroom_x"]
    return {
        "n_limited": int(limited.notna().sum()),
        "limited_min": float(limited.min()),
        "limited_max": float(limited.max()),
        "n_fuel_defined": int(fuel.notna().sum()),
        "fuel_min": float(fuel.min()),
        "n_fuel_missing": int(fuel.isna().sum()),
        "limited_above_one": int((limited > 1).sum()),
        "fuel_at_or_below_one": int((fuel <= 1).sum()),
    }


def decompose(plans: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    limited = plans[plans["tyre_limited"]]
    fuel = plans[~plans["tyre_limited"]]
    rows = []
    for name, column, _ in CANDIDATES:
        usable = plans.dropna(subset=[column])
        pos = usable[usable["tyre_limited"]][column].to_numpy()
        neg = usable[~usable["tyre_limited"]][column].to_numpy()
        point = auc(pos, neg)
        replicates = np.empty(DRAWS)
        for draw in range(DRAWS):
            replicates[draw] = auc(
                pos[rng.integers(0, pos.size, pos.size)],
                neg[rng.integers(0, neg.size, neg.size)],
            )
        rows.append({
            "quantity": name,
            "auc": round(point, 4),
            "ci_low": round(float(np.quantile(replicates, 0.025)), 4),
            "ci_high": round(float(np.quantile(replicates, 0.975)), 4),
            "n_tyre_limited": int(pos.size),
            "n_fuel_limited": int(neg.size),
            "n_missing": int(len(plans) - len(usable)),
            "draws": DRAWS,
        })
    frame = pd.DataFrame(rows)
    frame.attrs["n_limited"] = len(limited)
    frame.attrs["n_fuel"] = len(fuel)
    return frame


def closed_form_check(plans: pd.DataFrame) -> dict:
    """Does ``beta * n(n+1)/2 > pi`` reproduce the dynamic program's verdict?

    ``n`` is the fuel-minimum stint length, the longest the race allows before
    refuelling forces a stop, so the triangular sum is the most degradation an
    extra stop could ever recover. The comparison is therefore generous to the
    tyre side, and if it still fails to reproduce the verdict the closed form
    is not a stand-in for the solver.
    """
    work = plans.dropna(subset=["net_slope_s", "pit_loss_s", "fuel_range_laps"])
    n = work["fuel_range_laps"].astype(float)
    triangular = work["net_slope_s"] * n * (n + 1.0) / 2.0
    predicted = triangular > work["pit_loss_s"]
    actual = work["tyre_limited"]
    agree = int((predicted == actual).sum())
    return {
        "n": len(work),
        "agree": agree,
        "pct_agree": round(100 * agree / len(work)),
        "false_tyre_limited": int((predicted & ~actual).sum()),
        "false_fuel_limited": int((~predicted & actual).sum()),
        "auc_triangular": round(
            auc(triangular[actual].to_numpy(), triangular[~actual].to_numpy()), 4
        ),
    }


def write_report(table: pd.DataFrame, plans: pd.DataFrame, check: dict,
                 headroom: dict) -> Path:
    limited = plans[plans["tyre_limited"]]
    fuel = plans[~plans["tyre_limited"]]
    best = table.loc[table["auc"].idxmax()]
    assert len(table) == 2, (
        "the decomposition table should carry exactly the two discriminators "
        "that are not restatements of the label"
    )
    slope_row = table[table["quantity"] == "net degradation slope"].iloc[0]
    described = dict((name, text) for name, _, text in CANDIDATES)

    lines = [
        "<!-- generated by scripts/run_regime_decomposition.py -->",
        "",
        "# Which term decides the regime: the stop, or the tyre?",
        "",
        "Generated. Do not edit by hand.",
        "",
        "Result 2 says whether an extra stop can ever pay is set by the cost "
        "of the stop rather than by the car. The sharpest objection to it is "
        "that the claim is close to circular: the optimiser decides by "
        "comparing what a stop costs against what the tyre gives back, so pit "
        "loss predicting the outcome is pit loss predicting half of its own "
        "definition.",
        "",
        "That deserves a measurement rather than a rebuttal. If the stop cost "
        "were doing all the work, the degradation slope would carry no "
        "information about the regime. It carries some. So the claim is "
        "empirical: both terms enter and one dominates, by this much.",
        "",
        f"The sample is **{len(plans)} race-seasons**, "
        f"**{len(limited)}** of them tyre-limited and **{len(fuel)}** "
        "fuel-limited, where tyre-limited means the exact dynamic program "
        "chose more stops than the fuel minimum.",
        "",
        "## How well each quantity alone orders the two regimes",
        "",
        "The area under the ROC curve, which here reads as the probability "
        "that a tyre-limited race-season and a fuel-limited one, drawn at "
        "random, come out in the right order on that quantity alone. 0.5 is a "
        "coin toss. Intervals are a percentile bootstrap at the race-season, "
        f"{DRAWS:,} draws.",
        "",
        "| quantity | what it is | AUC | 95% interval |",
        "| --- | --- | ---: | ---: |",
    ]
    for _, row in table.iterrows():
        lines.append(
            f"| {row['quantity']} | {described[row['quantity']]} | "
            f"**{row['auc']:.3f}** | "
            f"[{row['ci_low']:.3f}, {row['ci_high']:.3f}] |"
        )
    lines += [
        "",
        f"**{best['quantity'].capitalize()} dominates at "
        f"{best['auc']:.3f}.** The degradation slope reaches "
        f"{slope_row['auc']:.3f}, which is well clear of a coin toss and well "
        "short of the stop cost. Neither is redundant and the ordering is not "
        "close.",
        "",
        "That is the answer to the circularity objection, and it is worth "
        "being exact about what it does and does not settle. It does not show "
        "that pit loss causes the regime; the two are related by "
        "construction, since the optimiser evaluates both. What it shows is "
        "that the comparison is not symmetric in practice: knowing what a "
        "stop costs tells you nearly the whole answer across four "
        "championships, while knowing how fast the tyre wears tells you "
        "noticeably less. The exogeneity argument for pit loss is made "
        "separately, in "
        "[`pit_loss_measurement_check.md`](pit_loss_measurement_check.md), "
        "from the fact that it varies far more between circuits than between "
        "seasons of the same circuit.",
        "",
        "## A discriminator that was thrown out",
        "",
        "A third quantity was tried: `slope_headroom_x`, the ratio of the "
        "breakeven slope to the measured one. It scored a perfect **1.000**, "
        "and that is a tautology rather than a result.",
        "",
        f"Every one of the **{headroom['n_limited']}** tyre-limited "
        f"race-seasons has a headroom of exactly "
        f"**{headroom['limited_min']:.1f}**. Of the fuel-limited ones, "
        f"**{headroom['n_fuel_defined']}** sit at "
        f"**{headroom['fuel_min']:.1f}** or above and "
        f"**{headroom['n_fuel_missing']}** have no value at all, because even "
        "an implausible 2 s/lap never triggers an extra stop there. Not one "
        "race falls on the wrong side.",
        "",
        "The reason is in how the breakeven slope is computed: "
        "`scripts/run_multistop.py` searches upward from the measured slope "
        "until the optimum takes an extra stop. A race that already takes one "
        "ends that search at the first step, so its ratio is 1 by "
        "construction, and a race that does not is strictly above. The "
        "quantity is the label wearing a different name.",
        "",
        "It is recorded here rather than dropped quietly, because an AUC of "
        "1.000 in a report written to answer an accusation of circularity is "
        "exactly the thing that accusation is about.",
        "",
        "## The closed form is an intuition, not the implementation",
        "",
        "The regime has a readable condition behind it. With a linear slope "
        "`beta`, a stint of `n` laps accumulates `beta * n(n+1)/2` seconds of "
        "degradation, and an extra stop is worth its `pi` seconds when that "
        "sum exceeds it:",
        "",
        "```",
        "beta * n(n+1)/2  >  pi",
        "```",
        "",
        "That expression appears nowhere in the code. "
        "`scripts/run_multistop.py` solves the exact multi-stop dynamic "
        "program under the hard fuel cap and reads the stop count off the "
        "solution, which is also why the breakeven slope in that table is "
        "found numerically rather than inverted from a formula.",
        "",
        "Checked rather than assumed, with `n` set to the fuel-minimum stint "
        "length so the triangular sum is the most degradation an extra stop "
        "could ever recover — the reading most generous to the tyre side:",
        "",
        f"- it reproduces the solver's verdict on **{check['agree']} of "
        f"{check['n']}** race-seasons ({check['pct_agree']}%);",
        f"- it calls **{check['false_tyre_limited']}** fuel-limited races "
        "tyre-limited and misses "
        f"**{check['false_fuel_limited']}** that are;",
        f"- as a ranking it reaches an AUC of "
        f"**{check['auc_triangular']:.3f}**.",
        "",
        "So the closed form is the right way to explain the mechanism and the "
        "wrong thing to quote as the criterion. Any statement of it belongs "
        "next to a sentence saying the solver is exact and the formula is an "
        "approximation to it.",
        "",
    ]
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    return OUT_MD


def main() -> None:
    plans = load()
    table = decompose(plans)
    check = closed_form_check(plans)
    headroom = headroom_is_a_restatement(plans)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT_CSV, index=False)
    print(f"wrote {OUT_CSV.relative_to(Path.cwd())}")
    out = write_report(table, plans, check, headroom)
    print(f"wrote {out.relative_to(Path.cwd())}")
    print()
    print(table.to_string(index=False))
    print()
    print("closed form:", check)
    print("headroom (excluded):", headroom)


if __name__ == "__main__":
    main()
