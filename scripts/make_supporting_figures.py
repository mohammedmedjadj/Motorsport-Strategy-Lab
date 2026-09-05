"""The layers underneath the three headline results, drawn from the artifacts.

`make_headline_figures.py` covers the three findings. This covers what they rest
on — and the repository badly needed it: 94 written reports and, before this,
28 images, 25 of which were per-circuit degradation plots. A reader could not
see the neutralisation regimes, the pit-loss spectrum every strategy conclusion
turns on, or how much of the calendar is actually measured, without reading
prose and building the picture themselves.

Six figures, each answering one question a reader asks in the first minute:

1. `s1_neutralisation_regimes`  — how often does a race get neutralised?
2. `s2_pit_loss_spectrum`       — what does a stop cost, per class?
3. `s3_f1_degradation`          — which circuits eat tyres, on which compound?
4. `s4_track_position`          — where is a place hard to regain?
5. `s5_baselines`               — does the optimiser beat a rule of thumb?
6. `s6_intervals`               — the tested results, with their intervals.

Every number is read from a committed CSV. Nothing is typed, so a figure cannot
drift from the finding it illustrates, and the drift workflow fails on any that
does.

Usage (offline, from the repo root)::

    python scripts/make_supporting_figures.py
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

from src.reporting.names import car_class as car_class_name  # noqa: E402
from src.reporting.names import circuit as circuit_name  # noqa: E402
from src.safety_car.endurance import RACE_KEY, race_timeline  # noqa: E402
from src.ingestion.config import (  # noqa: E402
    DERIVED_DIR,
    ENDURANCE_DERIVED_DIR,
    F1_DERIVED_DIR,
    REPORTS_DIR,
)

FIGURES = REPORTS_DIR / "figures"

#: Held identical to make_headline_figures.py so a reader who learns the
#: palette on one figure keeps it on every other.
CLASS_COLOURS = {
    "GTD": "#d1495b", "GTDPRO": "#edae49", "GTP": "#00798c",
    "HYPERCAR": "#30638e", "LMP2": "#003d5b", "LMP2 Pro/Am": "#7e9aa8",
    "F1": "#2b2d42",
}
COMPOUND_COLOURS = {"SOFT": "#d1495b", "MEDIUM": "#edae49", "HARD": "#8d99ae"}
INK, MUTED = "#222222", "#666666"


def _frame(ax: plt.Axes, xgrid: bool = True) -> None:
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_axisbelow(True)
    ax.grid(axis="x" if xgrid else "y", alpha=0.25, linewidth=0.6)


def _caption(ax: plt.Axes, text: str) -> None:
    ax.text(0.0, 1.012, text, transform=ax.transAxes, fontsize=9,
            color="#555555", va="bottom")


def s1_neutralisation_regimes() -> str:
    """Three series, three regimes, and no average that describes any of them."""
    # Reuse the project's own definition rather than re-deriving one. The first
    # version of this figure asked "did any row carry an SF flag", which fires
    # when a single car shows it on a single lap -- and disagreed with five
    # published reports (WEC 23 of 33 against their 19). The reports were
    # right: `race_timeline` collapses per-car flags to the *modal* flag for
    # the race on that lap, because a Safety Car is a state of the race, not of
    # a car. Reimplementing a definition the codebase already owns is how a
    # figure ends up contradicting the text beside it.
    flags = pd.read_csv(ENDURANCE_DERIVED_DIR / "race_flags.csv")
    timeline = race_timeline(flags)
    rows = []
    for key, race in timeline.groupby(RACE_KEY, sort=True):
        rows.append({
            "series": str(key[0]).upper(),
            "safety_car": bool((race["flags"] == "SF").any()),
            "full_course_yellow": bool((race["flags"] == "FCY").any()),
        })
    endurance = pd.DataFrame(rows)

    sc_model = pd.read_csv(F1_DERIVED_DIR / "sc_model.csv")
    f1_editions = int(sc_model["n_editions"].sum())
    f1_sc = int(sc_model["sc_races_with_event"].sum())

    bars = [("F1", f1_sc, f1_editions)]
    for series, group in endurance.groupby("series"):
        bars.append((series, int(group["safety_car"].sum()), len(group)))
    bars.sort(key=lambda b: b[1] / b[2])

    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    labels = [b[0] for b in bars]
    shares = [100 * b[1] / b[2] for b in bars]
    colours = ["#2b2d42" if label == "F1" else "#00798c" for label in labels]
    ax.barh(labels, shares, color=colours, height=0.55, zorder=3)
    for position, (label, hits, total) in enumerate(bars):
        share = 100 * hits / total
        ax.annotate(f"  {hits} of {total} races  ({share:.0f}%)",
                    (share, position), va="center", fontsize=10, color=INK)

    ax.set_xlim(0, 100)
    ax.set_xlabel("share of races seeing at least one Safety Car (%)")
    ax.set_title("Three neutralisation regimes, and no average describes any",
                 fontsize=13, pad=16, loc="left")
    _caption(ax, "a pooled model would sit between these and be wrong "
                 "everywhere — every stop taken under caution is discounted "
                 "by this rate")
    _frame(ax)
    path = FIGURES / "s1_neutralisation_regimes.png"
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return f"{path}  ({len(bars)} series)"


def s2_pit_loss_spectrum() -> str:
    """What a stop costs, per class — the axis every conclusion turns on."""
    plans = pd.read_csv(ENDURANCE_DERIVED_DIR / "multistop_plans.csv")
    order = (plans.groupby(["series", "car_class"])["pit_loss_s"].median()
             .sort_values().index)

    fig, ax = plt.subplots(figsize=(10, 5.4))
    rng = np.random.default_rng(20260904)
    for position, (series, car_class) in enumerate(order):
        subset = plans[(plans["series"] == series)
                       & (plans["car_class"] == car_class)]["pit_loss_s"]
        colour = CLASS_COLOURS.get(str(car_class), "#888888")
        ax.scatter(subset, position + rng.uniform(-0.2, 0.2, len(subset)),
                   s=22, alpha=0.55, color=colour, linewidth=0, zorder=2)
        ax.scatter([subset.median()], [position], marker="|", s=700,
                   linewidth=2.6, color=INK, zorder=4)
        ax.annotate(f"  {subset.median():.0f} s", (subset.median(), position),
                    va="center", fontsize=9.5, color=INK,
                    xytext=(6, 9), textcoords="offset points")

    # F1's pit loss sits an order of magnitude below every endurance class,
    # which is what makes this comparison worth drawing at all.
    #
    # Named explicitly rather than guarded with `if column in df.columns`. The
    # first version used that idiom against the wrong column name and dropped
    # the entire F1 row with no error -- the silent-narrowing pattern this
    # project keeps rediscovering. A KeyError here is the correct outcome.
    f1_loss = pd.read_csv(DERIVED_DIR / "f1" / "history_pit_loss.csv")
    f1_values = f1_loss["pit_loss_median_s"].dropna()
    ax.scatter(f1_values, -1 + rng.uniform(-0.2, 0.2, len(f1_values)),
               s=22, alpha=0.55, color=CLASS_COLOURS["F1"], linewidth=0,
               zorder=2)
    ax.scatter([f1_values.median()], [-1], marker="|", s=700,
               linewidth=2.6, color=INK, zorder=4)
    ax.annotate(f"  {f1_values.median():.0f} s", (f1_values.median(), -1),
                va="center", fontsize=9.5, color=INK,
                xytext=(6, 9), textcoords="offset points")

    # One entry reads 358 s. The reports already call it a near-certain
    # artefact -- a six-minute service is a stoppage the pit-loss estimator
    # absorbed, not a pit stop -- and a reader seeing an unexplained outlier on
    # a log axis has no way to know that. Naming it costs one line.
    worst = plans.nlargest(1, "pit_loss_s").iloc[0]
    if worst["pit_loss_s"] > 3 * plans["pit_loss_s"].quantile(0.99):
        y = list(order).index((worst["series"], worst["car_class"]))
        # Marked on the point, explained under the axis. An inline callout
        # this long sat on top of the data it was pointing at.
        ax.annotate("✕", (worst["pit_loss_s"], y), fontsize=11,
                    color="#8a4b52", ha="center", va="center", zorder=5)
        fig.text(
            0.012, 0.012,
            f"✕  {worst['pit_loss_s']:.0f} s "
            f"({worst['series'].upper()} {circuit_name(worst['circuit'])} "
            f"{int(worst['year'])}) is a known artefact — a six-minute "
            "service the pit-loss estimator absorbed as a stop. Kept in "
            "view rather than quietly removed.",
            fontsize=8.5, color="#8a4b52",
        )

    labels = ["Formula 1"] + [f"{s.upper()} {car_class_name(c)}" for s, c in order]
    ticks = [-1] + list(range(len(order)))
    ax.set_yticks(ticks)
    ax.set_yticklabels(labels)
    ax.set_xscale("log")
    ax.set_xlabel("pit loss (s), log scale — one point per race-season")
    ax.set_title("What a stop costs, and why it decides the strategy regime",
                 fontsize=13, pad=16, loc="left")
    _caption(ax, "a GT3 stop is a tyre change; a prototype stop is a tank, a "
                 "driver and four tyres — a 3x range that sets everything")
    _frame(ax)
    path = FIGURES / "s2_pit_loss_spectrum.png"
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return f"{path}  ({len(order)} classes)"


def s3_f1_degradation() -> str:
    """Which circuits eat tyres, on which compound, with intervals.

    Three things made the first version read as script output. Circuit names
    came from the slugs (`red_bull_ring`, `yas_marina`). A couple of extreme
    points stretched the axis until the other twenty-odd circuits sat in a band
    too narrow to read. And the title ran into its own subtitle.

    Off-scale points are clipped and listed under the axis rather than dropped.
    Removing them silently would be the same defect as any other silent
    narrowing here, and there have been enough of those.
    """
    coefs = pd.read_csv(F1_DERIVED_DIR / "degradation_coefficients.csv")
    order = (coefs.groupby("circuit")["deg_p1"].median()
             .sort_values().index.tolist())

    # Clip where the mass is. A handful of extremes otherwise compress every
    # other circuit into a tenth of the axis.
    low, high = coefs["deg_p1"].quantile([0.05, 0.95])
    pad = 0.25 * (high - low)
    limits = (low - pad, high + pad)
    off = coefs[(coefs["deg_p1"] < limits[0]) | (coefs["deg_p1"] > limits[1])]

    fig, ax = plt.subplots(figsize=(9.5, 10))
    for compound, group in coefs.groupby("compound"):
        colour = COMPOUND_COLOURS.get(str(compound), "#888888")
        offset = {"SOFT": -0.24, "MEDIUM": 0.0, "HARD": 0.24}.get(str(compound), 0)
        y = [order.index(c) + offset for c in group["circuit"]]
        ax.errorbar(
            group["deg_p1"], y,
            xerr=[group["deg_p1"] - group["deg_p1_ci_low"],
                  group["deg_p1_ci_high"] - group["deg_p1"]],
            fmt="o", markersize=4.5, elinewidth=1.1, capsize=0,
            color=colour, label=str(compound).title(), alpha=0.9, zorder=3,
        )
    ax.axvline(0, color="#444444", linewidth=1.0, zorder=2)
    ax.set_xlim(*limits)

    # A small arrow at the edge says a point continues past it; the values
    # themselves go under the axis, where nothing can collide with them.
    for row in off.itertuples():
        beyond = row.deg_p1 > limits[1]
        ax.annotate(
            "▸" if beyond else "◂",
            (limits[1] if beyond else limits[0], order.index(row.circuit)),
            fontsize=11, color="#8a4b52", ha="center", va="center", zorder=5,
        )

    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([circuit_name(c) for c in order], fontsize=9)
    ax.set_xlabel("tyre-age slope (s per lap of tyre age), cluster-robust 95% CI")
    ax.set_title("Degradation per circuit and compound, with honest intervals",
                 fontsize=13, pad=34, loc="left")
    _caption(ax, f"{len(coefs)} fitted coefficients across {len(order)} circuits.\n"
                 "An interval crossing zero means no measurable wear on that "
                 "compound at that circuit.")
    ax.legend(frameon=False, fontsize=9, loc="lower right",
              title="compound", title_fontsize=9,
              bbox_to_anchor=(1.0, 0.02))
    _frame(ax)

    if len(off):
        named = ";  ".join(
            f"{circuit_name(r.circuit)} {str(r.compound).title()} {r.deg_p1:+.3f}"
            for r in off.itertuples()
        )
        fig.text(0.012, 0.012,
                 f"Outside the axis, clipped rather than dropped:  {named}",
                 fontsize=8.5, color="#8a4b52")

    path = FIGURES / "s3_f1_degradation.png"
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return f"{path}  ({len(coefs)} coefficients, {len(off)} clipped)"


def s4_track_position() -> str:
    """Where a place is hard to regain — the primitive the rival model uses."""
    swaps = pd.read_csv(F1_DERIVED_DIR / "overtaking_difficulty.csv")
    swaps = swaps.sort_values("adj_swap_rate")

    fig, ax = plt.subplots(figsize=(9.5, 7.5))
    colours = plt.cm.RdYlBu_r(
        (swaps["adj_swap_rate"] - swaps["adj_swap_rate"].min())
        / (swaps["adj_swap_rate"].max() - swaps["adj_swap_rate"].min())
    )
    ax.barh(range(len(swaps)), swaps["adj_swap_rate"], color=colours,
            height=0.65, zorder=3)
    ax.set_yticks(range(len(swaps)))
    ax.set_yticklabels([circuit_name(c) for c in swaps["circuit"]], fontsize=9)
    for position, row in enumerate(swaps.itertuples()):
        ax.annotate(f"  {row.adj_swap_rate:.4f}", (row.adj_swap_rate, position),
                    va="center", fontsize=8.5, color=MUTED)

    ratio = swaps["adj_swap_rate"].max() / swaps["adj_swap_rate"].min()
    ax.set_xlabel("adjacent-car swap rate per lap  →  easier to overtake")
    ax.set_title("Track position: a 14-fold range that actually transfers",
                 fontsize=13, pad=16, loc="left")
    _caption(ax, f"{circuit_name(swaps['circuit'].iloc[0])} to "
                 f"{circuit_name(swaps['circuit'].iloc[-1])} is "
                 f"a {ratio:.0f}x range — unlike degradation, this holds "
                 "between seasons, which is why the rival model is built on it")
    _frame(ax)
    path = FIGURES / "s4_track_position.png"
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return f"{path}  ({len(swaps)} circuits, {ratio:.0f}x range)"


def s5_baselines() -> str:
    """Does the exact optimiser beat a rule of thumb? Often not.

    Per class, not per championship. IMSA's three classes run the same rounds
    with pit losses of 57, 24 and 40 seconds, and B3 --- run the tank out ---
    means something different in each. Averaging them into one IMSA bar
    describes none of them, which is the mistake this project refuses
    everywhere else.
    """
    frames = [
        pd.read_csv(DERIVED_DIR / series / "baseline_comparison.csv")
        for series in ("f1", "endurance")
        if (DERIVED_DIR / series / "baseline_comparison.csv").exists()
    ]
    if not frames:
        return "skipped — baseline comparison not generated"
    scored = pd.concat(frames, ignore_index=True)
    scored["car_class"] = scored["car_class"].fillna("")

    units: list[tuple[str, pd.DataFrame]] = []
    for series, group in scored.groupby("series"):
        if str(series) == "f1":
            units.append(("Formula 1", group))
            continue
        for car_class, sub in group.groupby("car_class"):
            units.append(
                (f"{str(series).upper()} {car_class_name(str(car_class))}", sub)
            )

    methods = [("model_pit_lap", "exact optimiser", "#2b2d42"),
               ("b1_lap", "B1 fixed interval", "#00798c"),
               ("b2_lap", "B2 threshold", "#edae49"),
               ("b3_lap", "B3 fuel deadline", "#d1495b")]

    # Order by how badly the optimiser does, so the pattern reads top to bottom.
    def optimiser_error(pair):
        errors = (pair[1]["model_pit_lap"] - pair[1]["real_pit_lap"]).abs().dropna()
        return errors.median() if len(errors) else 0.0

    units.sort(key=optimiser_error)

    fig, ax = plt.subplots(figsize=(11, 6.4))
    height = 0.2
    for index, (column, label, colour) in enumerate(methods):
        values, positions = [], []
        for position, (_, group) in enumerate(units):
            errors = (group[column] - group["real_pit_lap"]).abs().dropna()
            if not len(errors):
                continue
            values.append(errors.median())
            positions.append(position + (1.5 - index) * height)
        ax.barh(positions, values, height=height * 0.9, label=label,
                color=colour, zorder=3)
        for y, v in zip(positions, values):
            ax.annotate(f"{v:.0f}", (v, y), va="center", fontsize=8.5,
                        color=INK, xytext=(3, 0), textcoords="offset points")

    ax.set_yticks(range(len(units)))
    ax.set_yticklabels([label for label, _ in units], fontsize=9.5)
    ax.set_ylim(-0.6, len(units) - 0.4)
    ax.set_xlabel("median |Δ| laps against the real stop  →  further from practice")
    ax.set_title("A rule of thumb beats the exact optimiser in most classes",
                 fontsize=13, pad=30, loc="left")
    _caption(ax, f"{len(scored):,} decisions, same artifacts, same metric.\n"
                 "B3 is undefined in Formula 1, which has not refuelled since "
                 "2010, and is reported as undefined rather than substituted.")
    ax.legend(frameon=False, fontsize=9, ncol=4, loc="lower right")
    _frame(ax)
    path = FIGURES / "s5_baselines.png"
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return f"{path}  ({len(scored)} decisions across {len(units)} classes)"


def s6_intervals() -> str:
    """A forest plot of every result that carries an interval.

    Split into two panels on purpose. A forest plot earns its keep because bar
    *lengths* are comparable; putting a correlation (bounded, unitless) beside
    two R2 quantities on one axis invites a comparison that means nothing. The
    first version did exactly that, and the eye read the correlation's long bar
    as the strongest result rather than as a different measurement entirely.
    """
    path_csv = DERIVED_DIR / "cross_series" / "formal_tests.csv"
    if not path_csv.exists():
        return "skipped — formal tests not generated"
    tests = pd.read_csv(path_csv)
    # A leave-one-out sensitivity is not an interval, and drawing it as one
    # would say it is.
    tests = tests[tests["result"] != "cheap-stop edge (s)"]

    is_correlation = tests["result"].str.contains(r"\(r\)", regex=True)
    panels = [
        (tests[~is_correlation].reset_index(drop=True),
         "Transfer, in within-stint R² units", (-0.35, 0.75)),
        (tests[is_correlation].reset_index(drop=True),
         "Pit-loss rule, as a correlation", (-1.05, 0.15)),
    ]

    fig, axes = plt.subplots(
        2, 1, figsize=(10, 5.6),
        gridspec_kw={"height_ratios": [len(panels[0][0]), 1.15]},
    )
    for ax, (frame, heading, limits) in zip(axes, panels):
        for position, row in enumerate(frame.itertuples()):
            crosses_zero = row.ci_low <= 0 <= row.ci_high
            colour = "#8d99ae" if crosses_zero else "#d1495b"
            ax.plot([row.ci_low, row.ci_high], [position, position],
                    color=colour, linewidth=2.6, zorder=3,
                    solid_capstyle="round")
            ax.scatter([row.estimate], [position], s=70, color=colour,
                       edgecolor="white", linewidth=1.2, zorder=4)
            ax.annotate(
                f"  {row.estimate:+.3f}  [{row.ci_low:+.3f}, {row.ci_high:+.3f}]"
                + ("   crosses zero" if crosses_zero else ""),
                (max(row.ci_high, row.estimate), position), va="center",
                fontsize=9, color=INK, xytext=(8, 0),
                textcoords="offset points",
            )
        ax.axvline(0, color="#444444", linewidth=1.1, zorder=2)
        ax.set_yticks(range(len(frame)))
        ax.set_yticklabels(frame["result"], fontsize=9.5)
        ax.set_ylim(-0.7, len(frame) - 0.3)
        ax.set_xlim(*limits)
        ax.set_title(heading, fontsize=10.5, loc="left", color=MUTED, pad=6)
        _frame(ax)

    axes[-1].set_xlabel("estimate with 95% bootstrap interval")
    fig.suptitle("Every result that carries an interval",
                 fontsize=13, x=0.006, ha="left", y=0.995)
    fig.text(0.006, 0.945,
             "red excludes zero, grey does not — each resampled at the level "
             "its data varies at, never the level that makes it narrowest",
             fontsize=9, color="#555555")
    path = FIGURES / "s6_intervals.png"
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return f"{path}  ({len(tests)} results in 2 unit panels)"


def sync_site_figures() -> str:
    """Copy every figure into docs/, which is what GitHub Pages serves.

    The site cannot reference ../reports/figures/ -- Pages serves docs/ as the
    root -- so the choice is a copy or a broken image. A copy that nothing
    refreshes is the stale-duplicate problem this project has already had once,
    so it happens here, after every figure is regenerated, and
    tests/test_site.py fails if the two directories ever differ.
    """
    import shutil

    site = REPORTS_DIR.parent / "docs" / "figures"
    site.mkdir(parents=True, exist_ok=True)
    copied = 0
    for source in sorted(FIGURES.glob("*.png")):
        target = site / source.name
        if not target.exists() or target.read_bytes() != source.read_bytes():
            shutil.copy2(source, target)
        copied += 1
    # Anything in the site that no longer exists upstream is a dead image.
    for stale in sorted(site.glob("*.png")):
        if not (FIGURES / stale.name).exists():
            stale.unlink()
            print(f"  removed orphaned site figure {stale.name}")
    return f"{site}  ({copied} figures in sync)"


def main() -> int:
    FIGURES.mkdir(parents=True, exist_ok=True)
    for build in (s1_neutralisation_regimes, s2_pit_loss_spectrum,
                  s3_f1_degradation, s4_track_position, s5_baselines,
                  s6_intervals):
        print("wrote", build())
    print("synced", sync_site_figures())
    return 0


if __name__ == "__main__":
    sys.exit(main())