"""One page on Result 2, for a reader who knows strategy optimisation.

Written for a reply from Wytze de Vries (TU Eindhoven), who asked for the
correlation data behind the pit-loss rule. It is not the project one-pager: it
covers one result, in enough methodological detail that someone who builds
optimal control for endurance racing can judge whether the measurement is
sound, and it ends on the question I actually want answered.

Generated, not written, for the same reason the paper is: every quantity here
comes from a committed artifact. A brief sent to a researcher is the last place
a stale number should appear.

    python scripts/make_outreach_brief.py

Writes outreach/pit_loss_rule_brief.pdf. PDF because it is an email
attachment; Markdown would be pasted into a body and lose the figure.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ingestion.config import DERIVED_DIR, ENDURANCE_DERIVED_DIR, REPO_ROOT  # noqa: E402
from src.reporting import palette  # noqa: E402
from src.reporting.names import car_class as class_name  # noqa: E402
from src.reporting.names import circuit as circuit_name  # noqa: E402

OUT = REPO_ROOT / "outreach" / "pit_loss_rule_brief.pdf"
FIGURE = REPO_ROOT / "reports" / "figures" / "r2_pit_loss_rule.png"
REPO_URL = "github.com/mohammedmedjadj/Motorsport-Strategy-Lab"
CONCEPT_DOI = "10.5281/zenodo.22726130"


def _facts() -> dict[str, object]:
    """Everything the page states, recomputed from the artifacts."""
    plans = pd.read_csv(ENDURANCE_DERIVED_DIR / "multistop_plans.csv")
    plans["tyre_limited"] = plans["optimal_stops"] != plans["min_stops"]

    by_class = (
        plans.groupby(["series", "car_class"])
        .agg(
            pit_loss=("pit_loss_s", "median"),
            share=("tyre_limited", "mean"),
            n=("tyre_limited", "size"),
        )
        .reset_index()
        .sort_values("pit_loss")
    )

    tests = pd.read_csv(DERIVED_DIR / "cross_series" / "formal_tests.csv")
    correlation = tests[tests["result"].str.contains(r"\(r\)", regex=True)].iloc[0]

    limited = plans.loc[plans["tyre_limited"]]
    edge = float(limited["pit_loss_s"].max())
    defining = limited.loc[limited["pit_loss_s"].idxmax()]
    runner_up = float(limited["pit_loss_s"].nlargest(2).iloc[-1])
    above = plans.loc[plans["pit_loss_s"] > edge]

    return {
        "n_race_seasons": len(plans),
        "n_limited": int(plans["tyre_limited"].sum()),
        "by_class": by_class,
        "r": float(correlation["estimate"]),
        "ci": (float(correlation["ci_low"]), float(correlation["ci_high"])),
        "draws": int(float(correlation["draws"])),
        "edge": edge,
        "edge_where": (
            f"{str(defining['series']).upper()} "
            f"{class_name(str(defining['car_class']))} at "
            f"{circuit_name(str(defining['circuit_canonical']))} "
            f"{int(defining['year'])}"
        ),
        "runner_up": runner_up,
        "drop_pct": 100.0 * (edge - runner_up) / edge,
        "n_above": len(above),
        "n_limited_above": int(above["tyre_limited"].sum()),
        "fuel_quantile": 0.9,
    }


PAGE_W, PAGE_H = 8.27, 11.69
LEFT, RIGHT = 0.072, 0.928
BODY, SMALL, HEAD = 7.85, 7.35, 9.9
LINESPACING = 1.20

#: Top and bottom margins, in figure fractions. The overflow check below uses
#: the same constant, so the page cannot quietly acquire a thinner footer than
#: header by drifting.
MARGIN = 0.028


def _height(size: float, lines: int) -> float:
    """Figure-fraction height of a block of text, in the units y moves in."""
    return lines * size * LINESPACING / 72.0 / PAGE_H


def _page(facts: dict[str, object]) -> plt.Figure:
    ink, muted = palette.LIGHT["ink"], palette.LIGHT["muted"]
    fig = plt.figure(figsize=(PAGE_W, PAGE_H))
    fig.patch.set_facecolor("white")
    cursor = [1.0 - MARGIN]

    def block(body, size=BODY, colour=ink, weight="normal", gap=0.0075):
        fig.text(LEFT, cursor[0], body, size=size, color=colour, weight=weight,
                 va="top", ha="left", linespacing=LINESPACING)
        cursor[0] -= _height(size, body.count("\n") + 1) + gap

    def heading(body, colour=palette.NAVY):
        block(body, size=HEAD, colour=colour, weight="bold", gap=0.004)

    block("Does the stop decision reduce to the binding constraint?",
          size=15.0, weight="bold", gap=0.004)
    block("Pit-loss cost and the tyre/fuel boundary across "
          f"{facts['n_race_seasons']} endurance race-seasons",
          size=10.2, colour=muted, gap=0.003)
    block(f"Mohammed Reda Medjadj  ·  {REPO_URL}  ·  doi.org/{CONCEPT_DOI}",
          size=8.0, colour=muted, gap=0.012)

    fig.add_artist(plt.Line2D([LEFT, RIGHT], [cursor[0]] * 2,
                              color=palette.LIGHT["line"], linewidth=0.9,
                              transform=fig.transFigure))
    cursor[0] -= 0.014

    heading("The question")
    block("The tank sets a floor on the number of stops; tyre degradation can in principle justify one more\n"
          "than that floor. My question is whether that is settled by the price of the binding constraint\n"
          "alone — once a stop costs enough, no car's degradation is steep enough to pay for it — rather\n"
          "than by the machinery. Your competitor-aware work prices charge and the stops it forces; this\n"
          "asks whether the price of the constraint, not the vehicle, sets the regime.")

    heading("How the two quantities are measured")
    block("Pit loss, per green-flag stop, in-lap and following out-lap both under green:\n"
          "        loss  =  t_in + t_out  −  2 × that driver's median green pace in that race\n"
          "so it carries pit-lane transit and stationary time together, reported per class as a median.\n"
          f"Fuel range F is the ceiling of the {facts['fuel_quantile']:.1f} quantile of laps between pit visits, not the maximum,\n"
          "which is contaminated by cars that had stopped racing.\n"
          "\n"
          "Tyre-limited, by exact dynamic program. For race length L, green pace p, fitted net slope β and\n"
          "pit loss π, a plan partitions L into stints (n₁ … n_m₊₁) with m stops, costing\n"
          "        T  =  m·π  +  Σ_j ( n_j·p  +  β·n_j(n_j+1)/2 )        subject to  n_j ≤ F\n"
          "minimised exactly for each m from the fuel minimum ⌈L/F⌉−1 upward; tyre-limited means the\n"
          "time-optimal m exceeds that minimum. The triangular sum is exact rather than the β·n²/2 integral —\n"
          "they differ by β·n/2, about a second over a forty-lap stint, and that is the only quantity\n"
          "weighed against π. β is fitted per race-season with driver–race fixed effects, as a net slope:\n"
          "the source carries no compound label.")

    heading("The correlation")
    rows = ["class                         median pit loss    tyre-limited     race-seasons"]
    for row in facts["by_class"].itertuples():
        label = f"{str(row.series).upper()} {class_name(str(row.car_class))}"
        rows.append(f"{label:<28}{row.pit_loss:>9.1f} s{100 * row.share:>13.1f} %{row.n:>14d}")
    fig.text(LEFT, cursor[0], "\n".join(rows), size=SMALL, color=ink, va="top",
             ha="left", linespacing=LINESPACING, family="DejaVu Sans Mono")
    cursor[0] -= _height(SMALL, len(rows)) + 0.011

    low, high = facts["ci"]
    block(f"r = {facts['r']:.3f}, 95% CI [{low:.3f}, {high:.3f}], monotonic across all six classes with no inversion. The\n"
          f"interval is bootstrapped over races within class ({facts['n_race_seasons']} races, {facts['draws']:,} replicates), not over the six\n"
          f"class summaries — six fixed championships are not a source of variation. At race level, {facts['n_above']} of\n"
          f"{facts['n_race_seasons']} race-seasons sit above {facts['edge']:.1f} s of pit loss and "
          f"{facts['n_limited_above']} of those is tyre-limited, across every class\n"
          f"({facts['n_limited']} of {facts['n_race_seasons']} are tyre-limited in total).",
          gap=0.013)

    image = mpimg.imread(FIGURE)
    width = RIGHT - LEFT
    height = width * PAGE_W / PAGE_H * image.shape[0] / image.shape[1]
    axes = fig.add_axes((LEFT, cursor[0] - height, width, height))
    axes.imshow(image)
    axes.axis("off")
    cursor[0] -= height + 0.015

    heading("Where this evidence is thin", colour=palette.RED)
    block(f"The {facts['edge']:.1f} s edge is a maximum, and one race puts it there: {facts['edge_where']}. The next\n"
          f"tyre-limited race sits at {facts['runner_up']:.1f} s, so removing that one race moves it by "
          f"{facts['drop_pct']:.0f}%. I report no\n"
          "interval for it: a maximum sits on the boundary of its own support, so the bootstrap is degenerate\n"
          "above it and understates uncertainty below. The rule is not thin — the constant is.")

    heading("What I would value your view on")
    block("Whether a correlation across six class summaries is the right statistic at all. The alternative\n"
          f"I see is a per-race model with pit loss as covariate and tyre-limited as outcome, using all\n"
          f"{facts['n_race_seasons']} race-seasons instead of six points, at the cost of modelling the within-class\n"
          "dependence those summaries absorb.")

    if cursor[0] < MARGIN:
        raise SystemExit(
            f"the brief overflows one page (ended at {cursor[0]:.3f}, margin {MARGIN}); "
            "cut text rather than shrinking the figure"
        )
    return fig


def main() -> int:
    if not FIGURE.exists():
        raise SystemExit(
            f"{FIGURE} is missing; run scripts/make_headline_figures.py first"
        )
    facts = _facts()
    fig = _page(facts)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # No CreationDate: it is the only byte that changes between runs, and a
    # timestamp is not information about the brief. Regenerating an unchanged
    # brief should produce an unchanged file, so a real diff means a real change.
    fig.savefig(OUT, format="pdf", metadata={
        "Title": "Does the stop decision reduce to the binding constraint?",
        "Author": "Mohammed Reda Medjadj",
        "Subject": "Pit-loss cost and the tyre/fuel boundary across endurance racing",
        "Creator": "scripts/make_outreach_brief.py",
        "CreationDate": None,
    })
    plt.close(fig)
    print(f"wrote {OUT}  (r={facts['r']:.3f}, {facts['n_race_seasons']} race-seasons)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
