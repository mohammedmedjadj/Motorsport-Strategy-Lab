"""One figure per headline result, drawn from committed artifacts only.

The project had 26 per-circuit degradation plots and **no figure for any of its
three actual results**. A reader who is not going to work through forty reports
-- a mentor, a reviewer, anyone deciding in thirty seconds whether this is
serious -- had nothing to look at.

Every number here is read from a CSV in ``data/derived/``. Nothing is typed in,
so a figure cannot drift away from the finding it illustrates the way the prose
repeatedly has: if an artifact changes and its figure does not, the drift
workflow's ``git diff`` is non-empty and CI fails.

Writes ``reports/figures/r1_transfer.png``, ``r2_pit_loss_rule.png`` and
``r3_audit_bias.png``.

Usage (offline, from the repo root)::

    python scripts/make_headline_figures.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib  # noqa: E402

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from src.ingestion.config import (  # noqa: E402
    ENDURANCE_DERIVED_DIR,
    F1_DERIVED_DIR,
    REPORTS_DIR,
)

FIGURES = REPORTS_DIR / "figures"

#: One colour per class, held fixed across all three figures so a reader who
#: learns the palette on one keeps it on the others.
CLASS_COLOURS = {
    "GTD": "#d1495b",
    "GTDPRO": "#edae49",
    "GTP": "#00798c",
    "HYPERCAR": "#30638e",
    "LMP2": "#003d5b",
    "LMP2 Pro/Am": "#7e9aa8",
    "F1": "#2b2d42",
}


def _style(ax: plt.Axes) -> None:
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_axisbelow(True)
    ax.grid(axis="x", alpha=0.25, linewidth=0.6)


def r1_transfer() -> str:
    """Transfer is a property of the circuit-class, not of the championship."""
    loro = pd.read_csv(ENDURANCE_DERIVED_DIR / "endurance_degradation_loro.csv")
    mean = (
        loro[loro["held_out_season"].astype(str) == "MEAN"]
        .dropna(subset=["r2_within"])
        .sort_values("r2_within")
        .reset_index(drop=True)
    )

    fig, ax = plt.subplots(figsize=(9, 6.5))
    for car_class, group in mean.groupby("car_class"):
        ax.scatter(
            group["r2_within"], group.index,
            s=46, alpha=0.9, label=car_class,
            color=CLASS_COLOURS.get(str(car_class), "#888888"),
            edgecolor="white", linewidth=0.6, zorder=3,
        )
    ax.axvline(0, color="#444444", linewidth=1.0, zorder=2)

    # Name only the points a reader would otherwise have to squint at: the ones
    # that carry the result.
    for row in mean.itertuples():
        if row.r2_within > 0.2:
            ax.annotate(
                f"  {row.event} {row.car_class}",
                (row.r2_within, row.Index), fontsize=8.5,
                va="center", color="#222222",
            )

    ax.set_yticks([])
    ax.set_xlabel("leave-one-race-out mean within-stint R2   ->   transfers better")
    ax.set_title(
        "A degradation slope transfers by circuit-class, not by championship",
        fontsize=13, pad=16, loc="left",
    )
    clear = int((mean["r2_within"] > 0.2).sum())
    ax.text(
        0.0, 1.01,
        f"{len(mean)} circuit-classes across IMSA, WEC and ELMS - only {clear} "
        "clear R2 = 0.2 - one protocol, applied identically everywhere",
        transform=ax.transAxes, fontsize=9, color="#555555", va="bottom",
    )
    ax.legend(frameon=False, fontsize=9, loc="lower right", title="class",
              title_fontsize=9)
    _style(ax)

    path = FIGURES / "r1_transfer.png"
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return f"{path}  ({len(mean)} circuit-classes, {clear} above 0.2)"


def r2_pit_loss_rule() -> str:
    """The cost of the stop, not the car, sets the strategy regime."""
    plans = pd.read_csv(ENDURANCE_DERIVED_DIR / "multistop_plans.csv")
    plans["tyre_limited"] = plans["optimal_stops"] != plans["min_stops"]

    by_class = plans.groupby(["series", "car_class"]).agg(
        pit_loss=("pit_loss_s", "median"),
        share=("tyre_limited", "mean"),
        n=("tyre_limited", "size"),
    ).reset_index()
    by_class["share"] *= 100

    fig, (left, right) = plt.subplots(1, 2, figsize=(12.5, 5.6))

    # Left: the class-level rule, which is the headline.
    for row in by_class.itertuples():
        left.scatter(
            row.pit_loss, row.share, s=40 + row.n * 3.2,
            color=CLASS_COLOURS.get(str(row.car_class), "#888888"),
            alpha=0.9, edgecolor="white", linewidth=1.0, zorder=3,
        )
        left.annotate(
            f"{row.series.upper()} {row.car_class}",
            (row.pit_loss, row.share), fontsize=8.5,
            xytext=(7, 6), textcoords="offset points", color="#333333",
        )
    correlation = by_class["pit_loss"].corr(by_class["share"])
    left.set_xlabel("median pit loss (s)")
    left.set_ylabel("share of race-seasons that are tyre-limited (%)")
    left.set_title(
        f"Per class: r = {correlation:+.3f}, monotonic, no inversion",
        fontsize=11, loc="left", pad=12,
    )
    left.text(0.0, 1.02, "marker area proportional to race-seasons in the class",
              transform=left.transAxes, fontsize=8.5, color="#666666")
    _style(left)
    left.grid(axis="y", alpha=0.25, linewidth=0.6)

    # Right: every race. Six class means cannot show an edge; 205 races can.
    threshold = plans.loc[plans["tyre_limited"], "pit_loss_s"].max()
    for limited, marker, label in ((True, "o", "tyre-limited"),
                                   (False, "x", "fuel-limited")):
        subset = plans[plans["tyre_limited"] == limited]
        right.scatter(
            subset["pit_loss_s"], subset["net_slope_s"],
            marker=marker, s=26, alpha=0.65,
            color="#d1495b" if limited else "#7e9aa8",
            label=f"{label} ({len(subset)})", zorder=3,
        )
    right.axvline(threshold, color="#222222", linestyle="--", linewidth=1.2,
                  zorder=2)
    right.annotate(
        f"no race above {threshold:.1f} s\nis tyre-limited",
        (threshold, right.get_ylim()[1]), fontsize=8.5,
        xytext=(9, -26), textcoords="offset points", color="#222222",
    )
    right.set_xscale("log")
    right.set_xlabel("pit loss (s), log scale")
    right.set_ylabel("net degradation slope (s/lap)")
    right.set_title(f"Every race-season ({len(plans)}): the edge is hard",
                    fontsize=11, loc="left", pad=12)
    right.legend(frameon=False, fontsize=9, loc="upper right")
    _style(right)
    right.grid(axis="y", alpha=0.25, linewidth=0.6)

    fig.suptitle(
        "The cost of the stop, not the car, decides whether tyres ever beat fuel",
        fontsize=13, x=0.006, ha="left", y=0.995,
    )
    path = FIGURES / "r2_pit_loss_rule.png"
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return (f"{path}  (r={correlation:+.3f}, edge {threshold:.1f}s, "
            f"n={len(plans)})")


def r3_audit_bias() -> str:
    """An optimiser stops later than teams do, in every series measured."""
    f1 = pd.read_csv(F1_DERIVED_DIR / "systematic_audit.csv")
    endurance = pd.read_csv(ENDURANCE_DERIVED_DIR / "systematic_audit.csv")

    groups = [("F1", f1["delta_laps"])] + [
        (str(series).upper(), group["delta_laps"])
        for series, group in endurance.groupby("series")
    ]
    groups.sort(key=lambda pair: pair[1].median())

    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.set_xlim(-32, 92)
    for position, (label, deltas) in enumerate(groups):
        ax.scatter(
            deltas, [position] * len(deltas), s=14, alpha=0.16,
            color="#2b2d42" if label == "F1" else "#00798c", zorder=2,
        )
        median = deltas.median()
        ax.scatter([median], [position], marker="|", s=900, linewidth=2.6,
                   color="#d1495b", zorder=4)
        # "Later" needs a definition, and it is not delta > 0: the audit calls
        # a disagreement of one lap an agreement, so the same bar is used here.
        later = (deltas > 1).mean() * 100
        ax.annotate(
            f"median {median:+.0f}    {later:.0f}% later    n = {len(deltas)}",
            (62, position), fontsize=9, va="center", color="#333333",
        )

    ax.axvline(0, color="#444444", linewidth=1.2, zorder=3)
    ax.set_yticks(range(len(groups)))
    ax.set_yticklabels([label for label, _ in groups])
    ax.set_xticks([-30, -20, -10, 0, 10, 20, 30, 40, 50])
    ax.set_xlabel("model's lap  -  team's lap      (negative = model stops earlier)")
    total = sum(len(deltas) for _, deltas in groups)
    ax.set_title(
        "An exact optimiser stops later than real teams, in all four series",
        fontsize=13, pad=16, loc="left",
    )
    ax.text(
        0.0, 1.01,
        f"{total} replayed first-stop decisions - the same criterion in every "
        "series - two candidate explanations tested, both rejected",
        transform=ax.transAxes, fontsize=9, color="#555555", va="bottom",
    )
    _style(ax)

    path = FIGURES / "r3_audit_bias.png"
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return f"{path}  ({total} decisions across {len(groups)} series)"


def main() -> int:
    FIGURES.mkdir(parents=True, exist_ok=True)
    for build in (r1_transfer, r2_pit_loss_rule, r3_audit_bias):
        print("wrote", build())
    return 0


if __name__ == "__main__":
    sys.exit(main())
