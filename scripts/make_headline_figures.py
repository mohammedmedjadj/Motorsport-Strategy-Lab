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
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.reporting.names import car_class as class_name  # noqa: E402
from src.ingestion.config import (  # noqa: E402
    ENDURANCE_DERIVED_DIR,
    F1_DERIVED_DIR,
    REPORTS_DIR,
)

FIGURES = REPORTS_DIR / "figures"

#: One colour per class, held fixed across every figure, the Streamlit demo and
#: the website, so a reader who learns the palette on one keeps it everywhere.
#: Defined once in src/reporting/palette.py -- this used to be a hand-copied
#: dict in two files, each carrying a comment asserting it matched the other.
from src.reporting.palette import CLASS_COLOURS, INK, MUTED  # noqa: E402


def _caption(ax: plt.Axes, text: str) -> None:
    """Subtitle under the title, in the same place on every figure here."""
    ax.text(0.0, 1.012, text, transform=ax.transAxes, fontsize=9,
            color="#555555", va="bottom")


def _style(ax: plt.Axes) -> None:
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_axisbelow(True)
    ax.grid(axis="x", alpha=0.25, linewidth=0.6)


def r1_transfer() -> str:
    """In endurance, a degradation slope rarely transfers to an unseen season."""
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
            s=46, alpha=0.9, label=class_name(str(car_class)),
            color=CLASS_COLOURS.get(str(car_class), "#888888"),
            edgecolor="white", linewidth=0.6, zorder=3,
        )
    ax.axvline(0, color="#444444", linewidth=1.0, zorder=2)

    # Name only the points a reader would otherwise have to squint at: the ones
    # that carry the result.
    for row in mean.itertuples():
        if row.r2_within > 0.2:
            ax.annotate(
                f"  {row.event} {class_name(str(row.car_class))}",
                (row.r2_within, row.Index), fontsize=8.5,
                va="center", color="#222222",
            )

    # Two circuit-classes sit far below the rest (COTA Hypercar at -1.49 is 3x
    # the next-worst), and on a full-range axis they squeeze all 49 others into
    # a tenth of the canvas, hiding the structure the figure exists to show.
    # The axis is clipped and anything outside it is named, because dropping an
    # inconvenient point without saying so is a different thing entirely.
    floor = -0.55
    off_scale = mean[mean["r2_within"] < floor]
    ax.set_xlim(floor, mean["r2_within"].max() + 0.30)
    if not off_scale.empty:
        named = ", ".join(
            f"{row.event} {class_name(str(row.car_class))} {row.r2_within:+.2f}"
            for row in off_scale.itertuples()
        )
        # Under the axis, not inside it. At the floor it printed on top of
        # the worst point still in view, which is the one a reader most wants
        # to see.
        fig.text(0.012, 0.012,
                 f"off scale, worse than the axis shows: {named}",
                 fontsize=8.5, color="#8a4b52")

    ax.set_yticks([])
    ax.set_xlabel(
        "leave-one-race-out mean within-stint R\u00b2   \u2192   transfers better"
    )
    ax.set_title(
        "In endurance, a degradation slope rarely transfers to an unseen season",
        fontsize=13, pad=24, loc="left",
    )
    clear = int((mean["r2_within"] > 0.2).sum())
    ax.text(
        0.0, 1.01,
        f"{len(mean)} circuit-classes across IMSA, WEC and ELMS \u2014 only {clear} "
        "clear a within-stint R\u00b2 of 0.2 \u2014 one protocol, applied identically everywhere",
        transform=ax.transAxes, fontsize=9, color="#555555", va="bottom",
    )
    ax.legend(frameon=False, fontsize=9, loc="lower right", title="class",
              title_fontsize=9, bbox_to_anchor=(0.985, 0.02))
    _style(ax)

    path = FIGURES / "r1_transfer.png"
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return f"{path}  ({len(mean)} circuit-classes, {clear} above 0.2)"


def r2_pit_loss_rule() -> str:
    """Tyre-limited race-seasons occur only where the stop is cheap."""
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
    #
    # Two classes sit at zero within a few seconds of each other, and their
    # labels overprinted. Walk left to right and drop a label below its marker
    # whenever the one before it was close enough to collide.
    span = by_class["pit_loss"].max() - by_class["pit_loss"].min()
    placed: list[tuple[float, float, int]] = []
    for row in by_class.sort_values("pit_loss").itertuples():
        left.scatter(
            row.pit_loss, row.share, s=40 + row.n * 3.2,
            color=CLASS_COLOURS.get(str(row.car_class), "#888888"),
            alpha=0.9, edgecolor="white", linewidth=1.0, zorder=3,
        )
        collides = any(
            abs(row.pit_loss - x) < 0.22 * span
            and abs(row.share - y) < 2.0
            and offset > 0
            for x, y, offset in placed
        )
        offset = -14 if collides else 6
        left.annotate(
            f"{row.series.upper()} {class_name(str(row.car_class))}",
            (row.pit_loss, row.share), fontsize=8.5,
            xytext=(7, offset), textcoords="offset points", color="#333333",
        )
        placed.append((row.pit_loss, row.share, offset))

    # Labels sit to the right of their markers, so the rightmost one needs
    # room or it prints into the frame.
    left.set_xlim(by_class["pit_loss"].min() - 0.06 * span,
                  by_class["pit_loss"].max() + 0.42 * span)
    left.set_ylim(-2.5, by_class["share"].max() + 3.0)

    correlation = by_class["pit_loss"].corr(by_class["share"])
    left.set_xlabel("median pit loss (s)")
    left.set_ylabel("share of race-seasons that are tyre-limited (%)")
    left.set_title(
        f"Per class: r = {correlation:+.3f}, monotonic, no inversion",
        fontsize=11, loc="left", pad=26,
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
                    fontsize=11, loc="left", pad=26)
    right.legend(frameon=False, fontsize=9, loc="upper right")
    _style(right)
    right.grid(axis="y", alpha=0.25, linewidth=0.6)

    fig.suptitle(
        "In these championships, tyres beat fuel only where the stop is cheap",
        fontsize=13, x=0.006, ha="left", y=0.995,
    )
    path = FIGURES / "r2_pit_loss_rule.png"
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return (f"{path}  (r={correlation:+.3f}, edge {threshold:.1f}s, "
            f"n={len(plans)})")


def _signed(x: float) -> str:
    """A median for a label: "+2", "-1", and a plain "0" rather than "+0"."""
    text = f"{x:+.0f}"
    return "0" if text in ("+0", "-0") else text


def r3_audit_bias() -> str:
    """The planner-team gap, as published and with each team's strategy fixed.

    Split by **class**, not by series: IMSA runs GTP, GTD and GTD PRO at the
    same rounds with very different pit losses, and pooling them would average
    three strategy regimes into a number describing none of them.

    Each class gets two rows. The upper, grey one is the audit as first run: a
    single-next-stop engine that runs the stint after its stop to the flag. The
    lower, coloured one replays the same decisions with the stint ending at the
    team's own second stop (scripts/run_committed_strategy*.py). The figure has
    to show both, because the text now says most of the first was the question
    the audit asked; a figure showing only the first would contradict it.
    """
    f1 = pd.read_csv(F1_DERIVED_DIR / "systematic_audit.csv")
    endurance = pd.read_csv(ENDURANCE_DERIVED_DIR / "systematic_audit.csv")
    f1_commit = pd.read_csv(F1_DERIVED_DIR / "committed_strategy.csv")
    end_commit = pd.read_csv(ENDURANCE_DERIVED_DIR / "committed_strategy.csv")

    def committed(frame: pd.DataFrame) -> pd.Series:
        return frame["committed_delta_laps"].dropna().astype(float)

    groups: list[tuple[str, str, pd.Series, pd.Series]] = [
        ("F1", "Formula 1", f1["delta_laps"], committed(f1_commit))
    ]
    for (series, car_class), group in endurance.groupby(["series", "car_class"]):
        mask = (end_commit["series"] == series) & (end_commit["car_class"] == car_class)
        groups.append((
            str(series).upper(),
            f"{str(series).upper()} {class_name(str(car_class))}",
            group["delta_laps"],
            committed(end_commit[mask]),
        ))
    series_median: dict[str, list[float]] = {}
    for series, _, deltas, _ in groups:
        series_median.setdefault(series, []).append(deltas.median())
    groups.sort(key=lambda g: (
        sum(series_median[g[0]]) / len(series_median[g[0]]), g[2].median()
    ))

    series_colour = {"F1": "#2b2d42", "WEC": "#30638e",
                     "ELMS": "#003d5b", "IMSA": "#00798c"}
    grey = "#b8b8b8"

    def box(ax, values, y, colour, median_colour):
        ax.boxplot(
            [values], positions=[y], vert=False, widths=0.30,
            showfliers=False,
            medianprops={"color": median_colour, "linewidth": 2.4},
            boxprops={"color": colour, "linewidth": 1.1},
            whiskerprops={"color": colour, "linewidth": 1.1},
            capprops={"color": colour, "linewidth": 1.1},
            zorder=3,
        )

    fig, ax = plt.subplots(figsize=(10.5, 7.4))
    ax.set_xlim(-34, 104)
    rng = np.random.default_rng(20260904)
    for position, (series, label, published, held) in enumerate(groups):
        colour = series_colour.get(series, "#666666")
        upper, lower = position + 0.19, position - 0.19
        ax.scatter(published, upper + rng.uniform(-0.10, 0.10, len(published)),
                   s=8, alpha=0.22, color=grey, linewidth=0, zorder=2)
        ax.scatter(held, lower + rng.uniform(-0.10, 0.10, len(held)),
                   s=8, alpha=0.30, color=colour, linewidth=0, zorder=2)
        box(ax, published, upper, "#8a8a8a", "#8a8a8a")
        box(ax, held, lower, "#333333", "#d1495b")
        ax.annotate(
            f"{_signed(published.median())}  \u2192  {_signed(held.median())}",
            (60, position), fontsize=10, va="center", color=INK,
            fontweight="bold",
        )
        ax.annotate(
            f"n = {len(published)} / {len(held)}",
            (80, position), fontsize=8.5, va="center", color=MUTED,
        )

    ax.axvline(0, color="#444444", linewidth=1.2, zorder=4)
    ax.set_yticks(range(len(groups)))
    ax.set_yticklabels([label for _, label, _, _ in groups], fontsize=9.5)
    ax.set_ylim(-0.7, len(groups) - 0.3)
    ax.set_xticks([-30, -20, -10, 0, 10, 20, 30, 40, 50])
    ax.set_xlabel("model's lap  -  team's lap      (negative = model stops earlier)")
    ax.text(60, len(groups) - 0.45, "median: published \u2192 strategy fixed",
            fontsize=8.5, color=MUTED, va="center")
    total = sum(len(p) for _, _, p, _ in groups)
    ax.set_title(
        "Most of the planner-team gap was the question the audit asked",
        fontsize=13, pad=30, loc="left",
    )
    _caption(ax,
             f"Grey: {total} first stops as first audited, with the planner's "
             "second stint run to the flag.\nColour: the same decisions "
             "replayed with the stint ending at the team's own second stop.")
    _style(ax)

    path = FIGURES / "r3_audit_bias.png"
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return f"{path}  ({total} decisions across {len(groups)} classes)"


def main() -> int:
    FIGURES.mkdir(parents=True, exist_ok=True)
    for build in (r1_transfer, r2_pit_loss_rule, r3_audit_bias):
        print("wrote", build())
    # The website serves its own copy under docs/, and a copy nothing
    # refreshes is the stale-duplicate problem this project has had before.
    # Running this script alone used to leave the site showing the previous
    # figures; the only thing that noticed was a site test failing minutes
    # later without saying which script had skipped the step.
    from make_supporting_figures import sync_site_figures  # noqa: PLC0415

    print("synced", sync_site_figures())
    return 0


if __name__ == "__main__":
    sys.exit(main())
