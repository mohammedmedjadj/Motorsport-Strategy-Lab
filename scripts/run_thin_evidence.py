"""Which published claims rest on one race, one fold or one circuit?

A reviewer attacks the thinnest evidence first, so it is better to find it
yourself and say so. This walks every committed artifact behind a headline
claim and reports how much data actually sits under it — not whether the number
is right, but how far it could move if one race went the other way.

Nothing here says a result is wrong. Some of these are fine and the report says
which. What it refuses to do is let a number with three races behind it read the
same as one with sixty.

Writes ``reports/cross_series/thin_evidence.md``.

Usage (offline, from the repo root)::

    python scripts/run_thin_evidence.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from src.ingestion.config import (  # noqa: E402
    ENDURANCE_DERIVED_DIR,
    F1_DERIVED_DIR,
    REPORTS_DIR,
)

OUT = REPORTS_DIR / "cross_series" / "thin_evidence.md"

#: Below this many independent observations, a per-circuit constant is a
#: sample rather than a measurement. Three seasons is the point at which a
#: leave-one-out fold still leaves two to average, which is the least that
#: makes the exercise mean anything.
THIN = 4


def _cheap_stop_edge() -> tuple[str, list[str]]:
    plans = pd.read_csv(ENDURANCE_DERIVED_DIR / "multistop_plans.csv")
    plans["tyre_limited"] = plans["optimal_stops"] != plans["min_stops"]
    limited = plans[plans["tyre_limited"]].nlargest(3, "pit_loss_s")
    top = limited.iloc[0]
    second = limited.iloc[1]
    drop = 100 * (top["pit_loss_s"] - second["pit_loss_s"]) / top["pit_loss_s"]
    lines = [
        f"The edge sits at **{top['pit_loss_s']:.1f} s** because one race puts "
        f"it there: {top['series'].upper()} {top['car_class']} at "
        f"{top['circuit']} in {int(top['year'])}. The next tyre-limited race is "
        f"{second['series'].upper()} {second['car_class']} at "
        f"{second['circuit']} {int(second['year'])}, at "
        f"{second['pit_loss_s']:.1f} s — so removing one race moves the "
        f"threshold by {drop:.0f}%.",
        "",
        "The **rule** is not thin: "
        f"{int((plans['pit_loss_s'] > top['pit_loss_s']).sum())} race-seasons "
        "sit above the edge and none of them is tyre-limited, across every "
        "class. It is the constant that rests on one race, and a bootstrap "
        "cannot fix that — the statistic is a maximum, so it sits on the "
        "boundary of its own support.",
        "",
        "**Already stated** in `when_tyres_beat_fuel.md`, `synthesis.md` and "
        "the paper. Quote the rule; treat the number as an order of magnitude.",
    ]
    return "The cheap-stop threshold", lines


def _transfer_folds() -> tuple[str, list[str]]:
    loro = pd.read_csv(ENDURANCE_DERIVED_DIR / "endurance_degradation_loro.csv")
    mean = loro[loro["held_out_season"].astype(str) == "MEAN"].dropna(
        subset=["r2_within"]
    )
    folds = loro[loro["held_out_season"].astype(str) != "MEAN"]

    rows = ["| circuit-class | published mean | folds | the folds themselves | spread |",
            "|---|---|---|---|---|"]
    worst = None
    for row in mean.nlargest(5, "r2_within").itertuples():
        matching = folds[
            (folds["series"] == row.series) & (folds["event"] == row.event)
            & (folds["car_class"] == row.car_class)
        ]["r2_within"].dropna()
        values = ", ".join(f"{v:+.3f}" for v in matching)
        spread = float(matching.max() - matching.min()) if len(matching) else 0.0
        rows.append(
            f"| {row.event} {row.car_class} | **{row.r2_within:+.3f}** | "
            f"{len(matching)} | {values} | {spread:.3f} |"
        )
        if len(matching) <= 2 and (worst is None or spread > worst[1]):
            worst = (f"{row.event} {row.car_class}", spread, row.r2_within,
                     matching.min(), matching.max(), len(matching))

    lines = ["Every headline transfer number is a mean over leave-one-race-out "
             "folds. How many folds, and how far apart they sit:", "", *rows, ""]
    if worst:
        name, spread, mean_value, low, high, n = worst
        lines += [
            f"**{name} is the weak one.** Its {mean_value:+.3f} is the mean of "
            f"{n} folds that run {low:+.3f} to {high:+.3f} — a spread of "
            f"{spread:.3f}, which is larger than most circuit-classes' entire "
            "score. It should not be quoted beside a number averaged over five "
            "or six folds without saying so.",
            "",
            "The neighbouring Lime Rock GTD figure is a different case: three "
            "folds sitting within 0.024 of each other. Same circuit, same "
            "protocol, far more stable — which is itself worth knowing, since "
            "it says the instability is not a property of the circuit alone.",
        ]
    return "Transfer scores built on two folds", lines


def _thin_circuits() -> tuple[str, list[str]]:
    coefficients = pd.read_csv(F1_DERIVED_DIR / "degradation_coefficients.csv")
    swaps = pd.read_csv(F1_DERIVED_DIR / "overtaking_difficulty.csv")
    sc = pd.read_csv(F1_DERIVED_DIR / "sc_model.csv")

    races = coefficients.groupby("circuit")["compound_races"].max()
    thin_fit = races[races < THIN].sort_values()
    thin_swap = swaps[swaps["n_races"] < THIN].sort_values("n_races")
    thin_sc = sc[sc["n_editions"] < THIN].sort_values("n_editions")

    ratio = swaps["adj_swap_rate"].max() / swaps["adj_swap_rate"].min()
    fastest = swaps.nlargest(1, "adj_swap_rate").iloc[0]
    slowest = swaps.nsmallest(1, "adj_swap_rate").iloc[0]

    lines = [
        f"The project quotes a **{ratio:.0f}-fold** track-position range from "
        f"{slowest['circuit']} to {fastest['circuit']}. The high end rests on "
        f"**{int(fastest['n_races'])} races** at a circuit first run in 2023; "
        f"the low end on {int(slowest['n_races'])}.",
        "",
        f"Circuits whose constants come from fewer than {THIN} observations:",
        "",
        "| circuit | degradation races | track-position races | SC editions |",
        "|---|---|---|---|",
    ]
    circuits = sorted(set(thin_fit.index) | set(thin_swap["circuit"])
                      | set(thin_sc["circuit"]))
    for circuit in circuits:
        fit = races.get(circuit, float("nan"))
        swap = thin_swap[thin_swap["circuit"] == circuit]["n_races"]
        editions = thin_sc[thin_sc["circuit"] == circuit]["n_editions"]
        lines.append(
            f"| {circuit} | {'—' if pd.isna(fit) else int(fit)} | "
            f"{int(swap.iloc[0]) if len(swap) else '—'} | "
            f"{int(editions.iloc[0]) if len(editions) else '—'} |"
        )

    worst_fit = thin_fit.index[0] if len(thin_fit) else None
    if worst_fit is not None:
        lines += [
            "",
            f"**{worst_fit} is the extreme case**: its degradation "
            f"coefficients come from {int(thin_fit.iloc[0])} race, and its "
            "track-position constant from one too. Both feed the simulator "
            "like any other circuit's, and neither is a measurement in the "
            "sense the others are.",
        ]

    lines += [
        "",
        "The safety-car layer handles this correctly already — a Jeffreys prior "
        "and a credible interval, so a circuit with three editions gets a wide "
        "band rather than false precision. Monaco's much-quoted "
        f"{float(sc[sc['circuit'] == 'monaco']['sc_p_occurrence'].iloc[0]):.2f} "
        "carries an interval of "
        f"[{float(sc[sc['circuit'] == 'monaco']['sc_p_occurrence_ci_low'].iloc[0]):.2f}, "
        f"{float(sc[sc['circuit'] == 'monaco']['sc_p_occurrence_ci_high'].iloc[0]):.2f}] "
        "for exactly this reason, and the width is as much the result as the "
        "point.",
        "",
        "The degradation and track-position layers do not do the same thing. "
        "They report a per-circuit constant with a cluster-robust interval on "
        "the *slope*, which says nothing about how few races produced it.",
    ]
    return "Circuits with almost no data behind their constants", lines


def main() -> int:
    sections = [_cheap_stop_edge(), _transfer_folds(), _thin_circuits()]

    lines = [
        "<!-- GENERATED by scripts/run_thin_evidence.py — do not edit by hand. -->",
        "",
        "# Where the evidence is thin",
        "",
        "A reviewer goes for the weakest number first. This finds them before "
        "that happens, by walking the artifacts behind each headline claim and "
        "counting what actually sits underneath.",
        "",
        "None of this says a result is wrong. Some of these are perfectly "
        "sound and the report says which. What it will not do is let a number "
        "with three races behind it read the same as one with sixty.",
        "",
    ]
    for index, (heading, body) in enumerate(sections, 1):
        lines += [f"## {index}. {heading}", "", *body, ""]

    lines += [
        "## What is not thin",
        "",
        "Worth stating, so the list above is not read as a general disclaimer.",
        "",
        "The decision audit rests on 1,280 replayed stops and the baseline "
        "comparison on 1,263 of them, both under one criterion. The pit-loss "
        "correlation is computed across 205 race-seasons and its interval is "
        "bootstrapped over races rather than over the six class summaries. The "
        "transfer difference between GT3 and prototype classes uses 51 "
        "circuit-classes with a permutation test alongside the bootstrap. "
        "Those four are the load-bearing results and none of them turns on a "
        "handful of races.",
        "",
    ]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
